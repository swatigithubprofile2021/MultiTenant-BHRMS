from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean,func
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class Tone(Base):
    __tablename__ = "tones"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(50),unique=True, nullable=False)
    description = Column(String(255))
    is_default = Column(Boolean, default=False)    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    
    created_by = Column(Integer, ForeignKey("users.id"))    
    updated_by = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    
    creator = relationship("User",  foreign_keys=[created_by])
    updater = relationship("User",  foreign_keys=[updated_by])
    
    config = relationship("AgentConfig", back_populates="tone")

