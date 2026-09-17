from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from typing import List

# from enum import Enum
from app.schemas.document import Pageination
from scripts.seed_tone import DEFAULT_TONES

# class SpecializationEnum(Enum):
#     GENERAL = "GENERAL"
#     HR = "HR"
#     TECHNICAL_SUPPORT = "TECHNICAL_SUPPORT"
#     CUSTOMER_SUPPORT = "CUSTOMER_SUPPORT"
#     FINANCE = "FINANCE"
#     HEALTHCARE = "HEALTHCARE"
#     EDUCATION = "EDUCATION"


# =========================
# CREATE AGENT
# =========================


class AgentCreate(BaseModel):
    # Agent basic info
    name: str
    alias_name: Optional[str] = None
    description: Optional[str] = None
    # specialisation: Optional[SpecializationEnum] = SpecializationEnum.GENERAL
    specialisation_id: int
    is_public: Optional[bool] = False
    is_chat_agent: Optional[bool] = True
    
    # Agent Config
    model_name: str
    temperature: Optional[float] = Field(default=0.7, ge=0, le=1)
    system_prompt: Optional[str] = None
    allowed_sources: List[str]
    tone_id: Optional[int] = None
    welcome_message: Optional[str] = None
    theme_id: Optional[int] = None

# =========================
# CONFIG RESPONSE
# =========================

class AgentConfigResponse(BaseModel):
    model_name: str
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None
    allowed_sources: Optional[List[str]] = None
    tone_id: Optional[int] = None
    welcome_message: Optional[str] = None
    theme_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

# =========================
# AGENT RESPONSE
# =========================

class AgentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_public: Optional[bool] = None
    is_chat_agent: Optional[bool] = None
    alias_name: Optional[str] = None
    # specialisation: Optional[str] = None
    specialisation_id: int
    # specialisation: Optional[str]
    specialisation: Optional[str] = Field(default=None, alias="specialisation_name")
    
    created_at: datetime
    config: Optional[AgentConfigResponse]

    model_config = ConfigDict(from_attributes=True)


class AgentResponseList(BaseModel):
    data: List[AgentResponse]
    pagination: Pageination


class AgentUpdate(BaseModel):
    # Agent fields
    name: Optional[str] = None
    alias_name: Optional[str] = None
    description: Optional[str] = None
    # specialisation: Optional[str] = None
    specialisation_id: Optional[int] = None
    is_public: Optional[bool] = None
    is_chat_agent: Optional[bool] = None

    # Config fields
    model_name: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=1)
    system_prompt: Optional[str] = None
    allowed_sources: Optional[str] = None
    tone_id: Optional[int] = None
    welcome_message: Optional[str] = None
    theme_id: Optional[int] = None
