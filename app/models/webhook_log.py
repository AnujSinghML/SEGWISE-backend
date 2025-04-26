import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db import Base

class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Used to identify retries of the same webhook
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False)
    target_url = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=True)
    payload = Column(JSONB, nullable=False)
    attempt_number = Column(Integer, nullable=False, default=1)
    status_code = Column(Integer, nullable=True)  # HTTP status code, null if couldn't reach
    status = Column(String(50), nullable=False)  # SUCCESS, FAILED_ATTEMPT, FAILURE
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_webhook_log_delivery_id', delivery_id),
        Index('idx_webhook_log_subscription_id', subscription_id),
        Index('idx_webhook_log_created_at', created_at),  # For log retention cleanup
    )
    
    def __repr__(self):
        return f"<WebhookLog(id={self.id}, delivery_id={self.delivery_id}, attempt={self.attempt_number})>"