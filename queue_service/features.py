"""Сбор детерминированных фактов о студенте из сохранённых результатов тестов."""

import hashlib
import json
import statistics
from typing import Optional


def _norm(value):
    if isinstance(value, (list, tuple)):
        return tuple(sorted(str(x).strip().casefold() for x in value))
    return str(value).strip().casefold()


def _is_correct(user_answer, correct_answer) -> bool:
    if isinstance(correct_answer, list):
        return isinstance(user_answer, list) and _norm(user_answer) == _norm(correct_answer)
    if isinstance(user_answer, list):
        return len(user_answer) == 1 and _norm(user_answer[0]) == _norm(correct_answer)
    return _norm(user_answer) == _norm(correct_answer)


def _parse_duration(value) -> Optional[int]:
    if not value:
        return None
    text = str(value)
    if "day" in text:
        return None
    try:
        parts = [int(p) for p in text.split(":")]
    except ValueError:
        return None
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return None


def _short(value) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(x) for x in value)
    return str(value)


def _attempt_time(result: dict) -> str:
    return result.get("start_time") or ""


def input_hash(results: list) -> str:
    """Хеш входных данных портрета: один и тот же в сервисе и в очереди.

    Без него очередь и portrait_service считали бы кеш по разным ключам
    и повторно гоняли LLM на тех же данных.
    """
    payload = [
        [
            r.get("test_name"),
            r.get("start_time"),
            r.get("score_percentage"),
            r.get("final_status"),
            # Ответы входят в хеш: иначе новый прогон того же студента
            # (другие ошибки при том же балле) отдавал бы устаревший портрет.
            r.get("answers"),
        ]
        for r in sorted(results, key=lambda x: x.get("start_time") or "")
    ]
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_facts(results: list, max_errors: int = 30) -> tuple:
    ordered = sorted(results, key=_attempt_time)
    scores = [float(r.get("score_percentage") or 0) for r in ordered]
    attempts = len(ordered)
    passed = sum(1 for r in ordered if r.get("final_status") in ("Зачёт", "Passed"))

    topics: dict = {}
    for r in ordered:
        for topic, info in (r.get("category_scores") or {}).items():
            if not isinstance(info, dict):
                continue
            total = float(info.get("total") or 0)
            if total <= 0:
                continue
            agg = topics.setdefault(topic, {"score": 0.0, "total": 0.0})
            agg["score"] += float(info.get("score") or 0)
            agg["total"] += total

    topic_stats = [
        {
            "topic": topic,
            "percentage": round((agg["score"] / agg["total"]) * 100, 1) if agg["total"] else 0.0,
            "questions": int(agg["total"]),
        }
        for topic, agg in topics.items()
    ]
    topic_stats.sort(key=lambda t: t["percentage"])

    # Динамика: первая попытка против средней последующих.
    # С 2 попытками это уже осмысленно; «недостаточно данных» — только при одной.
    if attempts >= 2:
        first_avg = scores[0]
        last_avg = sum(scores[1:]) / (attempts - 1)
        delta = round(last_avg - first_avg, 1)
        trend = "рост" if delta >= 5 else "падение" if delta <= -5 else "стабильно"
    else:
        delta = None
        trend = "недостаточно данных"

    durations = [d for d in (_parse_duration(r.get("duration")) for r in ordered) if d is not None]

    # Собираем историю каждого вопроса по всем попыткам.
    # Без неё модель не знает, что ошибка в первой попытке была исправлена
    # во второй, и выдаёт закрытый пробел как текущий.
    history: dict = {}
    attempt_no = 0
    unanswered = 0
    total_answers = 0
    for r in ordered:
        attempt_no += 1
        for a in r.get("answers") or []:
            total_answers += 1
            question = (a.get("question") or "").strip()
            if not question:
                continue
            user_answer = a.get("user_answer")
            correct_answer = a.get("correct_answer")
            if user_answer in (None, "", "Нет ответа"):
                unanswered += 1
                verdict = "unanswered"
            elif _is_correct(user_answer, correct_answer):
                verdict = "correct"
            else:
                verdict = "wrong"

            entry = history.setdefault(
                question.casefold(),
                {
                    "topic": a.get("category") or "не указана",
                    "question": question[:300],
                    "options": [],
                    "correct_answer": _short(correct_answer),
                    "seen": [],
                },
            )
            if not entry["options"] and a.get("options"):
                entry["options"] = [_short(o)[:160] for o in a["options"]][:8]
            entry["seen"].append(
                {
                    "attempt": attempt_no,
                    "answer": _short(user_answer) if user_answer not in (None, "", "Нет ответа") else None,
                    "result": verdict,
                }
            )

    errors = []
    for entry in history.values():
        seen = entry["seen"]
        last = seen[-1]
        # Закрытый пробел: последний раз ответ был верным (или вопросов больше не было).
        if last["result"] == "correct":
            continue
        wrongs = [s for s in seen if s["result"] == "wrong"]
        if not wrongs:
            continue  # только пропуски без ответа — отдельная метрика, не пробел знаний
        options = entry["options"]
        errors.append(
            {
                "topic": entry["topic"],
                "question": entry["question"],
                # Варианты ответа дают модели контекст, чтобы понять суть пробела.
                "options": options,
                "student_answer": wrongs[-1]["answer"],
                "correct_answer": entry["correct_answer"],
                "wrong_count": len(wrongs),
                "attempts_tested": len(seen),
                # Если закрыт не был — показываем все неудачные попытки,
                # чтобы модель видела повторяемость заблуждения.
                "history": [
                    {"attempt": s["attempt"], "answer": s["answer"], "result": s["result"]}
                    for s in seen
                ],
            }
        )
        if len(errors) >= max_errors:
            break

    closed_gaps = sum(
        1
        for e in history.values()
        if e["seen"][-1]["result"] == "correct" and any(s["result"] == "wrong" for s in e["seen"])
    )
    persistent = sum(1 for e in errors if e["wrong_count"] >= 2)

    facts = {
        "attempts": attempts,
        "period": {
            "first": ordered[0].get("start_time"),
            "last": ordered[-1].get("start_time"),
        },
        "tests": sorted({r.get("test_name") for r in ordered if r.get("test_name")}),
        "average_score": round(sum(scores) / attempts, 1) if attempts else 0.0,
        "best_score": round(max(scores), 1) if scores else 0.0,
        "worst_score": round(min(scores), 1) if scores else 0.0,
        "score_std": round(statistics.pstdev(scores), 1) if len(scores) > 1 else 0.0,
        "passes": passed,
        "pass_rate": round((passed / attempts) * 100, 1) if attempts else 0.0,
        "total_answers": total_answers,
        "unanswered": unanswered,
        "open_gaps": len(errors),
        "persistent_gaps": persistent,
        "closed_gaps": closed_gaps,
        "average_duration_seconds": round(sum(durations) / len(durations)) if durations else None,
        "topics": topic_stats,
        "dynamics": {"trend": trend, "delta": delta},
    }
    return facts, errors


def level_from_score(average_score: float) -> str:
    if average_score < 50:
        return "начальный"
    if average_score < 70:
        return "базовый"
    if average_score < 85:
        return "уверенный"
    return "продвинутый"


def risk_from_facts(facts: dict) -> str:
    avg = facts.get("average_score") or 0
    pass_rate = facts.get("pass_rate") or 0
    if avg < 50 or pass_rate < 50:
        return "высокий"
    if avg < 70 or pass_rate < 75:
        return "средний"
    return "низкий"
