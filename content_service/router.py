import copy
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from database import get_db, get_questions_dict, get_criteria, DEFAULT_CRITERIA_KEY, DEFAULT_GRADING_CRITERIA
from security import get_current_user
from models import QuestionBody, CriteriaBody, BulkImportBody

logger = logging.getLogger(__name__)

router = APIRouter()


# Получение всех вопросов
@router.get("/content/questions")
async def get_questions(user=Depends(get_current_user)):
    return get_questions_dict(get_db())


# Получение списка категорий
@router.get("/content/categories")
async def get_categories(user=Depends(get_current_user)):
    return get_db()["questions"].distinct("topic")


# Массовый импорт вопросов
@router.post("/content/questions/import")
async def bulk_import_questions(body: BulkImportBody, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    db = get_db()
    imported = 0
    errors = []
    for i, q in enumerate(body.questions):
        topic = q.get("topic")
        question_text = q.get("question")
        options = q.get("options")
        correct = q.get("correct")
        if not topic or not question_text or not options or correct is None:
            errors.append(f"Вопрос #{i + 1}: отсутствуют обязательные поля (topic, question, options, correct).")
            continue
        doc = {
            "topic": topic,
            "question": question_text,
            "options": options,
            "correct": correct,
            "answer_type": q.get("answer_type", "single"),
        }
        if q.get("points"):
            doc["points"] = q["points"]
        if q.get("matrices"):
            doc["matrices"] = q["matrices"]
        if q.get("commands"):
            doc["commands"] = q["commands"]
        db["questions"].insert_one(doc)
        imported += 1
    logger.info("Bulk import: %d questions imported by %s", imported, user["sub"])
    result = {"message": f"Импортировано {imported} вопрос(ов).", "imported": imported}
    if errors:
        result["errors"] = errors
    return result


# Добавление вопроса в тему
@router.post("/content/questions/{topic}")
async def add_question(topic: str, body: QuestionBody, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    q = body.model_dump(exclude_none=True)
    q.pop("category", None)
    q["topic"] = topic
    get_db()["questions"].insert_one(q)
    logger.info("Question added to topic '%s' by %s", topic, user["sub"])
    return {"message": "Вопрос добавлен."}


# Обновление вопроса
@router.put("/content/questions/{topic}/{index}")
async def update_question(topic: str, index: int, body: QuestionBody, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    db = get_db()
    docs = list(db["questions"].find({"topic": topic}, {"_id": 1}))
    if not (0 <= index < len(docs)):
        raise HTTPException(404, "Вопрос не найден.")
    q = body.model_dump(exclude_none=True)
    q.pop("category", None)
    q["topic"] = topic
    db["questions"].replace_one({"_id": docs[index]["_id"]}, q)
    return {"message": "Вопрос обновлён."}


# Удаление вопроса
@router.delete("/content/questions/{topic}/{index}")
async def delete_question(topic: str, index: int, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    db = get_db()
    docs = list(db["questions"].find({"topic": topic}, {"_id": 1}))
    if not (0 <= index < len(docs)):
        raise HTTPException(404, "Вопрос не найден.")
    db["questions"].delete_one({"_id": docs[index]["_id"]})
    return {"message": "Вопрос удалён."}


# Получение критериев оценивания
@router.get("/content/criteria")
async def get_criteria_for_evaluation(
    creator_username: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    db = get_db()
    if creator_username:
        c = get_criteria(db, creator_username)
        if c:
            return c
    c = get_criteria(db, DEFAULT_CRITERIA_KEY)
    return c if c else copy.deepcopy(DEFAULT_GRADING_CRITERIA)


# Получение критериев для редактирования
@router.get("/content/criteria/for-editing")
async def get_criteria_for_editing(
    username: str = Query(...),
    role: str = Query(...),
    user=Depends(get_current_user),
):
    db = get_db()
    effective_role = user["role"]
    key = DEFAULT_CRITERIA_KEY if effective_role == "admin" else username
    c = get_criteria(db, key)
    return c if c else copy.deepcopy(DEFAULT_GRADING_CRITERIA)


# Сохранение критериев оценивания
@router.put("/content/criteria")
async def save_criteria(
    username: str = Query(...),
    role: str = Query(...),
    body: CriteriaBody = ...,
    user=Depends(get_current_user),
):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    db = get_db()
    effective_role = user["role"]
    if effective_role == "teacher" and username != user["sub"]:
        raise HTTPException(403, "Вы можете изменять только свои критерии.")
    key = DEFAULT_CRITERIA_KEY if effective_role == "admin" else username
    db["criteria"].update_one(
        {"key": key},
        {"$set": {"key": key, "topic_criteria": body.topic_criteria}},
        upsert=True,
    )
    return {"message": "Критерии успешно сохранены."}


# Получение критериев по умолчанию
@router.get("/content/criteria/defaults")
async def get_default_criteria(user=Depends(get_current_user)):
    return copy.deepcopy(DEFAULT_GRADING_CRITERIA)


# Получение критериев для конкретного теста
@router.get("/content/criteria/test/{test_id}")
async def get_test_criteria(test_id: str, user=Depends(get_current_user)):
    db = get_db()
    key = f"test::{test_id}"
    c = get_criteria(db, key)
    if c is None:
        raise HTTPException(404, "Критерии для этого теста не заданы.")
    return c


# Сохранение критериев для теста
@router.put("/content/criteria/test/{test_id}")
async def save_test_criteria(
    test_id: str,
    body: CriteriaBody,
    user=Depends(get_current_user),
):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    db = get_db()
    key = f"test::{test_id}"
    db["criteria"].update_one(
        {"key": key},
        {"$set": {"key": key, "topic_criteria": body.topic_criteria}},
        upsert=True,
    )
    return {"message": "Критерии для теста успешно сохранены."}


# Удаление критериев теста
@router.delete("/content/criteria/test/{test_id}")
async def delete_test_criteria(test_id: str, user=Depends(get_current_user)):
    if user["role"] not in ("teacher", "admin"):
        raise HTTPException(403, "Недостаточно прав.")
    db = get_db()
    key = f"test::{test_id}"
    db["criteria"].delete_one({"key": key})
    return {"message": "Критерии для теста удалены."}
