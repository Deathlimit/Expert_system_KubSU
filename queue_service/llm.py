"""Контракт с LLM: сборка запроса и разбор ответа.

Модуль детерминированный — он не вызывает модель. `/api/chat` выполняет
домашний воркер, а сервер собирает для него готовое тело запроса и
нормализует ответ, чтобы промпт и проверки не разъезжались между
сервером и воркером.
"""

import json
import logging
import re

from .features import level_from_score, risk_from_facts
from .llm_config import LLM_MAX_ERRORS, LLM_NUM_CTX, LLM_NUM_PREDICT, LLM_THINK, OLLAMA_MODEL

logger = logging.getLogger(__name__)

_PORTRAIT_RULES = """
Ты — опытный методист и аналитик образования. По результатам тестов студента ты составляешь объективный портрет его знаний и выявляешь пробелы.

Тебе передают ТОЛЬКО факты: статистику по темам, счётчики закрытых/открытых пробелов и список вопросов, где студент ошибался.

КАК ЧИТАТЬ ДАННЫЕ:
- `errors` содержит ТОЛЬКО вопросы, не исправленные к последней попытке. `closed_gaps` — счётчик исправленного, а не список: не придумывай, какие именно вопросы он закрыл.
- `wrong_count` — сколько раз студент ошибался на этом вопросе. `wrong_count >= 2` — устойчивое заблуждение, его приоритет выше.
- `attempts_tested` — сколько раз вопрос встречался. `wrong_count`, близкий к `attempts_tested`, — систематическая проблема.
- `history` — все ответы по попыткам (`result`: wrong/correct/unanswered). Смотри на `result`, а не только на последний `answer`.
- `topics[].percentage` — процент верных ответов по теме. `strengths` бери из тем, где процент высокий, и указывай цифру в скобках.
- `topic` — лишь подсказка автора теста. Область пробела формулируй по сути вопроса, а не копируй `topic`.
- Если `errors` пуст — `gaps` пустой массив, это хороший результат.

ГЛАВНОЕ ПРАВИЛО — НЕ ПРОПУСТИ ОШИБКУ И НЕ ПРОДУБЛИРУЙ ПРОБЕЛ:
1. Для каждой ошибки определи причину ОДНОЙ фразой.
2. Одна причина — одна область: все ошибки с этой причиной идут в её `evidence`.
3. Разные причины — разные области, даже внутри одной темы.
   - Плохо: отдельно «ссылки на списки» и «изменение списка в цикле», если обе про одно: `b = a` меняет `a`.
   - Хорошо: «Ссылочная модель: b = a делает псевдоним» — одна область с двумя evidence.
4. Каждая ошибка из `errors` попадает РОВНО в одну область. Областей не больше, чем ошибок, и ни одна ошибка не остаётся без области.

ТРЕБОВАНИЯ К ПОЛЯМ (пустых значений быть не может):
- `area` — навык на русском, 2-6 слов, без общих слов «основы», «работа с данными», «логика».
- `severity` — по влиянию на риск незачёта: «высокий» — базовая тема и повторяющаяся ошибка; «низкий» — единичная случайная.
- `evidence` — 1-3 факта: что студент ответил и что верно. При `wrong_count >= 2` укажи число повторов.
- `recommendation` — ОБЯЗАТЕЛЬНО непустое и конкретное: какой метод или правило повторить и на каких примерах. Плохо: «повторить тему». Хорошо: «Разобрать раздел про `strip()` и `range()` на коротких примерах кода».
- `confidence` — 0.5 при одном провале, до 0.8 при двух, до 0.9 если ошибается во всех попытках. Не 0.0 и не 1.0.
- `summary` — 2-3 предложения: уровень, главный пробел, прогресс (если `closed_gaps > 0`).
- `recommendations` — 2-4 конкретных действия, а не пересказ полей. Плохо: «повторить темы с низкой уверенностью».
- Не используй имена и персональные данные. Не выдумывай понятия, которых нет в данных.
"""

_SCHEMA = """
{
  "level": "начальный | базовый | уверенный | продвинутый",
  "summary": "2-3 предложения общего вывода",
  "strengths": ["сильная сторона (цифра)", "..."],
  "gaps": [
    {
      "area": "конкретный навык",
      "severity": "низкий | средний | высокий",
      "confidence": 0.0,
      "evidence": ["краткая формулировка ошибки", "..."],
      "recommendation": "что именно повторить и на каких примерах"
    }
  ],
  "dynamics": "рост | стабильно | падение | недостаточно данных",
  "recommendations": ["конкретное действие", "..."]
}
"""

# Без рассуждения: модель может отвечать сразу. Это самый быстрый режим.
_ANSWER_FORMAT_PLAIN = "Верни СТРОГО JSON без пояснений и markdown по схеме:\n" + _SCHEMA

# С рассуждением: модель получает отдельный бюджет на размышление.
# Gemma рассуждает по-английски и пересказывает задание заново (наблюдалось
# 44 176 симв. thinking и пустой content), поэтому рассуждению нужен предел.
_ANSWER_FORMAT_THINKING = (
    "Сначала подумай над данными, но кратко: не больше 15 предложений.\n"
    "Затем верни СТРОГО JSON без markdown по схеме:\n"
    + _SCHEMA
    + "\n\nПиши на русском. Не пересказывай задание целиком."
)


def build_system_prompt(think: bool) -> str:
    """Промпт под выбранный режим: с рассуждением или без."""
    return _PORTRAIT_RULES + "\n" + (_ANSWER_FORMAT_THINKING if think else _ANSWER_FORMAT_PLAIN)


SYSTEM_PROMPT = build_system_prompt(False)


def _parse_json(content: str) -> dict:
    text = (content or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response does not contain JSON object")
    return json.loads(text[start : end + 1])


def _as_list(value, limit: int, item_limit: int = 200) -> list:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if isinstance(item, (str, int, float)):
            text = str(item).strip()
        elif isinstance(item, dict):
            text = str(item.get("area") or item.get("text") or "").strip()
        else:
            continue
        if text:
            result.append(text[:item_limit])
        if len(result) >= limit:
            break
    return result


def _severity(value) -> str:
    text = str(value or "").strip().casefold()
    mapping = {
        "low": "низкий",
        "medium": "средний",
        "high": "высокий",
        "низкий": "низкий",
        "средний": "средний",
        "высокий": "высокий",
    }
    return mapping.get(text, "средний")


def _confidence(value, default: float = 0.6) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return round(min(max(number, 0.0), 1.0), 2)


def _normalize_gaps(value) -> list:
    if not isinstance(value, list):
        return []
    gaps = []
    for item in value:
        if not isinstance(item, dict):
            continue
        area = _clean_area(str(item.get("area") or ""))
        if not area:
            continue
        gaps.append(
            {
                "area": area[:120],
                "severity": _severity(item.get("severity")),
                "confidence": _confidence(item.get("confidence")),
                "evidence": _as_list(item.get("evidence"), 3, 160),
                "recommendation": str(item.get("recommendation") or "").strip()[:300],
            }
        )
        # Раньше здесь стоял жёсткий предел 7: на студенте с 12 пробелами
        # сервер молча отбрасывал сеть и ОС. Держим предел по числу ошибок,
        # которые вообще передаются модели.
        if len(gaps) >= LLM_MAX_ERRORS:
            break
    return gaps


def _normalize_dynamics(value, facts: dict) -> str:
    text = str(value or "").strip().casefold()
    allowed = {"рост", "стабильно", "падение", "недостаточно данных"}
    if text in allowed:
        return text
    return facts.get("dynamics", {}).get("trend") or "недостаточно данных"


_WORD_RE = re.compile(r"[а-яёa-z]{4,}")


def _stem(token: str) -> str:
    """Грубая основа: обрезает падежные окончания, чтобы «ошибки» и «ошибка» совпали."""
    for suffix in (
        "иями", "ями", "ами", "ов", "ев", "ей", "ой", "ый", "ий", "ая", "яя",
        "ое", "ее", "ые", "ие", "ия", "ии", "ах", "ях", "ам", "ям", "ом", "ем",
        "у", "ю", "а", "я", "ы", "и", "е", "о", "ь",
    ):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def _words(text: str) -> set:
    if not text:
        return set()
    return {_stem(token) for token in _WORD_RE.findall(text.casefold())}


def _area_signature(gap: dict) -> set:
    """Слова, по которым область можно сопоставить с ошибкой."""
    return _words(" ".join([gap.get("area") or ""] + list(gap.get("evidence") or [])))


def _error_signature(error: dict) -> set:
    return _words(
        " ".join([error.get("question") or "", error.get("topic") or "", error.get("correct_answer") or ""])
    )


def _clean_area(area: str) -> str:
    """Причёсывает название области: заглавная первая буква, без хвостовых точек.

    Модели возвращают названия в любом регистре («Границы итогов в цикле range»,
    «различие методов remove и pop»); приводим к единому виду.
    """
    text = re.sub(r"\s+", " ", (area or "").strip()).rstrip(".")
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _assign_errors_to_gaps(gaps: list, errors: list) -> list:
    """Ставит ошибки в соответствие областям; возвращает список по областям.

    Порядок — последний резерв, а не основа: в реальном прогоне модель
    перечислила области не в том порядке, что ошибки, и уверенность
    уезжала к чужим пробелам. Поэтому сначала совпадение по словам,
    и только нераспределённые ошибки идут в оставшиеся области по порядку.
    """
    remaining = list(errors)
    assigned = [[] for _ in gaps]

    # 1. Совпадение по словам (жадно, от наиболее специфичной области).
    def specificity(i: int) -> int:
        words = _area_signature(gaps[i])
        return max((len(words & _error_signature(e)) for e in errors), default=0)

    for i in sorted(range(len(gaps)), key=specificity, reverse=True):
        area_words = _area_signature(gaps[i])
        if not area_words:
            continue
        scored = [(len(area_words & _error_signature(e)), e) for e in remaining]
        scored = [(score, e) for score, e in scored if score >= 2]
        if not scored:
            continue
        best = max(score for score, _ in scored)
        # Все ошибки с одинаковой близостью идут в эту область...
        picked = [e for score, e in scored if score == best]
        # ...но не больше одной ошибки на область: иначе один повтор
        # раздувает уверенность сразу нескольких пробелов.
        assigned[i] = picked[:1]
        for e in assigned[i]:
            if e in remaining:
                remaining.remove(e)

    # 2. Область без совпадений получает повторяющуюся ошибку, если такая
    #    осталась: именно повторы — главный сигнал уверенности.
    for i, group in enumerate(assigned):
        if group:
            continue
        repeats = [e for e in remaining if int(e.get("wrong_count") or 1) >= 2]
        if repeats:
            assigned[i] = repeats[:1]
            remaining.remove(repeats[0])
        elif remaining:
            assigned[i] = remaining[:1]
            remaining.remove(remaining[0])

    return assigned


def _confidence_from_matches(matched: list) -> float:
    """Уверенность по ошибкам, отнесённым к области.

    Уверенность — это доля опоры на данные, а не убеждённость модели:
    - одиночная ошибка без повтора .............. 0.5
    - повторена 2 раза .......................... 0.75
    - повторена во всех попытках, где встречалась . 0.9
    """
    if not matched:
        return 0.5
    ratio = max(
        (int(e.get("wrong_count") or 1) / max(int(e.get("attempts_tested") or 1), 1))
        for e in matched
    )
    repeats = max(int(e.get("wrong_count") or 1) for e in matched)
    if repeats == 1:
        return 0.5
    # Потолок 0.9 — как обещает комментарий и требование к полю confidence.
    return round(0.5 + min(0.4, ratio * 0.4), 2)


def _dedupe_gaps(gaps: list) -> list:
    """Убирает области-дубли, которые модель иногда выдаёт повтором.

    Одинаковые названия в разных регистрах/формулировках склеиваются,
    evidence объединяется. Пустые названия отбрасываются.
    """
    merged: dict = {}
    for gap in gaps:
        area = re.sub(r"\s+", " ", (gap.get("area") or "").strip().casefold())
        area = re.sub(r"^(проблемы?|пробелы?)\s+(с|в)\s+", "", area)
        if not area:
            continue
        if area in merged:
            existing = merged[area]
            for ev in gap.get("evidence") or []:
                if ev not in existing["evidence"]:
                    existing["evidence"].append(ev)
            existing["evidence"] = existing["evidence"][:3]
            continue
        merged[area] = gap
    gaps[:] = list(merged.values())
    return gaps


def _check_confidence(gaps: list, errors: list) -> list:
    """Заменяет самооценку модели расчётом по данным."""
    groups = _assign_errors_to_gaps(gaps, errors)
    for gap, matched in zip(gaps, groups):
        gap["confidence"] = _confidence_from_matches(matched)
    return gaps


def normalize_portrait(data: dict, facts: dict, errors: list) -> dict:
    average = facts.get("average_score") or 0
    # Уровень — арифметика по среднему баллу, как и риск: в промпте нет
    # порогов, поэтому модель называет уровень произвольно (qwen3:8b на
    # данных со средним 63.9% выдала «начальный» вместо «базового»).
    level = level_from_score(average)

    summary = str(data.get("summary") or "").strip()
    if not summary:
        summary = (
            f"Студент выполнил {facts.get('attempts', 0)} попыток со средним результатом "
            f"{average}%. Зачёт получен в {facts.get('passes', 0)} из {facts.get('attempts', 0)} попыток."
        )

    gaps = _normalize_gaps(data.get("gaps"))
    _dedupe_gaps(gaps)
    if not gaps and errors:
        by_topic: dict = {}
        for error in errors:
            by_topic.setdefault(error.get("topic") or "не указана", []).append(error)
        for topic, topic_errors in list(by_topic.items())[:5]:
            gaps.append(
                {
                    "area": topic,
                    "severity": "средний",
                    "confidence": 0.5,
                    "evidence": [e.get("question", "")[:120] for e in topic_errors[:2]],
                    "recommendation": f"Повторить тему «{topic}» и разобрать похожие вопросы.",
                }
            )

    gaps = _check_confidence(gaps, errors)

    # Риск незачёта — арифметика, а не мнение модели: балл и доля зачётов
    # считаются по фактам. LLM склонна завышать его из-за одного слабого раздела
    # (наблюдалось: avg 72.5%, pass_rate 100% — модель выдала «средний»).
    risk = risk_from_facts(facts)

    return {
        "level": level,
        "summary": summary[:800],
        "strengths": _as_list(data.get("strengths"), 6, 160),
        "gaps": gaps,
        "dynamics": _normalize_dynamics(data.get("dynamics"), facts),
        "risk_of_failing": risk,
        "recommendations": _as_list(data.get("recommendations"), 6, 240),
    }


def fallback_portrait(facts: dict, errors: list) -> dict:
    average = facts.get("average_score") or 0
    topics = facts.get("topics") or []
    strengths = [t["topic"] for t in topics if t["percentage"] >= 80][:5]
    weak = [t for t in topics if t["percentage"] < 70]

    gaps = []
    for topic in weak[:5]:
        severity = "высокий" if topic["percentage"] < 40 else "средний"
        gaps.append(
            {
                "area": topic["topic"],
                "severity": severity,
                "confidence": 0.6,
                "evidence": [f"Верных ответов по теме: {topic['percentage']}%"],
                "recommendation": f"Повторить тему «{topic['topic']}».",
            }
        )

    recommendations = [f"Повторить тему «{t['topic']}»." for t in weak[:4]]
    if not recommendations:
        recommendations = ["Поддерживать уровень: решать более сложные задания."]

    return {
        "level": level_from_score(average),
        "summary": (
            f"Студент выполнил {facts.get('attempts', 0)} попыток со средним результатом "
            f"{average}%. Зачёт получен в {facts.get('passes', 0)} из {facts.get('attempts', 0)} попыток."
        ),
        "strengths": strengths,
        "gaps": gaps,
        "dynamics": facts.get("dynamics", {}).get("trend") or "недостаточно данных",
        "risk_of_failing": risk_from_facts(facts),
        "recommendations": recommendations,
    }


def build_request(facts: dict, errors: list, model: str, think: bool) -> dict:
    """Тело запроса к Ollama — готовое для домашнего воркера.

    Задание, которое Render отдаёт воркеру, приходит с готовым request body:
    воркер не собирает промпт сам и не может разойтись с сервером.
    """
    payload_errors = errors[:LLM_MAX_ERRORS]
    return {
        "model": model,
        "messages": [
            # Промпт зависит от режима: с рассуждением модели нужен свой
            # бюджет и запрет пересказывать задание, иначе она упирается
            # в num_predict и отдаёт пустой content.
            {"role": "system", "content": build_system_prompt(think)},
            {"role": "user", "content": json.dumps({"facts": facts, "errors": payload_errors}, ensure_ascii=False)},
        ],
        "stream": False,
        "format": "json",
        # qwen3 при think=true кладёт рассуждения в служебное поле `thinking`,
        # а в `content` возвращает чистый JSON — именно это нужно для `format: json`.
        "think": think,
        "options": {
            "temperature": 0.2,
            "num_ctx": LLM_NUM_CTX,
            "num_predict": LLM_NUM_PREDICT,
        },
    }


def parse_response(response: dict, facts: dict, errors: list) -> dict:
    """Разбор ответа Ollama — тоже общий: воркер и сервис нормализуют одинаково."""
    content = (response.get("message") or {}).get("content") or ""
    # done_reason="length" — модель не успела закончить ответ, обрезанный JSON
    # не парсится. Лучше отдать точный диагноз, чем «response does not contain JSON».
    if response.get("done_reason") == "length" and not content.strip():
        raise ValueError(
            f"LLM упёрлась в num_predict={LLM_NUM_PREDICT} и вернула пустой content "
            f"(модель {response.get('model') or OLLAMA_MODEL}, think={LLM_THINK}). Увеличьте "
            f"LLM_NUM_PREDICT или отключите рассуждение: LLM_THINK=false."
        )
    return normalize_portrait(_parse_json(content), facts, errors)
