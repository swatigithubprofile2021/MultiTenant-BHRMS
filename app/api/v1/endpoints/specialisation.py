from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from sqlalchemy import or_
from app.api.deps.auth_dep import get_db, require_role
from app.db.models.agent import Agent
from app.db.models.user import User
from app.db.models.specialisations import Specialisation
from app.db.models.agent_config import AgentConfig
from app.schemas.specialisation import (
    SpecialisationResponse,
    SpecialisationCreate,
    SpecialisationUpdate,
)
from sqlalchemy.orm import selectinload

router = APIRouter()


@router.get("/")
async def get_specialisations(db: AsyncSession = Depends(get_db)):

    stmt = select(Specialisation).order_by(Specialisation.name)

    result = await db.execute(stmt)

    specialisations = result.scalars().all()

    return [{"id": s.id, "name": s.name} for s in specialisations]


@router.post("/")
async def create_specialisation(
    payload: SpecialisationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "admin")),
):

    specialisation = Specialisation(name=payload.name)

    stmt = select(Specialisation).order_by(Specialisation.name)

    result = await db.execute(stmt)

    specialisations = result.scalars().all()

    for s in specialisations:
        if s.name.lower() == payload.name.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Specialisation with name '{payload.name}' already exists.",
            )

        if "_" in payload.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Specialisation name cannot contain underscores.",
            )

    db.add(specialisation)
    await db.commit()
    await db.refresh(specialisation)

    return specialisation


@router.put("/{specialisation_id}")
async def update_specialisation(
    specialisation_id: int,
    payload: SpecialisationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "platform_admin")),
):
    stmt = select(Specialisation).where(Specialisation.id == specialisation_id)
    result = await db.execute(stmt)

    specialisation = result.scalar_one_or_none()

    if not specialisation:
        raise HTTPException(status_code=404, detail="Specialisation not found")

    specialisation.name = payload.name

    if payload.is_active is not None:
        specialisation.is_active = payload.is_active

    await db.commit()
    await db.refresh(specialisation)

    return specialisation
