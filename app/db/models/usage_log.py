import uuid
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id = Column(Integer, nullable=False, index=True)
    tenant_name = Column(String(255), nullable=False, index=True)

    user_id = Column(String(255), nullable=False, index=True)
    user_name = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)

    agent_id = Column(Integer, nullable=False, index=True)
    agent_name = Column(String(255), nullable=False, index=True)
    agent_category = Column(String(255), nullable=False, index=True)

    conversation_id = Column(UUID(as_uuid=True))

    model = Column(String(100), nullable=False)

    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    is_chat_agent = Column(Boolean, nullable=False, default=True)

    estimated_cost = Column(Numeric(12, 6), nullable=False, default=0)

    response_time_ms = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
