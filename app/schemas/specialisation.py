from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from typing import List
from enum import Enum
from app.schemas.document import Pageination


class SpecialisationCreate(BaseModel):
    name: str


class SpecialisationUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class SpecialisationResponse(BaseModel):
    id: int
    name: str
    specialisation: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
