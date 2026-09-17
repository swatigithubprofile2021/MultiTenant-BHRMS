from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from uuid import UUID
from enum import Enum

from app.schemas.common import Pageination


class AdminType(Enum):
    Admin = "admin"
    TENANT_ADMIN = "tenant_admin"
    ALL = "all"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminUserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    tenant_id: Optional[int] = None


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    tenant_id: UUID
    role_id: UUID


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    tenant: str
    role: str


class UserResponseList(BaseModel):
    data: List[UserResponse]
    pagination: Pageination


class AdminUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
