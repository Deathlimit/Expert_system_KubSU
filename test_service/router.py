import logging
import random
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header

from database import get_col, clean, CONTENT_SERVICE_URL, SESSION_SERVICE_URL, get_users_col
from security import get_current_user, get_auth_header
from models import CreateTestBody, AssignBody, BatchAssignBody, GenerateTestBody, AddQuestionsBody, RenameTestBody, UpdateTestSettingsBody

logger = logging.getLogger(__name__)

router = APIRouter()


def _strip_correct(t: dict) -> dict:
    # Удаление правильных ответов (для студентов)
    if "questions" in t:
        t = dict(t)
        t["questions"] = [{k: v for k, v in q.items() if k != "correct"} for q in t["questions"]]
    return t


def _enrich_creator(tests: list) -> list:
    # Добавление ФИО создателя к тестам
    usernames = list({t.get("creator_username") for t in tests if t.get("creator_username")})
    if not usernames:
        return tests
    users = {u["username"]: u.get("full_name", "") for u in get_users_col().find({"username": {"$in": usernames}}, {"username": 1, "full_name": 1})}
    for t in tests:
        cu = t.get("creator_username", "")
        t["creator_full_name"] = users.get(cu) or cu
    return tests


# Получение списка тестов
@router.get("/tests")
async def list_tests(user=Depends(get_current_user)):
    if user["role"] == "student":
        return [_strip_correct(clean(t)) for t in get_col().find({"assigned_students": user["sub"]}, {"_id": 0})]
    return _enrich_creator([clean(t) for t in get_col().find({}, {"_id": 0})])


# Получение тестов по создателю
@router.get("/tests/creator/{username}")
async def list_tests_by_creator(username: str, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    return _enrich_creator([clean(t) for t in get_col().find({"creator_username": username}, {"_id": 0})])


# Получение назначенных тестов студенту
@router.get("/tests/assigned/{student_username}")
async def get_assigned_tests(student_username: str, user=Depends(get_current_user)):
    is_student = user["role"] == "student"
    _name_cache: dict = {}
    def _creator_display(username: str) -> str:
        if username not in _name_cache:
            u = get_users_col().find_one({"username": username}, {"full_name": 1})
            _name_cache[username] = (u.get("full_name") if u else None) or username
        return _name_cache[username]

    result: dict = {}
    for t in get_col().find({"assigned_students": student_username}, {"_id": 0}):
        creator = t.get("creator_username", "Неизвестный преподаватель")
        display = _creator_display(creator)
        t_clean = _strip_correct(t) if is_student else t
        t_clean["creator_full_name"] = display
        result.setdefault(display, []).append(t_clean)
    for teacher in result:
        result[teacher].sort(key=lambda x: x.get("test_name", ""))
    return result


# Получение теста по ID
@router.get("/tests/{test_id}")
async def get_test(test_id: str, user=Depends(get_current_user)):
    t = get_col().find_one({"test_id": test_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    t = clean(t)
    _enrich_creator([t])
    if user["role"] == "student":
        t = dict(t)
        if "questions" in t:
            t["questions"] = [
                {k: v for k, v in q.items() if k != "correct"}
                for q in t["questions"]
            ]
    return t


# Создание нового теста
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
        "grading_mode": body.grading_mode or "overall",
    })
    return {"test_id": test_id, "message": f"Тест '{body.test_name}' успешно создан."}


# Переименование теста
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


# Обновление настроек теста
@router.put("/tests/{test_id}/settings")
async def update_test_settings(test_id: str, body: UpdateTestSettingsBody, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    t = get_col().find_one({"test_id": test_id})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    updates = {
        "time_limit_minutes": body.time_limit_minutes,
        "cooldown_hours": body.cooldown_hours if body.cooldown_hours is not None else 0,
        "max_attempts": body.max_attempts,
    }
    if body.grading_mode is not None:
        updates["grading_mode"] = body.grading_mode
    get_col().update_one({"test_id": test_id}, {"$set": updates})
    logger.info("Test '%s' settings updated by %s", test_id, user["sub"])
    return {"message": "Настройки теста обновлены."}


# Клонирование теста
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
        "grading_mode": t.get("grading_mode", "overall"),
    }
    get_col().insert_one(clone)
    logger.info("Test '%s' cloned as '%s' by %s", test_id, new_id, user["sub"])
    return {"test_id": new_id, "message": f"Тест '{t['test_name']}' клонирован.", "test": {k: v for k, v in clone.items() if k != "_id"}}


# Удаление теста
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
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.delete(
                f"{CONTENT_SERVICE_URL}/content/criteria/test/{test_id}",
                headers=get_auth_header(authorization),
            )
    except Exception:
        pass  # Do not fail the delete if criteria cleanup fails
    return {"message": f"Тест '{t.get('test_name', '')}' удалён."}


# Удаление вопроса из теста
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


# Добавление вопросов в тест
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


# Назначение студента на тест
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


# Открепление студента от теста
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


# Массовое назначение студентов
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


# ------------------------------------------------------------------
# Эндпоинты для ссылок приглашения
# ------------------------------------------------------------------

# Создание ссылки приглашения
@router.post("/tests/{test_id}/share")
async def share_test(test_id: str, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    t = get_col().find_one({"test_id": test_id})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    share_token = t.get("share_token")
    if not share_token:
        share_token = uuid.uuid4().hex
        get_col().update_one({"test_id": test_id}, {"$set": {"share_token": share_token}})
    return {"share_token": share_token, "message": "Ссылка для приглашения создана."}


# Удаление ссылки приглашения
@router.delete("/tests/{test_id}/share")
async def unshare_test(test_id: str, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    t = get_col().find_one({"test_id": test_id})
    if not t:
        raise HTTPException(404, "Тест не найден.")
    get_col().update_one({"test_id": test_id}, {"$unset": {"share_token": ""}})
    return {"message": "Ссылка для приглашения отозвана."}


# Получение информации о тесте по ссылке
@router.get("/tests/shared/{share_token}")
async def get_shared_test_info(share_token: str):
    t = get_col().find_one({"share_token": share_token}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Ссылка недействительна или тест не найден.")
    return {
        "test_id": t["test_id"],
        "test_name": t.get("test_name", ""),
        "question_count": len(t.get("questions", [])),
        "time_limit_minutes": t.get("time_limit_minutes"),
        "grading_mode": t.get("grading_mode", "overall"),
        "creator_username": t.get("creator_username", ""),
    }


# Присоединение к тесту по ссылке
@router.post("/tests/shared/{share_token}/join")
async def join_test_by_share(share_token: str, authorization: str = Header(...), user=Depends(get_current_user)):
    t = get_col().find_one({"share_token": share_token}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Ссылка недействительна или тест не найдена.")
    test_id = t["test_id"]
    assigned = t.get("assigned_students", [])
    username = user["sub"]
    role = user.get("role", "student")

    # Преподаватели не могут проходить тесты по ссылке
    if role not in ("student", "admin"):
        return {
            "test_id": test_id,
            "test_name": t.get("test_name", ""),
            "already_assigned": False,
            "role_restricted": True,
            "message": "Преподаватели не могут проходить тесты по ссылке приглашения.",
        }

    # Проверка: учетная запись не активирована
    if role == "unassigned":
        return {
            "test_id": test_id,
            "test_name": t.get("test_name", ""),
            "already_assigned": False,
            "account_not_activated": True,
            "message": "Ваша учетная запись не активирована. Обратитесь к преподавателю.",
        }

    # Проверка: есть ли активная сессия для другого теста
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp_active = await client.get(
                f"{SESSION_SERVICE_URL}/sessions/active",
                headers=get_auth_header(authorization),
            )
            if resp_active.status_code == 200:
                active_data = resp_active.json()
                if active_data.get("active") and active_data.get("test_id") != test_id:
                    return {
                        "test_id": test_id,
                        "test_name": t.get("test_name", ""),
                        "already_assigned": False,
                        "has_active_session": True,
                        "active_test_id": active_data.get("test_id"),
                        "active_test_name": active_data.get("test_name"),
                        "message": "У вас уже есть активный тест. Завершите его прежде чем присоединяться к новому.",
                    }
    except httpx.RequestError:
        pass  # Если сервис недоступен, продолжаем

    was_assigned = username in assigned
    if not was_assigned:
        get_col().update_one({"test_id": test_id}, {"$push": {"assigned_students": username}})
        logger.info("Auto-assigned user %s to test %s via share link", username, test_id)

    return {
        "test_id": test_id,
        "test_name": t.get("test_name", ""),
        "already_assigned": was_assigned,
        "message": f"Вы назначены на тест '{t.get('test_name', '')}'.",
    }


# Генерация теста по теме
@router.post("/tests/generate")
async def generate_test(
    body: GenerateTestBody,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    # Генерация теста по теме и максимальному баллу
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
