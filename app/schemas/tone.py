from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from enum import Enum
from app.schemas.document import Pageination



class ToneCreate(BaseModel):
    # tenant_id: int
    name: str
    description: Optional[str] = None


class ToneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ToneResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_default: bool

    class Config:
        from_attributes = True


class ToneResponseList(BaseModel):
    tones: list[ToneResponse]
    pagination: Pageination

    class Config:
        from_attributes = True

