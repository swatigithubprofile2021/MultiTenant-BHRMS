from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.tone import Tone
from app.schemas.tone import ToneCreate, ToneUpdate, ToneResponse
from app.api.deps.auth_dep import get_db, require_role

router = APIRouter()

@router.post("/", response_model=ToneResponse)
async def create_tone(
    payload: ToneCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "super_admin")),
):
    tone = Tone(**payload.model_dump())
    db.add(tone)
    await db.commit()
    await db.refresh(tone)
    return tone


@router.get("/", response_model=list[ToneResponse])
async def list_tones(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tone))
    return result.scalars().all()


@router.patch("/{tone_id}", response_model=ToneResponse)
async def update_tone(
    tone_id: int,
    payload: ToneUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "super_admin")),
):
    result = await db.execute(select(Tone).where(Tone.id == tone_id))
    tone = result.scalar_one_or_none()

    if not tone:
        raise HTTPException(404, "Tone not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(tone, key, value)

    await db.commit()
    return tone


@router.delete("/{tone_id}")
async def delete_tone(
    tone_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "super_admin")),
):
    result = await db.execute(select(Tone).where(Tone.id == tone_id))
    tone = result.scalar_one_or_none()

    if not tone:
        raise HTTPException(404, "Tone not found")

    await db.delete(tone)
    await db.commit()
    return {"message": "Deleted successfully"}