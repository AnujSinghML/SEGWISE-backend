from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, HttpUrl, validator
from datetime import datetime

class SubscriptionBase(BaseModel):
    target_url: HttpUrl
    secret_key: Optional[str] = None
    event_types: Optional[List[str]] = None
    
    @validator('event_types', pre=True)
    def parse_event_types(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(',') if x.strip()]
        return v

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionUpdate(BaseModel):
    target_url: Optional[HttpUrl] = None
    secret_key: Optional[str] = None
    event_types: Optional[List[str]] = None
    is_active: Optional[bool] = None

class SubscriptionResponse(SubscriptionBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    @validator('event_types', pre=True)
    def parse_event_types_response(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [x.strip() for x in v.split(',') if x.strip()]
        return v
    
    class Config:
        orm_mode = True