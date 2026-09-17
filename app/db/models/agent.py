from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    ForeignKey,
    Text,
    func,
    Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SqlEnum

# from app.schemas.agent import SpecializationEnum
from app.db.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(255), nullable=False)
    alias_name = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    specialisation_id = Column(
        Integer, ForeignKey("specialisations.id"), nullable=False, index=True
    )

    specialisation = relationship("Specialisation")

    is_template = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    is_chat_agent = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant = relationship("Tenant", back_populates="agents")
    creator = relationship("User")

    config = relationship(
        "AgentConfig",
        back_populates="agent",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def specialisation_name(self):
        return self.specialisation.name if self.specialisation else None
