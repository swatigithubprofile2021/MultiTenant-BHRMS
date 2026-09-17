import json
import time
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.roles import Role
from app.db.models.user import User
from app.core.security import verify_password
from app.core.jwt import create_access_token
from app.schemas.user import LoginRequest
from app.api.deps.auth_dep import get_db, get_current_user_on_logout, get_redis

router = APIRouter()


@router.post("/login")
async def login(
    login_request: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    smt = (
        select(User)
        .options(selectinload(User.role).selectinload(Role.permissions))
        .where(User.email == login_request.email)
    )
    result = await db.execute(smt)
    user = result.scalar_one_or_none()
    if not user or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token_data = {
        "user_id": str(user.id),
        "role": user.role.name,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
    }
    access_token = create_access_token(token_data)
    permissions = [p.code for p in user.role.permissions]

    response.headers["Authorization"] = f"Bearer {access_token}"
    #response.headers["X-Role"] = f"Role_{user.id}"
    # response.headers["Access-Control-Expose-Headers"] = (
    #     "Authorization"  # For frontend CORS
    #     "X-Role"
    # )
    response.headers["X-Role"] = user.role.name
    response.headers["Access-Control-Expose-Headers"] = "Authorization, X-Role"

    return {"msg": "Login successful", "access_ids": permissions }


@router.post("/logout")
async def logout(
    token: str = Depends(get_current_user_on_logout), redis: Redis = Depends(get_redis)
):
    """
    Invalidate JWT by storing it in Redis blacklist until it expires
    """
    payload = token  # token dependency returns decoded payload
    exp = payload.get("exp")
    if exp:
        ttl = int(exp - time.time())  # time to live until token naturally expires
        await redis.setex(f"blacklist:{token}", ttl, "revoked")
    return JSONResponse({"message": "Logout successful."})
