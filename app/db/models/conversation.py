import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id = Column(String(255), nullable=False, index=True)

    session_id = Column(String(255), nullable=False, index=True)

    agent_id = Column(
        Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title = Column(String(255), nullable=True)  # optional auto-generated title

    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_conv_org_date", "tenant_id", "started_at"),)
