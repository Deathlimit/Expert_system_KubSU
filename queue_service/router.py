"""HTTP API сервиса очереди: /queue/..."""

from typing import Optional

from fastapi import APIRouter, Body, Depends, Query

from .models import CreateTaskBody
from .security import get_current_user, verify_worker
from .service import (
    claim_or_submit,
    create_task,
    get_task_for_user,
    list_tasks,
    pending_tasks,
    student_insights,
)

router = APIRouter(prefix="/queue", tags=["queue"])


@router.post("/tasks", status_code=201)
async def enqueue_task(body: CreateTaskBody, user=Depends(get_current_user)):
    """Кнопка на фронте: поставить задачу «создать профиль студента»."""
    return create_task(body, user)


@router.get("/tasks")
async def get_tasks(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    user=Depends(get_current_user),
):
    return list_tasks(user, status=status, type=type, username=username, limit=limit)


@router.get("/tasks/pending")
async def get_pending_tasks(
    limit: int = Query(10, ge=1, le=100),
    _=Depends(verify_worker),
):
    """Воркер узнаёт, какие задачи сейчас в очереди (без захвата)."""
    return pending_tasks(limit)


@router.get("/insights")
async def get_insights(
    username: str = Query(..., min_length=1),
    user=Depends(get_current_user),
):
    """История портретов студента и сравнение с его группой."""
    return student_insights(username, user)


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, user=Depends(get_current_user)):
    """Фронт опрашивает статус задачи."""
    return get_task_for_user(task_id, user)


@router.post("/tasks/{task_id}")
async def claim_or_submit_task(
    task_id: str,
    body: Optional[dict] = Body(default=None),
    _=Depends(verify_worker),
):
    """Первый POST — захват (queued -> in_progress), второй — результат (-> done)."""
    return claim_or_submit(task_id, body or {})