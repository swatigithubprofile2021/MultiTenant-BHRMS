from fastapi import APIRouter, Request
from app.db.session import async_engine

router = APIRouter()


@router.get("/health/live", tags=["Health"])
async def liveness():
    return {"status": "alive"}


@router.get("/health/ready", tags=["Health"])
async def readiness(request: Request):
    try:
        async with async_engine.begin() as conn:
            await conn.execute("SELECT 1")

        # check redis
        await request.app.state.redis_client.ping()

        return {"status": "ready"}
    except Exception:
        return {"status": "not_ready"}
