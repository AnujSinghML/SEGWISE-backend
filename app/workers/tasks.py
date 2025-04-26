import json
import httpx
import logging
from uuid import UUID
from datetime import datetime, timedelta
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db import SessionLocal
from app.config import settings
from app.models.webhook_log import WebhookLog
from app.models.subscription import Subscription
from app.cache.redis import get_cached_subscription, cache_subscription
from app.utils import calculate_next_retry_delay, should_deliver_to_subscription

# Set up logging
logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=None)
def deliver_webhook(
    self,
    delivery_id: str,
    subscription_id: str,
    payload: dict,
    attempt_number: int = 1,
    event_type: str = None
):
    """
    Attempt to deliver a webhook to the target URL
    
    This task will retry itself with exponential backoff if delivery fails,
    up to the configured maximum retry attempts.
    """
    logger.info(f"Delivering webhook {delivery_id} to subscription {subscription_id}, attempt {attempt_number}")
    
    db = SessionLocal()
    
    try:
        # Get subscription info (first from cache, then from DB)
        subscription_data = get_cached_subscription(subscription_id)
        
        if not subscription_data:
            # Cache miss, fetch from DB
            subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
            if not subscription:
                logger.error(f"Subscription {subscription_id} not found")
                log_delivery_result(
                    db, delivery_id, subscription_id, None, 
                    payload, attempt_number, None, "FAILURE", 
                    "Subscription not found", event_type
                )
                return
            
            subscription_data = {
                "id": str(subscription.id),
                "target_url": subscription.target_url,
                "secret_key": subscription.secret_key,
                "event_types": subscription.event_types,
                "is_active": subscription.is_active
            }
            
            # Cache subscription data for future use
            cache_subscription(str(subscription.id), subscription_data)
        
        # Check if subscription is active
        if not subscription_data["is_active"]:
            logger.info(f"Subscription {subscription_id} is inactive, skipping delivery")
            log_delivery_result(
                db, delivery_id, subscription_id, subscription_data["target_url"], 
                payload, attempt_number, None, "FAILURE", 
                "Subscription is inactive", event_type
            )
            return
        
        # Check if this webhook should be delivered based on event type
        if not should_deliver_to_subscription(event_type, subscription_data.get("event_types")):
            logger.info(f"Webhook event type {event_type} doesn't match subscription {subscription_id} event types")
            log_delivery_result(
                db, delivery_id, subscription_id, subscription_data["target_url"], 
                payload, attempt_number, None, "FAILURE", 
                f"Event type {event_type} doesn't match subscription filters", event_type
            )
            return
            
        # Attempt delivery
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Webhook-Delivery-Service/1.0",
            "X-Webhook-ID": delivery_id,
        }
        
        # Add signature header if secret key is available
        if subscription_data.get("secret_key"):
            payload_bytes = json.dumps(payload).encode('utf-8')
            from app.utils import generate_hmac_signature
            signature = generate_hmac_signature(payload_bytes, subscription_data["secret_key"])
            headers["X-Hub-Signature-256"] = f"sha256={signature}"
        
        # Add event type header if available
        if event_type:
            headers["X-Webhook-Event"] = event_type
        
        # Make the HTTP request
        with httpx.Client(timeout=settings.WEBHOOK_TIMEOUT) as client:
            response = client.post(
                subscription_data["target_url"],
                json=payload,
                headers=headers
            )
            
            # Check if request was successful (2xx status code)
            if 200 <= response.status_code < 300:
                logger.info(f"Successfully delivered webhook {delivery_id} to {subscription_data['target_url']}")
                log_delivery_result(
                    db, delivery_id, subscription_id, subscription_data["target_url"], 
                    payload, attempt_number, response.status_code, "SUCCESS", 
                    None, event_type
                )
                return
            
            # Non-2xx response
            error_message = f"Target returned status code: {response.status_code}"
            logger.warning(f"Failed to deliver webhook {delivery_id}: {error_message}")
            
            # Determine if we should retry
            if attempt_number < settings.MAX_RETRY_ATTEMPTS:
                log_delivery_result(
                    db, delivery_id, subscription_id, subscription_data["target_url"], 
                    payload, attempt_number, response.status_code, "FAILED_ATTEMPT", 
                    error_message, event_type
                )
                
                # Schedule retry with exponential backoff
                next_attempt = attempt_number + 1
                delay = calculate_next_retry_delay(
                    attempt_number,
                    settings.INITIAL_RETRY_DELAY,
                    settings.RETRY_BACKOFF_FACTOR
                )
                
                logger.info(f"Scheduling retry {next_attempt} for webhook {delivery_id} in {delay} seconds")
                deliver_webhook.apply_async(
                    args=[delivery_id, subscription_id, payload, next_attempt, event_type],
                    countdown=delay
                )
            else:
                # Max retries reached
                logger.error(f"Maximum retry attempts reached for webhook {delivery_id}")
                log_delivery_result(
                    db, delivery_id, subscription_id, subscription_data["target_url"], 
                    payload, attempt_number, response.status_code, "FAILURE", 
                    f"Maximum retry attempts reached. Last error: {error_message}", event_type
                )
                
    except httpx.RequestError as e:
        # Network-related error
        error_message = f"Request error: {str(e)}"
        logger.warning(f"Failed to deliver webhook {delivery_id}: {error_message}")
        
        if attempt_number < settings.MAX_RETRY_ATTEMPTS:
            log_delivery_result(
                db, delivery_id, subscription_id, subscription_data["target_url"], 
                payload, attempt_number, None, "FAILED_ATTEMPT", 
                error_message, event_type
            )
            
            # Schedule retry with exponential backoff
            next_attempt = attempt_number + 1
            delay = calculate_next_retry_delay(
                attempt_number,
                settings.INITIAL_RETRY_DELAY,
                settings.RETRY_BACKOFF_FACTOR
            )
            
            logger.info(f"Scheduling retry {next_attempt} for webhook {delivery_id} in {delay} seconds")
            deliver_webhook.apply_async(
                args=[delivery_id, subscription_id, payload, next_attempt, event_type],
                countdown=delay
            )
        else:
            # Max retries reached
            logger.error(f"Maximum retry attempts reached for webhook {delivery_id}")
            log_delivery_result(
                db, delivery_id, subscription_id, subscription_data["target_url"], 
                payload, attempt_number, None, "FAILURE", 
                f"Maximum retry attempts reached. Last error: {error_message}", event_type
            )
            
    except Exception as e:
        # Unexpected error
        error_message = f"Unexpected error: {str(e)}"
        logger.error(f"Error delivering webhook {delivery_id}: {error_message}")
        log_delivery_result(
            db, delivery_id, subscription_id, subscription_data["target_url"], 
            payload, attempt_number, None, "FAILURE", 
            error_message, event_type
        )
    finally:
        db.close()

def log_delivery_result(
    db: Session,
    delivery_id: str,
    subscription_id: str,
    target_url: str,
    payload: dict,
    attempt_number: int,
    status_code: int = None,
    status: str = "FAILED_ATTEMPT",
    error_details: str = None,
    event_type: str = None
):
    """Log the result of a webhook delivery attempt"""
    log_entry = WebhookLog(
        delivery_id=delivery_id,
        subscription_id=subscription_id,
        target_url=target_url,
        event_type=event_type,
        payload=payload,
        attempt_number=attempt_number,
        status_code=status_code,
        status=status,
        error_details=error_details
    )
    
    db.add(log_entry)
    db.commit()

@celery_app.task
def cleanup_old_webhook_logs():
    """Delete webhook logs that are older than the retention period"""
    db = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=settings.LOG_RETENTION_HOURS)
        logger.info(f"Cleaning up webhook logs older than {cutoff_time}")
        
        # Delete logs older than the cutoff time
        result = db.query(WebhookLog).filter(WebhookLog.created_at < cutoff_time).delete()
        db.commit()
        
        logger.info(f"Deleted {result} old webhook logs")
    except Exception as e:
        logger.error(f"Error cleaning up old webhook logs: {str(e)}")
        db.rollback()
    finally:
        db.close()