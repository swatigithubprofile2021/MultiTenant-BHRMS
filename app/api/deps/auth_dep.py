from fastapi import Depends, HTTPException, Request, status
from redis import Redis
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.jwt import decode_access_token
from app.db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.session import AsyncSessionLocal

security = HTTPBearer()


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


async def get_redis(request: Request) -> Redis:
    return request.app.state.redis_client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials

    # Decode token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    # Check blacklist
    if await redis.get(f"blacklist:{token}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
        )

    user_id = payload.get("user_id")
    smt = select(User).options(selectinload(User.role)).where(User.id == int(user_id))
    result = await db.execute(smt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user


async def get_current_user_on_logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis: Redis = Depends(get_redis),
):
    token = credentials.credentials

    # Decode token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    # Check blacklist
    if await redis.get(f"blacklist:{token}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
        )

    return payload


def require_role(*allowed_roles):
    async def role_dependency(current_user: User = Depends(get_current_user)):
        if current_user.role.name not in allowed_roles:
            raise HTTPException(status_code=403, detail="Permission denied")
        return current_user

    return role_dependency
