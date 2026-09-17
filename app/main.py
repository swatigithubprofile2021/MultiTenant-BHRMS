import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.lifespan import lifespan
from app.core.logger import logger
from app.monitoring.health import router as health_router
from app.monitoring.middleware import MetricsMiddleware
from app.monitoring.metrics_endpoint import router as metrics_router
from app.api.router import api_router
from fastapi.staticfiles import StaticFiles
from app.core.config import settings

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

description = "AI assistant platform with multi-tenant RAG and analytics.\n\n" """
    ### Agent Chat WebSocket Endpoint\n

    `ws://localhost:8000/api/v1/ws/chat?agent_id=<agent_id>`\n

    Used for chat with a agent.
    """

app = FastAPI(
    title="Multi-Tenant AI Assistant with RAG",
    description=description,
    version="2.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Authorization", "X-Role"],
)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Static files for uploaded assets
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.exception(
            f"Unhandled error on {request.method} {request.url.path}: {e}",
            stack_info=True,
            exc_info=True,
        )
        raise
    finally:
        process_time = round((time.time() - start_time) * 1000, 2)
        logger.info(f"{request.method} {request.url.path} | " f"{process_time}ms")


# routes
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(metrics_router)

app.include_router(api_router, prefix="/api")
