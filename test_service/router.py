import logging
import random
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header

from database import get_col, clean, CONTENT_SERVICE_URL
from security import get_current_user, get_auth_header
from models import CreateTestBody, AssignBody, BatchAssignBody, GenerateTestBody, AddQuestionsBody, RenameTestBody

logger = logging.getLogger(__name__)

router = APIRouter()


def _strip_correct(t: dict) -> dict:
    """Remove 'correct' key from each question in a test dict (for student views)."""
    if "questions" in t:
        t = dict(t)
        t["questions"] = [{k: v for k, v in q.items() if k != "correct"} for q in t["questions"]]
    return t


@router.get("/tests")
async def list_tests(user=Depends(get_current_user)):
    if user["role"] == "student":
        # Students should only see tests assigned to them
        return [_strip_correct(clean(t)) for t in get_col().find({"assigned_students": user["sub"]}, {"_id": 0})]
    return [clean(t) for t in get_col().find({}, {"_id": 0})]


@router.get("/tests/creator/{username}")
async def list_tests_by_creator(username: str, user=Depends(get_current_user)):
    return [clean(t) for t in get_col().find({"creator_username": username}, {"_id": 0})]


@router.get("/tests/assigned/{student_username}")
async def get_assigned_tests(student_username: str, user=Depends(get_current_user)):
    """Return assigned tests grouped by teacher."""
    is_student = user["role"] == "student"
    result: dict = {}
    for t in get_col().find({"assigned_students": student_username}, {"_id": 0}):
        creator = t.get("creator_username", "Неизвестный преподаватель")
        result.setdefault(creator, []).append(_strip_correct(t) if is_student else t)
    for teacher in result:
        result[teacher].sort(key=lambda x: x.get("test_name", ""))
    return result


@router.get("/tests/{test_id}")
async def get_test(test_id: str, user=Depends(get_current_user)):
    t = get_col().find_one({"test_id": test_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    # Hide correct answers from students
    if user["role"] == "student":
        t = dict(t)
        if "questions" in t:
            t["questions"] = [
                {k: v for k, v in q.items() if k != "correct"}
                for q in t["questions"]
            ]
    return t


@router.post("/tests")
async def create_test(body: CreateTestBody, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    test_id = uuid.uuid4().hex
    get_col().insert_one({
        "test_id": test_id,
        "test_name": body.test_name,
        "creator_username": user["sub"],
        "creation_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "questions": body.questions,
        "assigned_students": [],
        "time_limit_minutes": body.time_limit_minutes,
        "cooldown_hours": body.cooldown_hours if body.cooldown_hours is not None else 24,
        "max_attempts": body.max_attempts,
    })
    return {"test_id": test_id, "message": f"Тест '{body.test_name}' успешно создан."}


@router.put("/tests/{test_id}/name")
async def rename_test(test_id: str, body: RenameTestBody, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    t = get_col().find_one({"test_id": test_id})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    get_col().update_one({"test_id": test_id}, {"$set": {"test_name": body.test_name}})
    logger.info("Test '%s' renamed to '%s' by %s", test_id, body.test_name, user["sub"])
    return {"message": f"Тест переименован в '{body.test_name}'."}


@router.post("/tests/{test_id}/clone")
async def clone_test(test_id: str, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    t = get_col().find_one({"test_id": test_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    new_id = uuid.uuid4().hex
    clone = {
        "test_id": new_id,
        "test_name": t["test_name"] + " (копия)",
        "creator_username": user["sub"],
        "creation_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "questions": list(t.get("questions", [])),
        "assigned_students": [],
        "time_limit_minutes": t.get("time_limit_minutes"),
        "cooldown_hours": t.get("cooldown_hours", 24),
        "max_attempts": t.get("max_attempts"),
    }
    get_col().insert_one(clone)
    logger.info("Test '%s' cloned as '%s' by %s", test_id, new_id, user["sub"])
    return {"test_id": new_id, "message": f"Тест '{t['test_name']}' клонирован.", "test": {k: v for k, v in clone.items() if k != "_id"}}


@router.delete("/tests/{test_id}")
async def delete_test(
    test_id: str,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    t = get_col().find_one({"test_id": test_id}, {"_id": 0, "test_name": 1})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    get_col().delete_one({"test_id": test_id})
    # Best-effort: remove per-test criteria from content_service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.delete(
                f"{CONTENT_SERVICE_URL}/content/criteria/test/{test_id}",
                headers=get_auth_header(authorization),
            )
    except Exception:
        pass  # Do not fail the delete if criteria cleanup fails
    return {"message": f"Тест '{t.get('test_name', '')}' удалён."}


@router.delete("/tests/{test_id}/questions/{index}")
async def delete_question_from_test(test_id: str, index: int, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    t = get_col().find_one({"test_id": test_id})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    qs = t.get("questions", [])
    if not (0 <= index < len(qs)):
        raise HTTPException(400, "Индекс вопроса вне диапазона.")
    qs.pop(index)
    get_col().update_one({"test_id": test_id}, {"$set": {"questions": qs}})
    return {"message": "Вопрос удалён из теста."}


@router.post("/tests/{test_id}/questions")
async def add_questions_to_test(test_id: str, body: AddQuestionsBody, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    t = get_col().find_one({"test_id": test_id})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    if not body.questions:
        raise HTTPException(400, "Список вопросов пуст.")
    get_col().update_one({"test_id": test_id}, {"$push": {"questions": {"$each": body.questions}}})
    updated = get_col().find_one({"test_id": test_id}, {"_id": 0})
    return {"message": f"Добавлено {len(body.questions)} вопрос(ов) в тест.", "test": updated}


@router.put("/tests/{test_id}/assign")
async def assign_student(test_id: str, body: AssignBody, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    t = get_col().find_one({"test_id": test_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    if body.student_username in t.get("assigned_students", []):
        raise HTTPException(409, "Студент уже назначен.")
    get_col().update_one({"test_id": test_id}, {"$push": {"assigned_students": body.student_username}})
    return {"message": f"Студент {body.student_username} назначен на тест '{t['test_name']}'."}


@router.put("/tests/{test_id}/unassign")
async def unassign_student(test_id: str, body: AssignBody, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    t = get_col().find_one({"test_id": test_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    if body.student_username not in t.get("assigned_students", []):
        raise HTTPException(404, "Студент не назначен на этот тест.")
    get_col().update_one({"test_id": test_id}, {"$pull": {"assigned_students": body.student_username}})
    return {"message": f"Студент {body.student_username} удалён с теста '{t['test_name']}'."}


@router.put("/tests/{test_id}/assignments")
async def batch_update_assignments(test_id: str, body: BatchAssignBody, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    t = get_col().find_one({"test_id": test_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    assigned = t.get("assigned_students", [])
    to_add = [s for s in body.assign if s not in assigned]
    to_remove = [s for s in body.unassign if s in assigned]

    messages = []
    if to_add:
        get_col().update_one({"test_id": test_id}, {"$push": {"assigned_students": {"$each": to_add}}})
        messages += [f"Назначен: {s}" for s in to_add]
    messages += [f"Уже назначен: {s}" for s in body.assign if s in assigned]
    if to_remove:
        get_col().update_one({"test_id": test_id}, {"$pull": {"assigned_students": {"$in": to_remove}}})
        messages += [f"Снят: {s}" for s in to_remove]
    messages += [f"Не был назначен: {s}" for s in body.unassign if s not in assigned]
    return {"messages": messages, "test": get_col().find_one({"test_id": test_id}, {"_id": 0})}


@router.post("/tests/generate")
async def generate_test(
    body: GenerateTestBody,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    """Generate a test by topic and max score, fetching questions from content service."""
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{CONTENT_SERVICE_URL}/content/questions",
                headers=get_auth_header(authorization),
            )
        except httpx.RequestError as e:
            logger.error("Failed to reach content service: %s", e)
            raise HTTPException(502, "Сервис контента недоступен.")
    if resp.status_code != 200:
        raise HTTPException(502, "Не удалось получить вопросы из сервиса контента.")

    topic_questions = resp.json().get(body.topic, [])
    if not topic_questions:
        raise HTTPException(404, f"Нет вопросов по теме '{body.topic}'.")

    random.shuffle(topic_questions)
    generated, total_score = [], 0
    for q_orig in topic_questions:
        q = dict(q_orig)
        if not q.get("category"):
            q["category"] = body.topic
        pts = q.get("points", 2 if q.get("answer_type") == "multiple" else 1)
        if total_score + pts <= body.max_score:
            q["points"] = pts
            generated.append(q)
            total_score += pts
        elif not generated and pts <= body.max_score:
            q["points"] = pts
            generated.append(q)
            total_score += pts
            break

    if not generated:
        raise HTTPException(404, f"Не удалось подобрать вопросы по теме '{body.topic}' на {body.max_score} баллов.")

    return {
        "questions": generated,
        "total_score": total_score,
        "message": f"Тест сформирован. Баллов: {total_score}/{body.max_score}.",
    }
