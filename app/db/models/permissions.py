from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.models.association import role_permissions


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)  # for backend logic
    name = Column(String(100), nullable=False)  # for UI display

    # Roles that have this permission (many-to-many)
    roles = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )
