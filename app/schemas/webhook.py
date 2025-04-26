from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

class WebhookIngestion(BaseModel):
    payload: Dict[str, Any]
    event_type: Optional[str] = None

class WebhookDeliveryTask(BaseModel):
    delivery_id: UUID
    subscription_id: UUID
    target_url: str
    payload: Dict[str, Any]
    attempt_number: int
    event_type: Optional[str] = None
    secret_key: Optional[str] = None

class WebhookLogEntry(BaseModel):
    id: UUID
    delivery_id: UUID
    subscription_id: UUID
    target_url: str
    event_type: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None  
    attempt_number: int
    status_code: Optional[int] = None
    status: str
    error_details: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True  # This is the Pydantic v2 equivalent of orm_mode = True

class DeliveryStatus(BaseModel):
    delivery_id: UUID
    subscription_id: UUID
    total_attempts: int
    latest_status: str
    latest_attempt: datetime
    logs: List[WebhookLogEntry]

class SubscriptionDeliveryStats(BaseModel):
    subscription_id: UUID
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    recent_logs: List[WebhookLogEntry]