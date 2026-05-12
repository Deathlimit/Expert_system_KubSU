import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import get_col
from router import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# TEMPORARY: Self-ping to prevent Render free tier from sleeping
# TODO: Remove this when proper solution is implemented (e.g., Render Pro, cron job, etc.)
PING_INTERVAL_SECONDS = 180  # 3 minutes


async def _self_ping_loop(base_url: str):
    """Ping own health endpoint every 3 minutes to keep service awake."""
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
    logger.info("Session Service starting up...")
    get_col()

    # TEMPORARY: Start self-ping loop to prevent Render from sleeping
    # TODO: Remove this temporary solution
    base_url = "https://expert-system-431h.onrender.com"
    asyncio.create_task(_self_ping_loop(base_url))
    logger.info("Self-ping loop started (temporary solution)")

    logger.info("Session Service ready.")
    yield
    logger.info("Session Service shutting down.")


app = FastAPI(title="Session Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
