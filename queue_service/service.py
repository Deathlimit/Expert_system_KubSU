"""Бизнес-логика очереди задач на HTTP-поллинге.

Протокол:
  1. Фронт/бек POST /queue/tasks — ставит задачу (queued) и получает task_id.
     Для create_student_profile в payload сразу кладутся student, results,
     facts, errors и готовый request к Ollama (промпт собирает сервер).
  2. Воркер POST /queue/tasks/{task_id} без тела — задача переходит
     в in_progress, в ответ приходит её payload.
  3. Воркер POST /queue/tasks/{task_id} с {"result": ...} — результат
     сохраняется, задача переходит в done. result может быть сырым ответом
     Ollama /api/chat: сервер нормализует его через queue_service.llm.
"""

import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from pymongo import ReturnDocument

from .database import (
    LEASE_SECONDS,
    get_portrait_history_col,
    get_portraits_col,
    get_profiles_col,
    get_results_col,
    get_tasks_col,
    get_users_col,
    now_utc,
)
from .features import build_facts, input_hash, level_from_score, quick_stats
from .llm import build_request, fallback_portrait, parse_response
from .llm_config import LLM_MAX_ERRORS, LLM_THINK, OLLAMA_MODEL
from .models import DEFAULT_TASK_TYPE, CreateTaskBody

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("queued", "in_progress")
FINISHED_STATUSES = ("done", "failed")
ROLE_TEACHER = "teacher"
ROLE_ADMIN = "admin"
ROLE_STUDENT = "student"


def _iso(value):
    if isinstance(value, datetime):
        # PyMongo возвращает naive-даты (в UTC), хотя кладём мы aware.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return value


def public_task(doc: dict) -> dict:
    payload = doc.get("payload") or {}
    return {
        "task_id": doc.get("_id"),
        "type": doc.get("type"),
        "status": doc.get("status"),
        "username": doc.get("username") or payload.get("username"),
        "payload": payload,
        "result": doc.get("result"),
        "error": doc.get("error"),
        "attempts": doc.get("attempts", 0),
        "created_by": doc.get("created_by"),
        "created_at": _iso(doc.get("created_at")),
        "started_at": _iso(doc.get("started_at")),
        "finished_at": _iso(doc.get("finished_at")),
    }


def _check_read_access(doc: dict, user: dict) -> None:
    # Портрет студента — служебные данные преподавателя/администратора.
    if doc.get("type") == DEFAULT_TASK_TYPE:
        if user.get("role") not in (ROLE_TEACHER, ROLE_ADMIN):
            raise HTTPException(403, "Профиль студента доступен только преподавателю и администратору.")
        return
    if user.get("role") in (ROLE_TEACHER, ROLE_ADMIN):
        return
    if user.get("sub") in (doc.get("created_by"), doc.get("username")):
        return
    raise HTTPException(403, "Недостаточно прав.")


def _get_doc_or_404(task_id: str) -> dict:
    doc = get_tasks_col().find_one({"_id": task_id})
    if not doc:
        raise HTTPException(404, "Задача не найдена или истекла.")
    return doc


def create_task(body: CreateTaskBody, user: dict) -> dict:
    # Портрет студента создаёт только преподаватель или администратор.
    # Раньше студент мог поставить задачу на себя — закрыто осознанно.
    if body.type == DEFAULT_TASK_TYPE and user.get("role") not in (ROLE_TEACHER, ROLE_ADMIN):
        raise HTTPException(403, "Создавать профиль студента может только преподаватель или администратор.")

    username = (body.username or "").strip()
    student: Optional[dict] = None
    results: list = []
    facts: Optional[dict] = None
    errors: list = []

    if body.type == DEFAULT_TASK_TYPE:
        if not username:
            raise HTTPException(400, "Для создания профиля студента нужен username.")
        student = get_users_col().find_one(
            {"username": username},
            {"_id": 0, "password": 0, "token_version": 0},
        )
        if not student:
            raise HTTPException(404, f"Пользователь '{username}' не найден.")
        # Воркер получает всё нужное для профиля сразу — без доступа к БД.
        results = list(get_results_col().find({"username": username}, {"_id": 0}))
        # Факты и ошибки считаем здесь: воркер не должен повторять логику
        # разбора ответов, а модель получает уже готовый request.
        facts, errors = build_facts(results, LLM_MAX_ERRORS)

    col = get_tasks_col()
    if not body.force:
        existing = col.find_one(
            {
                "type": body.type,
                "username": username,
                "status": {"$in": list(ACTIVE_STATUSES)},
            }
        )
        if existing:
            return {**public_task(existing), "deduplicated": True}

    task_id = f"task_{secrets.token_urlsafe(12)}"
    payload = dict(body.payload or {})
    if username:
        payload.setdefault("username", username)
    if body.type == DEFAULT_TASK_TYPE:
        payload.setdefault("student", student)
        payload.setdefault("results", results)
        payload.setdefault("facts", facts)
        payload.setdefault("errors", errors)
        # Готовое тело /api/chat: промпт и параметры собирает сервер,
        # воркер только выбирает модель (у себя дома) и отправляет запрос.
        payload.setdefault("request", build_request(facts, errors, OLLAMA_MODEL, LLM_THINK))
    doc = {
        "_id": task_id,
        "type": body.type,
        "status": "queued",
        "username": username,
        "payload": payload,
        "created_by": user.get("sub"),
        "created_at": now_utc(),
        "attempts": 0,
    }
    col.insert_one(doc)
    logger.info(
        "Task %s (%s) queued for %s by %s (%d results, %d errors)",
        task_id,
        body.type,
        username or "-",
        user.get("sub"),
        len(results),
        len(errors),
    )
    return {**public_task(doc), "deduplicated": False}


def _save_profile(task: dict, result: Any) -> Optional[str]:
    """Сохраняет результат задачи в student_profiles и student_portraits."""
    username = (task.get("payload") or {}).get("username") or task.get("username")
    if not username or not isinstance(result, dict):
        return None

    now = now_utc()
    try:
        get_profiles_col().update_one(
            {"username": username},
            {
                "$set": {
                    "username": username,
                    "profile": result,
                    "queue_task_id": task["_id"],
                    "updated_at": now,
                }
            },
            upsert=True,
        )

        if task.get("type") == DEFAULT_TASK_TYPE:
            raw = json.dumps(result, ensure_ascii=False, sort_keys=True, default=str)
            portrait = result.get("portrait")
            if not isinstance(portrait, dict):
                # Воркер мог прислать сам портрет без обёртки.
                portrait = result
            # Тот же хеш, что считает сервер портрета: иначе кеш портрета
            # не совпадёт и LLM пересчитает то же самое.
            results = (task.get("payload") or {}).get("results") or []
            results_digest = (
                input_hash(results)
                if results
                else result.get("input_hash")
                or hashlib.sha256(raw.encode("utf-8")).hexdigest()
            )
            get_portraits_col().update_one(
                {"username": username},
                {
                    "$set": {
                        "username": username,
                        "input_hash": results_digest,
                        "generated_at": result.get("generated_at") or now.isoformat(),
                        "model": result.get("model"),
                        "source": result.get("source") or "queue",
                        "llm_error": result.get("llm_error"),
                        "facts": result.get("facts") or {},
                        "errors_count": result.get("errors_count") or 0,
                        "portrait": portrait,
                        "queue_task_id": task["_id"],
                    }
                },
                upsert=True,
            )
            student = (task.get("payload") or {}).get("student")
            group_name = student.get("group") if isinstance(student, dict) else None
            # История: одна запись на уникальный input_hash. Повторный прогон
            # тех же данных обновляет generated_at, а не плодит дубли.
            get_portrait_history_col().update_one(
                {"username": username, "input_hash": results_digest},
                {
                    "$set": {
                        "username": username,
                        "input_hash": results_digest,
                        "group": group_name,
                        "generated_at": result.get("generated_at") or now.isoformat(),
                        "model": result.get("model"),
                        "source": result.get("source"),
                        "llm_error": result.get("llm_error"),
                        "facts": result.get("facts") or {},
                        "errors_count": result.get("errors_count") or 0,
                        "portrait": portrait,
                        "queue_task_id": task["_id"],
                    }
                },
                upsert=True,
            )
    except Exception as exc:  # noqa: BLE001 — задачу всё равно помечаем done
        logger.exception("Failed to save profile for %s", username)
        return f"{type(exc).__name__}: {exc}"
    return None


def _normalize_result(task: dict, result: Any) -> Any:
    """Превращает сырой ответ Ollama в портрет; готовый портрет не трогает.

    Воркер отправляет ответ `/api/chat` как есть, поэтому разбор и
    нормализация живут на сервере — одним кодом для всех воркеров.
    """
    if not isinstance(result, dict) or "message" not in result:
        return result
    payload = task.get("payload") or {}
    facts = payload.get("facts")
    if not isinstance(facts, dict):
        return result

    errors = payload.get("errors") or []
    model = result.get("model") or (payload.get("request") or {}).get("model")
    try:
        portrait = parse_response(result, facts, errors)
    except Exception as exc:  # noqa: BLE001 — фоллбэк лучше упавшей задачи
        logger.warning("Failed to parse LLM response for %s: %s", task.get("_id"), exc)
        return {
            "portrait": fallback_portrait(facts, errors),
            "facts": facts,
            "errors_count": len(errors),
            "model": model,
            "source": "fallback",
            "llm_error": str(exc)[:500],
        }
    return {
        "portrait": portrait,
        "facts": facts,
        "errors_count": len(errors),
        "model": model,
        "source": "llm",
        "llm_error": None,
    }


def _complete_task(task_id: str, body: dict) -> dict:
    col = get_tasks_col()
    error = body.get("error")
    result = body.get("result")
    update = {"finished_at": now_utc()}
    if error:
        update.update({"status": "failed", "error": str(error)[:2000]})
    else:
        result = _normalize_result(_get_doc_or_404(task_id), result)
        # Отметка времени генерации видна и в задаче, и в истории: без неё
        # фронт не знает, когда портрет построен.
        if isinstance(result, dict) and not result.get("generated_at"):
            result["generated_at"] = now_utc().isoformat()
        update.update({"status": "done", "result": result})

    # Разрешаем завершить и только что захваченную, и ещё queued задачу
    # (одношаговый сценарий, если воркер сразу прислал результат).
    matched = col.update_one(
        {"_id": task_id, "status": {"$in": list(ACTIVE_STATUSES)}},
        {"$set": update},
    )
    if matched.matched_count == 0:
        existing = _get_doc_or_404(task_id)
        if existing.get("status") in FINISHED_STATUSES:
            raise HTTPException(409, "Задача уже завершена.")
        raise HTTPException(409, "Задача не может быть завершена.")

    doc = _get_doc_or_404(task_id)
    if not error:
        save_error = _save_profile(doc, result)
        if save_error:
            col.update_one({"_id": task_id}, {"$set": {"save_error": save_error}})
            doc = _get_doc_or_404(task_id)
    logger.info("Task %s finished with status %s", task_id, doc.get("status"))
    return public_task(doc)


def claim_or_submit(task_id: str, body: dict) -> dict:
    body = body if isinstance(body, dict) else {}
    col = get_tasks_col()

    if body.get("release"):
        doc = col.find_one_and_update(
            {"_id": task_id, "status": "in_progress"},
            {"$set": {"status": "queued"}, "$unset": {"started_at": ""}},
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            raise HTTPException(409, "Задача не в процессе выполнения.")
        return {**public_task(doc), "released": True}

    has_result = "result" in body and body.get("result") is not None
    has_error = bool(body.get("error"))
    if has_result or has_error:
        return _complete_task(task_id, body)

    # Первый POST: атомарно переводим queued -> in_progress.
    doc = col.find_one_and_update(
        {"_id": task_id, "status": "queued"},
        {
            "$set": {"status": "in_progress", "started_at": now_utc()},
            "$inc": {"attempts": 1},
        },
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        logger.info("Task %s claimed", task_id)
        return {**public_task(doc), "claimed": True}

    doc = _get_doc_or_404(task_id)
    # Повторный опрос или уже завершённая задача: отдаём актуальное состояние.
    return {**public_task(doc), "claimed": False}


def list_tasks(
    user: dict,
    status: Optional[str] = None,
    type: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = 100,
) -> list:
    is_staff = user.get("role") in (ROLE_TEACHER, ROLE_ADMIN)
    # Профили студентов — только для преподавателя/администратора. Студенту
    # запрещены и явный фильтр по типу, и выборка без типа (она включает профили).
    if not is_staff and type in (None, DEFAULT_TASK_TYPE):
        raise HTTPException(403, "Профили студентов доступны только преподавателю и администратору.")

    query: dict = {}
    if not is_staff:
        query["$or"] = [{"created_by": user.get("sub")}, {"username": user.get("sub")}]
    if status:
        query["status"] = status
    if type:
        query["type"] = type
    if username:
        query["username"] = username

    docs = get_tasks_col().find(query).sort("created_at", -1).limit(limit)
    return [public_task(doc) for doc in docs]


def get_task_for_user(task_id: str, user: dict) -> dict:
    doc = _get_doc_or_404(task_id)
    _check_read_access(doc, user)
    return public_task(doc)


def pending_tasks(limit: int) -> list:
    """Список queued-задач для воркера + возврат брошенных in_progress."""
    col = get_tasks_col()
    cutoff = now_utc() - timedelta(seconds=LEASE_SECONDS)
    stale = col.update_many(
        {"status": "in_progress", "started_at": {"$lt": cutoff}},
        {"$set": {"status": "queued"}, "$unset": {"started_at": ""}},
    )
    if stale.modified_count:
        logger.warning("Requeued %d stale tasks", stale.modified_count)

    docs = col.find({"status": "queued"}).sort("created_at", 1).limit(limit)
    return [public_task(doc) for doc in docs]


def _group_snapshot(group_name: str, usernames: list) -> dict:
    """Средние по группе: балл, зачёты и проценты по темам.

    Среднее считаем по студентам, а не по всем попыткам: иначе студент с
    десятком пересдач перевесил бы всю группу. По темам усредняем только
    среди тех, у кого тема вообще встречалась.
    """
    results_col = get_results_col()
    averages = []
    pass_rates = []
    topic_acc: dict = {}
    for name in usernames:
        stats = quick_stats(list(results_col.find({"username": name}, {"_id": 0})))
        if stats["average_score"] is not None:
            averages.append(stats["average_score"])
        if stats["pass_rate"] is not None:
            pass_rates.append(stats["pass_rate"])
        for topic in stats["topics"]:
            topic_acc.setdefault(topic["topic"], []).append(topic["percentage"])

    topics = [
        {"topic": topic, "percentage": round(sum(values) / len(values), 1)}
        for topic, values in topic_acc.items()
        if values
    ]
    topics.sort(key=lambda t: t["percentage"])
    average = round(sum(averages) / len(averages), 1) if averages else None
    return {
        "name": group_name,
        "size": len(usernames),
        "average_score": average,
        "pass_rate": round(sum(pass_rates) / len(pass_rates), 1) if pass_rates else None,
        "level": level_from_score(average) if average is not None else None,
        "topics": topics,
    }


def student_insights(username: str, user: dict) -> dict:
    """История портретов студента и сравнение с его группой."""
    if user.get("role") not in (ROLE_TEACHER, ROLE_ADMIN):
        raise HTTPException(403, "История портретов доступна только преподавателю и администратору.")
    username = (username or "").strip()
    if not username:
        raise HTTPException(400, "Укажите username.")

    history = []
    for doc in get_portrait_history_col().find({"username": username}).sort("generated_at", 1):
        facts = doc.get("facts") or {}
        portrait = doc.get("portrait") or {}
        history.append(
            {
                "generated_at": _iso(doc.get("generated_at")),
                "input_hash": doc.get("input_hash"),
                "model": doc.get("model"),
                "source": doc.get("source"),
                "level": portrait.get("level"),
                "risk_of_failing": portrait.get("risk_of_failing"),
                "average_score": facts.get("average_score"),
                "pass_rate": facts.get("pass_rate"),
                "open_gaps": facts.get("open_gaps"),
                "attempts": facts.get("attempts"),
                "errors_count": doc.get("errors_count"),
            }
        )

    student = get_users_col().find_one(
        {"username": username}, {"_id": 0, "group": 1, "full_name": 1}
    ) or {}
    group_name = (student.get("group") or "").strip()
    group = None
    if group_name:
        members = [
            u["username"]
            for u in get_users_col().find(
                {"group": group_name, "role": ROLE_STUDENT}, {"_id": 0, "username": 1}
            )
        ]
        if username not in members:
            members.append(username)
        group = _group_snapshot(group_name, members)

    return {
        "username": username,
        "full_name": student.get("full_name", ""),
        "group": group,
        "history": history,
    }