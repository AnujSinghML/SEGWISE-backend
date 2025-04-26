import uuid
from sqlalchemy import Column, String, Boolean, Text, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db import Base

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_url = Column(String(255), nullable=False)
    secret_key = Column(String(255), nullable=True)
    event_types = Column(Text, nullable=True)  # Comma-separated list of event types
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_subscription_id', id),
    )
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, target_url={self.target_url})>"