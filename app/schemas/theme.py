from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from enum import Enum
from app.schemas.document import Pageination

class ThemeAssetType(str,Enum):
    widget_launcher = "widget_launcher"
    bot_avatar = "bot_avatar"


class ThemeCreate(BaseModel):
    # tenant_id: int
    primary_color: Optional[str] = None
    font_family: Optional[str] = None
    widget_position: Optional[str] = None
    widget_size: Optional[str] = None
    widget_launcher_icon: Optional[str] = None
    bot_avatar: Optional[str] = None
    hide_estimated_wait_time: Optional[bool] = None
    disable_sound_notification: Optional[bool] = None
    hide_widget_when_offline: Optional[bool]= None


class ThemeUpdate(BaseModel):
    primary_color: Optional[str] = None
    font_family: Optional[str] = None   
    widget_position: Optional[str] = None
    widget_size: Optional[str] = None
    widget_launcher_icon: Optional[str] = None
    bot_avatar: Optional[str] = None
    hide_estimated_wait_time: Optional[bool] = None
    disable_sound_notification: Optional[bool] = None
    hide_widget_when_offline: Optional[bool] = None


class ThemeResponse(BaseModel):
    id: int
    tenant_id: int
    primary_color: Optional[str]
    font_family: Optional[str]
    widget_position: Optional[str]
    widget_size: Optional[str]
    widget_launcher_icon: Optional[str]
    bot_avatar: Optional[str]
    hide_estimated_wait_time: Optional[bool]
    disable_sound_notification: Optional[bool]
    hide_widget_when_offline: Optional[bool]  
    
    

    class Config:
        from_attributes = True


class ThemeResponseList(BaseModel):
    themes: list[ThemeResponse]
    pagination: Pageination
    
    class Config:
        from_attributes = True
    

