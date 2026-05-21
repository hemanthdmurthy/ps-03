from datetime import datetime
from pydantic import BaseModel

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    type: str  # 'info', 'placement', 'alert', 'system'
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationCreate(BaseModel):
    user_id: str
    title: str
    message: str
    type: str = "info"

class NotificationMarkRead(BaseModel):
    is_read: bool = True
