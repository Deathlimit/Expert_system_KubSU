"""Единая точка входа бэкенда для Render — без нейросети.

На Render нет GPU и Ollama, поэтому сервис портретов (portrait_service)
сюда не входит. Портреты считает домашний воркер: он забирает задания из
`/queue` и отправляет готовое тело `/api/chat` в Ollama локально.

Все остальные микросервисы подключены к одному FastAPI-приложению. Пути
размечены префиксами (/auth, /content, /tests, /sessions, /queue),
поэтому nginx/маршрутизация не нужны.

Локально:
    cd backend_render
    uvicorn main:app --reload --port 8000

Render:
    build: pip install -r requirements.txt
    start: uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth_service import database as auth_db
from auth_service.router import router as auth_router
from content_service import database as content_db
from content_service.router import router as content_router
from queue_service import database as queue_db
from queue_service.router import router as queue_router
from session_service import database as session_db
from session_service.router import router as session_router
from test_service import database as test_db
from test_service.router import router as test_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Без этого периодический self-ping писал бы в лог строку httpx на каждый запрос.
logging.getLogger("httpx").setLevel(logging.WARNING)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else ["*"]

# Neural-сервис (/portraits, Ollama) осознанно отсутствует: его роль
# выполняет домашний воркер очереди.
SERVICES = ("auth", "content", "tests", "sessions", "queue")

# Пинг собственного /health: бесплатный Render засыпает после 15 минут без
# трафика, а свой запрос — это трафик. Адрес Render подставляет сам
# (RENDER_EXTERNAL_URL); локально переменной нет — keep-alive выключается.
KEEPALIVE_ENABLED = os.environ.get("KEEPALIVE_ENABLED", "true").strip().casefold() not in (
    "false", "0", "no", "off",
)
KEEPALIVE_INTERVAL = float(os.environ.get("KEEPALIVE_INTERVAL_SECONDS", "60"))
KEEPALIVE_URL = (
    os.environ.get("KEEPALIVE_URL")
    or os.environ.get("RENDER_EXTERNAL_URL")
    or os.environ.get("INTERNAL_BASE_URL")
    or ""
).rstrip("/")


async def _keepalive_loop() -> None:
    """Раз в интервал дёргаем свой /health, пока сервис живёт."""
    url = f"{KEEPALIVE_URL}/health"
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            # Сначала ждём интервал: на старте lifespan сервер ещё не принимает
            # соединения, и запрос к себе же сразу упал бы.
            await asyncio.sleep(KEEPALIVE_INTERVAL)
            try:
                response = await client.get(url)
                logger.info("Keep-alive: GET %s -> %s", url, response.status_code)
            except Exception as exc:  # noqa: BLE001 — пинг не должен ронять сервис
                logger.warning("Keep-alive: не удалось дёрнуть %s: %s", url, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Expert System API starting up (no LLM)...")
    # Auth
    auth_db.get_db()
    auth_db.ensure_demo_test()
    auth_db.get_groups_col()
    auth_db.get_tests_col()
    # Content
    content_db.get_db()
    # Tests
    test_db.get_col()
    # Sessions
    session_db.get_col()
    session_db.get_active_sessions_col()
    # Queue
    queue_db.get_tasks_col()
    queue_db.get_profiles_col()
    keepalive_task = None
    if KEEPALIVE_ENABLED and KEEPALIVE_URL:
        keepalive_task = asyncio.create_task(_keepalive_loop())
        logger.info("Keep-alive включён: %s каждые %.0f с", KEEPALIVE_URL, KEEPALIVE_INTERVAL)
    else:
        logger.info("Keep-alive выключен (нет адреса для self-call или KEEPALIVE_ENABLED=false).")
    logger.info("Expert System API ready.")
    yield
    if keepalive_task:
        keepalive_task.cancel()
        with suppress(asyncio.CancelledError):
            await keepalive_task
    logger.info("Expert System API shutting down.")


app = FastAPI(title="Expert System API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=bool(CORS_ORIGINS != ["*"]),
    allow_methods=["*"], allow_headers=["*"],
)

for router in (
    auth_router,
    content_router,
    test_router,
    session_router,
    queue_router,
):
    app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "services": list(SERVICES), "llm": "external"}
