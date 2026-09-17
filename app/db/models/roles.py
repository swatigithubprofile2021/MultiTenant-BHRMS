from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DATETIME, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.models.association import role_permissions
from app.db.models.permissions import Permission


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    # Permissions linked to this role
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        cascade="all, delete",
    )

    users = relationship("User", back_populates="role")
