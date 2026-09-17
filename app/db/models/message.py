import uuid
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    Integer,
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.schemas.common import MessageRoleEnum
from app.db.base import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = Column(
        SqlEnum(MessageRoleEnum, name="message_role"),
        nullable=False,
        index=True,
    )

    content = Column(Text, nullable=False)

    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationship
    conversation = relationship("Conversation", back_populates="messages")
