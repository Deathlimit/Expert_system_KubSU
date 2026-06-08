import logging
import random
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header
from pymongo import DESCENDING

from database import get_col, get_active_sessions_col, CONTENT_SERVICE_URL, TEST_SERVICE_URL
from security import get_current_user, auth_header, service_auth_header
from models import StartSessionBody, SubmitAnswerBody
from session import TestSession

logger = logging.getLogger(__name__)

router = APIRouter()

_sessions: dict = {}
_SESSION_STALE_HOURS = 6


def _save_session_to_db(session: TestSession):
    try:
        doc = session.to_dict()
        get_active_sessions_col().replace_one({"session_id": session.session_id}, doc, upsert=True)
    except Exception as e:
        logger.error("Failed to persist session %s to DB: %s", session.session_id, e)


def _load_session_from_db(session_id: str, username: str):
    doc = get_active_sessions_col().find_one({"session_id": session_id, "username": username})
    if not doc:
        return None
    return TestSession.from_dict(doc)


def _delete_session_from_db(session_id: str):
    try:
        result = get_active_sessions_col().delete_one({"session_id": session_id})
        logger.info("Deleted session %s from DB (matched=%d)", session_id, result.deleted_count)
    except Exception as e:
        logger.error("Failed to delete session %s from DB: %s", session_id, e)


def _delete_all_sessions_for_user(username: str):
    try:
        result = get_active_sessions_col().delete_many({"username": username})
        if result.deleted_count > 0:
            logger.info("Cleaned up %d orphaned session(s) for user %s", result.deleted_count, username)
        to_remove = [sid for sid, s in _sessions.items() if s.username == username]
        for sid in to_remove:
            _sessions.pop(sid, None)
    except Exception as e:
        logger.error("Failed to clean sessions for user %s: %s", username, e)


def _find_active_session_for_user(username: str):
    doc = get_active_sessions_col().find_one({"username": username})
    if not doc:
        return None
    return TestSession.from_dict(doc)


def _auto_finish_expired(session: TestSession) -> dict:
    while session.current_question_index < len(session.questions):
        session.user_answers.append(None)
        session.current_question_index += 1
    results = session._evaluate_and_finish()
    _delete_session_from_db(session.session_id)
    _sessions.pop(session.session_id, None)
    return results


# Получение активной сессии пользователя
@router.get("/sessions/active")
async def get_active_session(user=Depends(get_current_user)):
    session = _find_active_session_for_user(user["sub"])
    if not session:
        return {"active": False}
    if session.is_time_expired():
        results = _auto_finish_expired(session)
        if not session.show_results_to_students:
            results.pop("score_percentage", None)
            results.pop("category_scores", None)
            results.pop("correct_count", None)
        return {"active": False, "finished_expired": True, "results": results}
    if session.current_question_index >= len(session.questions):
        logger.warning("Found orphaned completed session %s for user %s, cleaning up", session.session_id, user["sub"])
        _delete_session_from_db(session.session_id)
        _sessions.pop(session.session_id, None)
        return {"active": False}
    return {
        "active": True,
        "session_id": session.session_id,
        "test_id": session.premade_test_id,
        "test_name": session.test_name,
        "current_question_index": session.current_question_index,
        "total_questions": len(session.questions),
        "current_question": session.get_current_question(),
        "past_questions": session.get_past_questions(),
        "past_answers": session.user_answers[:session.current_question_index],
    }


# Начало новой сессии тестирования
@router.post("/sessions/start")
async def start_session(
    body: StartSessionBody,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    username = user["sub"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        if body.test_id:
            existing = _find_active_session_for_user(username)
            if existing:
                if existing.current_question_index >= len(existing.questions):
                    logger.warning("Cleaning up orphaned completed session %s", existing.session_id)
                    _delete_session_from_db(existing.session_id)
                    _sessions.pop(existing.session_id, None)
                    existing = None

            if existing:
                if existing.premade_test_id == body.test_id:
                    if existing.is_time_expired():
                        results = _auto_finish_expired(existing)
                        return {"finished": True, "results": results, "timed_out": True}
                    logger.info("Resuming session %s for user %s", existing.session_id, username)
                    return {
                        "session_id": existing.session_id,
                        "total_questions": len(existing.questions),
                        "current_question": existing.get_current_question(),
                        "resumed": True,
                        "past_questions": existing.get_past_questions(),
                        "past_answers": existing.user_answers[:existing.current_question_index],
                    }
                else:
                    raise HTTPException(409, "У вас уже есть активный тест. Завершите его прежде чем начинать новый.")

            try:
                resp_test = await client.get(
                    f"{TEST_SERVICE_URL}/tests/{body.test_id}",
                    headers=service_auth_header(),
                )
            except httpx.RequestError as e:
                logger.error("Failed to reach test service: %s", e)
                raise HTTPException(502, "Сервис тестов недоступен.")
            if resp_test.status_code != 200:
                raise HTTPException(502, "Не удалось получить данные теста.")
            test_data = resp_test.json()

            assigned = test_data.get("assigned_students", [])
            if user["role"] == "student" and username not in assigned:
                raise HTTPException(403, "Вы не назначены на этот тест.")

            is_eligible, elig_msg = _check_eligibility_internal(username, body.test_id, test_data)
            if not is_eligible:
                raise HTTPException(403, elig_msg)

            questions = test_data.get("questions", [])
            if not questions:
                raise HTTPException(400, "Тест не содержит вопросов.")

            try:
                resp2 = await client.get(
                    f"{CONTENT_SERVICE_URL}/content/criteria/test/{body.test_id}",
                    headers=auth_header(authorization),
                )
            except httpx.RequestError as e:
                logger.warning("Failed to fetch test-specific criteria: %s", e)
                resp2 = None
            if resp2 and resp2.status_code == 200:
                criteria = resp2.json()
            else:
                resp2 = await client.get(
                    f"{CONTENT_SERVICE_URL}/content/criteria",
                    headers=auth_header(authorization),
                    params={"creator_username": test_data.get("creator_username")} if test_data.get("creator_username") else {},
                )
                criteria = resp2.json() if resp2.status_code == 200 else {"topic_criteria": []}
            session = TestSession(
                username, questions, criteria,
                premade_test_id=body.test_id,
                test_name=test_data.get("test_name"),
                time_limit_minutes=test_data.get("time_limit_minutes"),
                grading_mode=test_data.get("grading_mode", "overall"),
                user_role=user["role"],
                show_results_to_students=test_data.get("show_results_to_students", True),
            )

        elif body.num_questions_per_category:
            try:
                resp = await client.get(
                    f"{CONTENT_SERVICE_URL}/content/questions",
                    headers=auth_header(authorization),
                )
            except httpx.RequestError as e:
                logger.error("Failed to reach content service: %s", e)
                raise HTTPException(502, "Сервис контента недоступен.")
            if resp.status_code != 200:
                raise HTTPException(502, "Не удалось получить вопросы.")
            all_questions = resp.json()

            selected = []
            for cat, num_needed in body.num_questions_per_category.items():
                available = all_questions.get(cat, [])
                if not available:
                    logger.warning(f"No questions available for category: {cat}")
                    continue
                num_to_sample = min(num_needed, len(available))
                if num_to_sample > 0:
                    sampled = random.sample(available, num_to_sample)
                    for q_orig in sampled:
                        q = dict(q_orig)
                        q["category"] = cat
                        selected.append(q)

            if not selected:
                raise HTTPException(400, "Не удалось сгенерировать вопросы для теста.")

            resp2 = await client.get(
                f"{CONTENT_SERVICE_URL}/content/criteria",
                headers=auth_header(authorization),
            )
            criteria = resp2.json() if resp2.status_code == 200 else {"topic_criteria": []}
            session = TestSession(username, selected, criteria, user_role=user["role"])

        else:
            raise HTTPException(400, "Укажите test_id или num_questions_per_category.")

    _cleanup_stale_sessions()
    _delete_all_sessions_for_user(username)
    _sessions[session.session_id] = session
    _save_session_to_db(session)
    logger.info("Session %s started for user %s (test_id=%s)", session.session_id, username, body.test_id)
    return {
        "session_id": session.session_id,
        "total_questions": len(session.questions),
        "current_question": session.get_current_question(),
    }


# Отправка ответа на вопрос
@router.post("/sessions/{session_id}/answer")
async def submit_answer(session_id: str, body: SubmitAnswerBody, user=Depends(get_current_user)):
    session = _get_session(session_id, user["sub"])
    result = session.submit_answer(body.answer)
    if result.get("finished"):
        _sessions.pop(session_id, None)
        _delete_session_from_db(session_id)
        if user["role"] == "student":
            results_inner = result.get("results") or result
            for a in results_inner.get("answers", []):
                a.pop("correct_answer", None)
            if not session.show_results_to_students:
                results_inner.pop("score_percentage", None)
                results_inner.pop("category_scores", None)
                results_inner.pop("correct_count", None)
    else:
        _sessions[session_id] = session
        _save_session_to_db(session)
    return result


# Получение статуса сессии
@router.get("/sessions/{session_id}/status")
async def session_status(session_id: str, user=Depends(get_current_user)):
    session = _get_session(session_id, user["sub"])
    return {
        "session_id": session_id,
        "current_index": session.current_question_index,
        "total_questions": len(session.questions),
        "finished": session.current_question_index >= len(session.questions),
    }


# Получение результатов теста
@router.get("/sessions/results/test/{test_id}")
async def get_results_for_test(test_id: str, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    col = get_col()
    records = [
        {k: v for k, v in r.items() if k != "_id"}
        for r in col.find({"premade_test_id": test_id}).sort("start_time", DESCENDING)
    ]
    return records


# Получение агрегированной статистики по тесту
@router.get("/sessions/results/test/{test_id}/stats")
async def get_test_aggregate_stats(test_id: str, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    col = get_col()
    records = list(col.find({"premade_test_id": test_id}, {"_id": 0}))
    if not records:
        return {
            "total_attempts": 0, "unique_students": 0, "average_score": 0,
            "pass_rate": 0, "best_score": 0, "worst_score": 0,
            "per_topic": {},
        }

    scores = [r.get("score_percentage", 0) for r in records if r.get("score_percentage") is not None]
    passed = sum(1 for r in records if r.get("final_status") in ("Зачёт", "Passed"))
    unique_students = len(set(r.get("username") for r in records if r.get("username")))

    topic_scores: dict = {}
    for r in records:
        cat_scores = r.get("category_scores", {})
        for cat, info in cat_scores.items():
            if isinstance(info, dict) and info.get("total", 0) > 0:
                topic_scores.setdefault(cat, []).append(info.get("percentage", 0))

    per_topic = {}
    for cat, pcts in topic_scores.items():
        if pcts:
            per_topic[cat] = {
                "average": round(sum(pcts) / len(pcts), 1),
                "best": round(max(pcts), 1),
                "worst": round(min(pcts), 1),
                "attempts": len(pcts),
            }

    return {
        "total_attempts": len(records),
        "unique_students": unique_students,
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "pass_rate": round((passed / len(records)) * 100, 1) if records else 0,
        "best_score": round(max(scores), 1) if scores else 0,
        "worst_score": round(min(scores), 1) if scores else 0,
        "per_topic": per_topic,
    }


# Получение всей истории (преподаватель/админ)
@router.get("/sessions/history")
async def get_all_history(user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    col = get_col()
    return [{k: v for k, v in r.items() if k != "_id"} for r in col.find().sort("start_time", DESCENDING)]


# Очистка истории
@router.delete("/sessions/history")
async def clear_history(
    username: str = None,
    test_id: str = None,
    user=Depends(get_current_user),
):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")

    col = get_col()
    query = {}
    if username:
        query["username"] = username
    if test_id:
        query["premade_test_id"] = test_id

    if not query:
        raise HTTPException(400, "Укажите username или test_id для очистки истории.")

    result = col.delete_many(query)
    return {"deleted": result.deleted_count}


# Получение истории пользователя
@router.get("/sessions/history/{username}")
async def get_user_history(username: str, user=Depends(get_current_user)):
    if user["role"] == "student" and user["sub"] != username:
        raise HTTPException(403, "Нет доступа к истории другого пользователя.")
    col = get_col()
    records = [{k: v for k, v in r.items() if k != "_id"} for r in col.find({"username": username})]
    processed = _process_history(records)
    if user["role"] == "student":
        for r in processed:
            for a in r.get("answers", []):
                a.pop("correct_answer", None)
            if not r.get("show_results_to_students", True):
                r.pop("score_percentage", None)
                r.pop("category_scores", None)
    return processed


# Проверка допуска к тесту
@router.get("/sessions/eligibility/{username}/{test_id}")
async def check_eligibility(
    username: str,
    test_id: str,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    test_data = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{TEST_SERVICE_URL}/tests/{test_id}",
                headers=service_auth_header(),
            )
            if r.status_code == 200:
                test_data = r.json()
    except Exception:
        pass
    is_eligible, message = _check_eligibility_internal(username, test_id, test_data)
    return {"eligible": is_eligible, "message": message}


def _get_session(session_id: str, username: str) -> TestSession:
    session = _sessions.get(session_id)
    if session:
        if session.username != username:
            raise HTTPException(403, "Нет доступа к этой сессии.")
        return session
    db_session = _load_session_from_db(session_id, username)
    if not db_session:
        raise HTTPException(404, "Сессия не найдена.")
    _sessions[session_id] = db_session
    return db_session


def _cleanup_stale_sessions() -> None:
    now = datetime.now()
    stale_ids = [
        sid for sid, s in _sessions.items()
        if (now - s.start_time).total_seconds() > _SESSION_STALE_HOURS * 3600
    ]
    for sid in stale_ids:
        logger.info("Removing stale session: %s", sid)
        _sessions.pop(sid, None)
    cutoff = (now - timedelta(hours=_SESSION_STALE_HOURS)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        get_active_sessions_col().delete_many({"start_time": {"$lt": cutoff}})
    except Exception:
        pass


def _process_history(user_history: list) -> list:
    premade = sorted(
        [r for r in user_history if r.get("premade_test_id")],
        key=lambda x: (x["premade_test_id"], x.get("start_time", "")),
    )
    others = [
        {**r, "test_name": r.get("test_name") or "Динамический тест", "attempt_number": "N/A"}
        for r in user_history if not r.get("premade_test_id")
    ]

    processed = []
    current_id, counter = None, 0
    for r in premade:
        pid = r["premade_test_id"]
        counter = 1 if pid != current_id else counter + 1
        current_id = pid
        name = r.get("test_name") or f"Готовый тест (ID: {pid[:8]}...)"
        processed.append({**r, "test_name": name, "attempt_number": counter})

    processed.extend(others)
    processed.sort(key=lambda x: x.get("start_time", ""), reverse=True)
    return processed


def _check_eligibility_internal(username: str, test_id: str, test_data: dict = None) -> tuple:
    col = get_col()

    cooldown_hours = 24
    max_attempts = None
    if test_data:
        raw_cd = test_data.get("cooldown_hours")
        cooldown_hours = raw_cd if raw_cd is not None else 24
        max_attempts = test_data.get("max_attempts")

    attempts = list(col.find(
        {"username": username, "premade_test_id": test_id},
        sort=[("end_time", DESCENDING)],
    ))

    if max_attempts is not None and len(attempts) >= max_attempts:
        return False, f"Вы исчерпали максимальное количество попыток ({max_attempts})."

    if cooldown_hours > 0 and attempts:
        last = attempts[0]
        end_str = last.get("end_time")
        if end_str and end_str != "N/A":
            try:
                elapsed = datetime.now() - datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
                cooldown = timedelta(hours=cooldown_hours)
                if elapsed < cooldown:
                    remaining = int((cooldown - elapsed).total_seconds())
                    hours, minutes = remaining // 3600, (remaining % 3600) // 60
                    return False, (
                        f"Вы уже проходили этот тест. "
                        f"Следующая попытка будет доступна через {hours} ч. {minutes} мин."
                    )
            except ValueError:
                pass

    return True, "Тест доступен для прохождения."
