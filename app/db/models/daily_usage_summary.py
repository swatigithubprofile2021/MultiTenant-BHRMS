import uuid
from sqlalchemy import Column, Integer, Numeric, Date, Float, String
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class DailyUsageSummary(Base):
    __tablename__ = "daily_usage_summary"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id = Column(Integer, nullable=False, index=True)
    tenant_name = Column(String(255), nullable=False, index=True)

    agent_id = Column(Integer, nullable=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)

    user_name = Column(String(255), nullable=False, index=True)
    agent_name = Column(String(255), nullable=False, index=True)
    agent_category = Column(String(255), nullable=False, index=True)

    date = Column(Date, nullable=False, index=True)
    total_requests = Column(Integer, default=0)
    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    avg_conversation_length = Column(Float, default=0.0)
    avg_response_time_ms = Column(Float, default=0.0)
