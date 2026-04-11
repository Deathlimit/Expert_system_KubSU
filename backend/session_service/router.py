import logging
import random
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header
from pymongo import DESCENDING

from database import get_col, CONTENT_SERVICE_URL, TEST_SERVICE_URL
from security import get_current_user, auth_header
from models import StartSessionBody, SubmitAnswerBody
from session import TestSession

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory store of active sessions (not persisted across restarts)
_sessions: dict = {}

# Maximum time (in hours) before a stale session is auto-removed
_SESSION_STALE_HOURS = 6


# ------------------------------------------------------------------
# Session lifecycle
# ------------------------------------------------------------------

@router.post("/sessions/start")
async def start_session(
    body: StartSessionBody,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    username = user["sub"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        if body.test_id:
            # Fetch test data first (needed for eligibility check + session creation)
            try:
                resp_test = await client.get(
                    f"{TEST_SERVICE_URL}/tests/{body.test_id}",
                    headers=auth_header(authorization),
                )
            except httpx.RequestError as e:
                logger.error("Failed to reach test service: %s", e)
                raise HTTPException(502, "Сервис тестов недоступен.")
            if resp_test.status_code != 200:
                raise HTTPException(502, "Не удалось получить данные теста.")
            test_data = resp_test.json()

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
                # Fall back to creator-specific or default criteria
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
                sampled = random.sample(available, min(num_needed, len(available)))
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
            session = TestSession(username, selected, criteria)

        else:
            raise HTTPException(400, "Укажите test_id или num_questions_per_category.")

    _cleanup_stale_sessions()
    _sessions[session.session_id] = session
    logger.info("Session %s started for user %s (test_id=%s)", session.session_id, username, body.test_id)
    return {
        "session_id": session.session_id,
        "total_questions": len(session.questions),
        "current_question": session.get_current_question(),
    }


@router.post("/sessions/{session_id}/answer")
async def submit_answer(session_id: str, body: SubmitAnswerBody, user=Depends(get_current_user)):
    session = _get_session(session_id, user["sub"])
    result = session.submit_answer(body.answer)
    if result.get("finished"):
        _sessions.pop(session_id, None)
    return result


@router.get("/sessions/{session_id}/status")
async def session_status(session_id: str, user=Depends(get_current_user)):
    session = _get_session(session_id, user["sub"])
    return {
        "session_id": session_id,
        "current_index": session.current_question_index,
        "total_questions": len(session.questions),
        "finished": session.current_question_index >= len(session.questions),
    }


# ------------------------------------------------------------------
# Teacher statistics by test
# ------------------------------------------------------------------

@router.get("/sessions/results/test/{test_id}")
async def get_results_for_test(test_id: str, user=Depends(get_current_user)):
    """Return all results for a specific premade test (teacher/admin only)."""
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    col = get_col()
    records = [
        {k: v for k, v in r.items() if k != "_id"}
        for r in col.find({"premade_test_id": test_id}).sort("start_time", DESCENDING)
    ]
    return records


@router.get("/sessions/results/test/{test_id}/stats")
async def get_test_aggregate_stats(test_id: str, user=Depends(get_current_user)):
    """Return aggregate statistics for a specific premade test."""
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    col = get_col()
    records = list(col.find({"premade_test_id": test_id}, {"_id": 0}))
    if not records:
        return {"total_attempts": 0, "unique_students": 0, "average_score": 0, "pass_rate": 0, "best_score": 0, "worst_score": 0}

    scores = [r.get("score_percentage", 0) for r in records if r.get("score_percentage") is not None]
    passed = sum(1 for r in records if r.get("final_status") in ("Зачёт", "Passed"))
    unique_students = len(set(r.get("username") for r in records if r.get("username")))

    return {
        "total_attempts": len(records),
        "unique_students": unique_students,
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "pass_rate": round((passed / len(records)) * 100, 1) if records else 0,
        "best_score": round(max(scores), 1) if scores else 0,
        "worst_score": round(min(scores), 1) if scores else 0,
    }


# ------------------------------------------------------------------
# History
# ------------------------------------------------------------------

@router.get("/sessions/history")
async def get_all_history(user=Depends(get_current_user)):
    col = get_col()
    return [{k: v for k, v in r.items() if k != "_id"} for r in col.find().sort("start_time", DESCENDING)]


@router.get("/sessions/history/{username}")
async def get_user_history(username: str, user=Depends(get_current_user)):
    col = get_col()
    records = [{k: v for k, v in r.items() if k != "_id"} for r in col.find({"username": username})]
    return _process_history(records)


# ------------------------------------------------------------------
# Eligibility (24-hour cooldown)
# ------------------------------------------------------------------

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
                headers=auth_header(authorization),
            )
            if r.status_code == 200:
                test_data = r.json()
    except Exception:
        pass
    is_eligible, message = _check_eligibility_internal(username, test_id, test_data)
    return {"eligible": is_eligible, "message": message}


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _get_session(session_id: str, username: str) -> TestSession:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Сессия не найдена.")
    if session.username != username:
        raise HTTPException(403, "Нет доступа к этой сессии.")
    return session


def _cleanup_stale_sessions() -> None:
    """Remove sessions that have been idle for too long."""
    now = datetime.now()
    stale_ids = [
        sid for sid, s in _sessions.items()
        if (now - s.start_time).total_seconds() > _SESSION_STALE_HOURS * 3600
    ]
    for sid in stale_ids:
        logger.info("Removing stale session: %s", sid)
        _sessions.pop(sid, None)


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
        # Use stored test_name if available, fallback to short ID
        name = r.get("test_name") or f"Готовый тест (ID: {pid[:8]}...)"
        processed.append({**r, "test_name": name, "attempt_number": counter})

    processed.extend(others)
    processed.sort(key=lambda x: x.get("start_time", ""), reverse=True)
    return processed


def _check_eligibility_internal(username: str, test_id: str, test_data: dict = None) -> tuple:
    """Check cooldown and attempt limit using per-test settings from test_data."""
    col = get_col()

    cooldown_hours = 24  # default
    max_attempts = None  # default: unlimited
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
