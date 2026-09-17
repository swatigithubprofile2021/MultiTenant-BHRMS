from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps.auth_dep import get_db, require_role
from app.db.models.permissions import Permission
from app.db.models.user import User
from app.schemas.permission import PermissionResponse

router = APIRouter()


@router.get("", response_model=list[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    stmt = select(Permission).order_by(Permission.id)
    result = await db.execute(stmt)
    permissions = result.scalars().all()

    return permissions
