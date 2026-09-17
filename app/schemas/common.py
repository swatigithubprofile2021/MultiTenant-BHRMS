from pydantic import BaseModel
from enum import Enum


class Pageination(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class MessageRoleEnum(Enum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"
    AI = "ai"
    HUMAN = "human"
    TOOL = "tool"
