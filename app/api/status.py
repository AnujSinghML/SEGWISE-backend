from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db import get_db
from app.models.webhook_log import WebhookLog
from app.models.subscription import Subscription
from app.schemas.webhook import WebhookLogEntry, DeliveryStatus, SubscriptionDeliveryStats

router = APIRouter(
    prefix="/status",
    tags=["Delivery Status"],
)

# Helper function to convert WebhookLog ORM model to WebhookLogEntry Pydantic model
def webhook_log_to_entry(log: WebhookLog) -> WebhookLogEntry:
    return WebhookLogEntry(
        id=log.id,
        delivery_id=log.delivery_id,
        subscription_id=log.subscription_id,
        target_url=log.target_url,
        event_type=log.event_type,
        attempt_number=log.attempt_number,
        status_code=log.status_code,
        status=log.status,
        error_details=log.error_details,
        created_at=log.created_at,
        payload=log.payload  # Make sure to include payload if it exists in your WebhookLogEntry model
    )

@router.get("/deliveries/{delivery_id}", response_model=DeliveryStatus)
def get_delivery_status(
    delivery_id: UUID,
    db: Session = Depends(get_db)
):
    try:
        # Get all log entries for this delivery ID
        logs = db.query(WebhookLog).filter(WebhookLog.delivery_id == delivery_id).order_by(WebhookLog.created_at).all()
        
        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No delivery found with ID {delivery_id}"
            )
        
        # Get the latest log entry
        latest_log = logs[-1]
        
        # Convert ORM WebhookLog objects to WebhookLogEntry Pydantic models
        log_entries = [webhook_log_to_entry(log) for log in logs]
        
        return DeliveryStatus(
            delivery_id=delivery_id,
            subscription_id=latest_log.subscription_id,
            total_attempts=len(logs),
            latest_status=latest_log.status,
            latest_attempt=latest_log.created_at,
            logs=log_entries  # Use the converted list
        )
    except Exception as e:
        # Log the error
        print(f"Error retrieving delivery status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving delivery status"
        )

@router.get("/subscriptions/{subscription_id}/deliveries", response_model=SubscriptionDeliveryStats)
def get_subscription_deliveries(
    subscription_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    try:
        # Check if subscription exists
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with ID {subscription_id} not found"
            )
        
        # Get delivery statistics
        # Count total deliveries (unique delivery_ids)
        delivery_count = db.query(func.count(WebhookLog.delivery_id.distinct()))\
            .filter(WebhookLog.subscription_id == subscription_id)\
            .scalar()
        
        # Count successful deliveries
        successful_count = db.query(func.count(WebhookLog.delivery_id.distinct()))\
            .filter(WebhookLog.subscription_id == subscription_id, WebhookLog.status == "SUCCESS")\
            .scalar()
        
        # Count failed deliveries (those that reached FAILURE status)
        failed_count = db.query(func.count(WebhookLog.delivery_id.distinct()))\
            .filter(WebhookLog.subscription_id == subscription_id, WebhookLog.status == "FAILURE")\
            .scalar()
        
        # Get recent log entries, ordered by creation time (newest first)
        recent_logs = db.query(WebhookLog)\
            .filter(WebhookLog.subscription_id == subscription_id)\
            .order_by(desc(WebhookLog.created_at))\
            .limit(limit)\
            .all()
        
        # Convert ORM objects to Pydantic models
        log_entries = [webhook_log_to_entry(log) for log in recent_logs]
        
        return SubscriptionDeliveryStats(
            subscription_id=subscription_id,
            total_deliveries=delivery_count,
            successful_deliveries=successful_count,
            failed_deliveries=failed_count,
            recent_logs=log_entries  # Use the converted list
        )
    except HTTPException:
        raise
    except Exception as e:
        # Log the error
        print(f"Error retrieving subscription deliveries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving subscription deliveries"
        )