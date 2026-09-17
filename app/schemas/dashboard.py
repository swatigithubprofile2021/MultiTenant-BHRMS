from pydantic import BaseModel
from typing import List, Any


class TopBot(BaseModel):
    id: str
    name: str
    total_tokens: int


class TopOrganization(BaseModel):
    id: str
    name: str
    total_tokens: int
    total_requests: int


class TopUser(BaseModel):
    user_id: str
    name: str
    total_requests: int


class DashboardResponse(BaseModel):
    total_bots: int
    top_bots: List[TopBot]
    total_conversations: int
    avg_conversation: float
    total_messages: int
    avg_message_per_conversation: float
    top_organizations: List[TopOrganization]


class TenantDashboardResponse(BaseModel):
    total_bots: int
    top_bots: List[TopBot]
    total_conversations: int
    avg_conversation: float
    total_messages: int
    avg_message_per_conversation: float
    top_users: List[TopUser]
