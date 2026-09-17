import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean,func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from sqlalchemy.orm import relationship



class ThemeConfig(Base):
    __tablename__ = "theme_config"

    id = Column(Integer, primary_key=True, index=True)

    # Multi-tenant linkage
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    #  UI Customization
    primary_color = Column(String(10))
    font_family = Column(String(50))

    widget_position = Column(String(20))  # bottom_right, top_left
    widget_size = Column(String(20))  # small, medium, large

    # Icons & Avatars
    widget_launcher_icon = Column(String)  # file path or URL
    bot_avatar = Column(String)  # file path or URL

    # Notification Settings
    hide_estimated_wait_time = Column(Boolean, default=False)
    disable_sound_notification = Column(Boolean, default=False)

    #  Visibility Settings
    hide_widget_when_offline = Column(Boolean, default=False)

    # ⏱Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    config = relationship("AgentConfig", back_populates="theme")

