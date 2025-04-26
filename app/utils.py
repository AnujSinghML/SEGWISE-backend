import hmac
import hashlib
import uuid
from typing import Optional, Dict, Any

def generate_hmac_signature(payload: bytes, secret: str) -> str:
    """Generate HMAC signature for webhook payload"""
    return hmac.new(
        key=secret.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature"""
    expected_signature = generate_hmac_signature(payload, secret)
    return hmac.compare_digest(expected_signature, signature)

def generate_delivery_id() -> str:
    """Generate a unique delivery ID for tracking webhook delivery attempts"""
    return str(uuid.uuid4())

def should_deliver_to_subscription(event_type: Optional[str], subscription_event_types: Optional[str]) -> bool:
    """
    Check if webhook should be delivered to subscription based on event type
    
    Args:
        event_type: The event type of the incoming webhook
        subscription_event_types: Comma-separated list of event types the subscription is interested in
        
    Returns:
        bool: True if webhook should be delivered, False otherwise
    """
    # If no event type filtering is set up, deliver to all subscriptions
    if not subscription_event_types or not subscription_event_types.strip():
        return True
    
    # If webhook has no event type but subscription requires specific types, don't deliver
    if not event_type:
        return False
    
    # Check if webhook event type matches any of the subscription's event types
    subscription_types = [t.strip() for t in subscription_event_types.split(',') if t.strip()]
    return event_type in subscription_types

def calculate_next_retry_delay(attempt: int, base_delay: int, backoff_factor: int) -> int:
    """
    Calculate delay for next retry attempt using exponential backoff
    
    Args:
        attempt: Current attempt number (1-based)
        base_delay: Initial delay in seconds
        backoff_factor: Backoff multiplier factor
        
    Returns:
        int: Delay in seconds for the next retry
    """
    return base_delay * (backoff_factor ** (attempt - 1))