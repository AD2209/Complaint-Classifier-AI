from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ComplaintBase(BaseModel):
    user_details: str
    description: str
    attachment_path: Optional[str] = None

class ComplaintCreate(ComplaintBase):
    pass

class ComplaintResponse(ComplaintBase):
    id: str
    category: str
    urgency: str
    advice: Optional[str] = None
    action_taken: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
