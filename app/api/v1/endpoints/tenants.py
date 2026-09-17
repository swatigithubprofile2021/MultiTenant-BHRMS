from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.schemas.common import Pageination
from app.schemas.tenant import (
    TenantCreate,
    TenantResponse,
    TenantResponseList,
    TenantUpdate,
)
from app.api.deps.auth_dep import require_role, get_db

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TenantResponse)
async def create_tenant(
    tenant_info: TenantCreate,
    current_user: User = Depends(require_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    create tenant under which documets, tenant admin and agents etc exists.
    """
    smt = select(Tenant).where(Tenant.name == tenant_info.name)
    # Check if tenant with same name exists
    result = await db.execute(smt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant name already exists"
        )

    # Create new tenant
    tenant = Tenant(name=tenant_info.name, created_by=current_user.id)

    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    return TenantResponse(id=tenant.id, name=tenant_info.name)


@router.get("", response_model=TenantResponseList)
async def list_tenants(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    name: str | None = Query(None),
    current_user: User = Depends(require_role("super_admin", "admin", "tenant_admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    List tenants with pagination
    """

    # Base query
    base_query = select(Tenant)

    count_query = select(func.count(Tenant.id))

    if name:
        base_query = base_query.where(Tenant.name.ilike(f"%{name}%"))

        count_query = count_query.where(Tenant.name.ilike(f"%{name}%"))

    if current_user.tenant_id is not None:
        base_query = base_query.where(Tenant.id == current_user.tenant_id)
        count_query = count_query.where(Tenant.id == current_user.tenant_id)

    # Get total count
    total = (await db.execute(count_query)).scalar_one()

    # Apply ordering + pagination
    stmt = base_query.order_by(Tenant.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    tenants = result.scalars().all()

    tenant_responses = [TenantResponse.model_validate(tenant) for tenant in tenants]

    return TenantResponseList(
        data=tenant_responses,
        pagination=Pageination(
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + limit < total,
        ),
    )


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    payload: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "admin")),
    
):
  
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if payload.name and payload.name != tenant.name:
        # Duplicate name check
        duplicate_stmt = select(Tenant).where(Tenant.name == payload.name)
        duplicate_result = await db.execute(duplicate_stmt)
        duplicate = duplicate_result.scalar_one_or_none()

        if duplicate:
            raise HTTPException(status_code=400, detail="Tenant name already exists")

        tenant.name = payload.name

    await db.commit()
    await db.refresh(tenant)

    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: int,
    current_user: User = Depends(require_role("super_admin", "admin", "tenant_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a Tenant"""
    tenant_id = current_user.tenant_id

    stmt = select(Tenant)

    if current_user.tenant_id is not None:
        stmt = stmt.where(Tenant.id == tenant_id).where(
            Tenant.created_by == current_user.id
        )

    result = await db.execute(stmt)

    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not exists"
        )

    await db.delete(tenant)
    await db.commit()

    return {"message": f"Tenant {tenant.name} deleted"}
