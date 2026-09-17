from pydantic import BaseModel, ConfigDict
from typing import List, Optional

from app.schemas.common import Pageination


class TenantCreate(BaseModel):
    name: str


class TenantResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class TenantResponseList(BaseModel):
    data: List[TenantResponse]
    pagination: Pageination


class TenantUpdate(BaseModel):
    name: Optional[str] = None
