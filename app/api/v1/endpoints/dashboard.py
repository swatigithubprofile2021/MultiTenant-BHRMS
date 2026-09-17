from fastapi import Depends
from redis import Redis
from app.utils.dashboard import get_dashboard
from app.api.deps.auth_dep import get_db, get_redis
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from sqlalchemy import or_
from app.db.models.agent import Agent
from app.db.models.user import User


from app.api.deps.auth_dep import get_db, require_role, get_current_user
from sqlalchemy.orm import selectinload

router = APIRouter()


@router.get("/super-admin")
async def dashboard_super(
    time_filter: str = Query("max", enum=["day", "week", "month", "year", "max"]),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await get_dashboard(
        redis=redis, db=db, role="super_admin", time_filter=time_filter
    )


@router.get("/platform-admin")
async def dashboard_platform(
    time_filter: str = Query("max", enum=["day", "week", "month", "year", "max"]),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await get_dashboard(
        redis=redis, db=db, role="platform_admin", time_filter=time_filter
    )


@router.get("/tenant-admin")
async def dashboard_tenant(
    time_filter: str = Query("max", enum=["day", "week", "month", "year", "max"]),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    return await get_dashboard(
        redis=redis,
        db=db,
        role="tenant_admin",
        tenant_id=current_user.tenant_id,
        time_filter=time_filter,
    )
