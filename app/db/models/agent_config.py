# app/db/models/agent_config.py

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from app.db.base import Base


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(
        Integer,
        ForeignKey("agents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    model_name = Column(String(100), nullable=False, index=True)
    temperature = Column(Float, default=0.7)
    system_prompt = Column(Text, nullable=True)
    allowed_sources = Column(ARRAY(String(100)), nullable=True, default=[])
    tone_id = Column(Integer, ForeignKey("tones.id"), nullable=True)
    welcome_message = Column(Text, nullable=True)
    theme_id =Column(Integer, ForeignKey("theme_config.id"), nullable=True)
  
    
    agent = relationship("Agent", back_populates="config")
    tone = relationship("Tone", back_populates="config")
    theme = relationship("ThemeConfig", back_populates="config")
