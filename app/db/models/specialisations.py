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
from app.db.base import Base


class Specialisation(Base):
    __tablename__ = "specialisations"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), unique=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    is_active = Column(Boolean, nullable=False, default=True)
