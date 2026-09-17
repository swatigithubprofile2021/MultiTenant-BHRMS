from fastapi import APIRouter
from app.api.v1.endpoints import (
    documents,
    auth,
    admins,
    tenants,
    agents,
    permission,
    dashboard,
    sessions,
    specialisation,
    theme, tone
    
)
from app.api.v1.websockets import chat

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(admins.router, prefix="/admins", tags=["Admins"])
router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
router.include_router(documents.router, prefix="/documents", tags=["Documents"])
router.include_router(chat.router, prefix="/ws/chat", tags=["Chat"])
router.include_router(permission.router, prefix="/permissions", tags=["Permissions"])
router.include_router(agents.router, prefix="/agents", tags=["Agents"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
router.include_router(
    specialisation.router, prefix="/specialisations", tags=["Specialisations"]
)
router.include_router(theme.router, prefix="/theme", tags=["Theme"])
router.include_router(tone.router, prefix="/tones", tags=["Tones"])


