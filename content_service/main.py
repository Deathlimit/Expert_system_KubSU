import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import get_db
from router import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else ["*"]

# Интервал самопинга (3 минуты)
PING_INTERVAL_SECONDS = 180


async def _self_ping_loop(base_url: str):
    # Самопинг для поддержания активности сервиса
    await asyncio.sleep(PING_INTERVAL_SECONDS)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.get(f"{base_url}/health")
            logger.info("Self-ping completed to prevent sleep")
    except Exception as e:
        logger.warning(f"Self-ping failed: {e}")
    finally:
        asyncio.create_task(_self_ping_loop(base_url))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Content Service starting up...")
    get_db()

    base_url = "https://expert-system-431h.onrender.com"
    asyncio.create_task(_self_ping_loop(base_url))
    logger.info("Self-ping loop started")

    logger.info("Content Service ready.")
    yield
    logger.info("Content Service shutting down.")


app = FastAPI(title="Content Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=bool(CORS_ORIGINS != ["*"]),
    allow_methods=["*"], allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
