from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User
from app.db.models.tenant import Tenant
from app.db.models.roles import Role
from app.schemas.common import Pageination
from app.schemas.user import AdminType, UserResponse, UserResponseList
from app.core.security import hash_password
from app.api.deps.auth_dep import require_role, get_db
from app.schemas.user import AdminUserRegister, AdminUserUpdate

router = APIRouter()


# Create Platform Admin
@router.post(
    "/platform", status_code=status.HTTP_201_CREATED, response_model=UserResponse
)
async def create_platform_admin(
    adminUserRegister: AdminUserRegister,
    current_user: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    smt = select(User).where(User.email == adminUserRegister.email)
    # Check if email already exists
    result = await db.execute(smt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    # Get platform admin role
    smt = select(Role).where(Role.name == "admin")
    result = await db.execute(smt)
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role 'admin' not found",
        )

    new_admin = User(
        name=adminUserRegister.name,
        email=adminUserRegister.email,
        hashed_password=hash_password(adminUserRegister.password),
        role_id=role.id,
        tenant_id=None,  # Platform-level, no tenant
    )

    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)

    return UserResponse(
        id=new_admin.id,
        name=new_admin.name,
        email=new_admin.email,
        tenant="N/A",
        role="Admin",
    )


# Create Tenant Admin
@router.post(
    "/tenant", status_code=status.HTTP_201_CREATED, response_model=UserResponse
)
async def create_tenant_admin(
    adminUserRegister: AdminUserRegister,
    current_user: User = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    if adminUserRegister.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id required"
        )

    smt = select(Tenant).where(Tenant.id == adminUserRegister.tenant_id)
    # Check if tenant exists
    result = await db.execute(smt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == adminUserRegister.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    # Get tenant_admin role
    result = await db.execute(select(Role).where(Role.name == "tenant_admin"))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role 'tenant_admin' not found",
        )

    tenant_admin = User(
        name=adminUserRegister.name,
        email=adminUserRegister.email,
        hashed_password=hash_password(adminUserRegister.password),
        role_id=role.id,
        tenant_id=adminUserRegister.tenant_id,
    )

    db.add(tenant_admin)
    await db.commit()
    await db.refresh(tenant_admin)

    return UserResponse(
        id=tenant_admin.id,
        name=tenant_admin.name,
        email=tenant_admin.email,
        tenant=tenant_admin.tenant.name,
        role="Tenant admin",
    )


# get list of Admins
@router.get("", response_model=UserResponseList)
async def list_admin(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_type: AdminType = AdminType.ALL,
    name: str | None = Query(None),
    email: str | None = Query(None),
    current_user: User = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    base_query = (
        select(User)
        .join(User.role)
        .options(
            joinedload(User.tenant),
            joinedload(User.role),
        )
        .where(User.role.has(Role.name != "super_admin"))
    )

    if current_user.role.name == "admin":
        base_query = base_query.where(User.role.has(Role.name == "tenant_admin"))
    else:
        if admin_type == AdminType.ALL:
            base_query = base_query.where(
                or_(
                    User.role.has(Role.name == "admin"),
                    User.role.has(Role.name == "tenant_admin"),
                )
            )
        else:
            base_query = base_query.where(User.role.has(Role.name == admin_type.value))

    if name:
        base_query = base_query.where(User.name.ilike(f"%{name}%"))

    if email:
        base_query = base_query.where(User.email.ilike(f"%{email}%"))

    # Efficient count
    count_stmt = select(func.count()).select_from(base_query.order_by(None).subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Pagination + ordering
    stmt = base_query.order_by(User.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    users = result.scalars().unique().all()

    user_responses = [
        UserResponse(
            id=usr.id,
            name=usr.name,
            email=usr.email,
            tenant=usr.tenant.name if usr.tenant else "N/A",
            role=usr.role.name.replace("_", " ").capitalize(),
        )
        for usr in users
    ]

    return UserResponseList(
        data=user_responses,
        pagination=Pageination(
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + limit < total,
        ),
    )


@router.patch("/platform/{user_id}", response_model=UserResponse)
async def update_platform_admin(
    user_id: int,
    payload: AdminUserUpdate,
    current_user: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).options(joinedload(User.role)).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or user.role.name != "admin":
        raise HTTPException(status_code=404, detail="Platform admin not found")

    # Email uniqueness check
    if payload.email and payload.email != user.email:
        email_stmt = select(User).where(User.email == payload.email)
        email_result = await db.execute(email_stmt)
        existing = email_result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = payload.email

    if payload.name:
        user.name = payload.name

    if payload.password:
        user.hashed_password = hash_password(payload.password)

    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        tenant="N/A",
        role="Admin",
    )


@router.patch("/tenant/{user_id}", response_model=UserResponse)
async def update_tenant_admin(
    user_id: int,
    payload: AdminUserUpdate,
    current_user: User = Depends(require_role("admin")),  # ONLY platform admin
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(User)
        .options(joinedload(User.role), joinedload(User.tenant))
        .where(User.id == user_id)
    )

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role.name != "tenant_admin":
        raise HTTPException(status_code=400, detail="Not a tenant admin")

    # Email uniqueness check
    if payload.email and payload.email != user.email:
        email_stmt = select(User).where(User.email == payload.email, User.id != user.id)
        existing = (await db.execute(email_stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

        user.email = payload.email

    if payload.name:
        user.name = payload.name

    if payload.password:
        user.hashed_password = hash_password(payload.password)

    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        tenant=user.tenant.name if user.tenant else "N/A",
        role="Tenant admin",
    )


# Delete Admin
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin(
    user_id: int,
    current_user: User = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    #stmt = select(User).where(User.id == user_id)

    stmt = (
        select(User)
        .options(joinedload(User.role))   #  preload role
        .where(User.id == user_id)
    )
    

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not exists"
        )

    if current_user.role.name == "super_admin":
        if user.role.name not in ("admin", "tenant_admin"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Not allowed."
            )

    if current_user.role.name == "admin":
        if user.role.name != "tenant_admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Not allowed."
            )

    await db.delete(user)
    await db.commit()

    return {"message": f"User {user.name} deleted"}
