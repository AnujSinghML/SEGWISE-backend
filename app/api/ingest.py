import json
import uuid
from fastapi import APIRouter, Body, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.subscription import Subscription
from app.schemas.webhook import WebhookIngestion
from app.workers.tasks import deliver_webhook
from app.utils import verify_signature

router = APIRouter(
    prefix="/ingest",
    tags=["Webhook Ingestion (Payload)"],
)

@router.post("/{subscription_id}", status_code=status.HTTP_202_ACCEPTED)
async def ingest_webhook(
    subscription_id: uuid.UUID,
    payload: dict = Body(..., example={"event": "order.created", "data": {"order_id": 123, "amount": 99.99}}),
    x_hub_signature_256: str = Header(None),
    x_webhook_event: str = Header(None),
    db: Session = Depends(get_db)
):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription with ID {subscription_id} not found"
        )
    
    body_bytes = json.dumps(payload).encode('utf-8')
    
    if subscription.secret_key and x_hub_signature_256:
        signature = x_hub_signature_256
        if signature.startswith("sha256="):
            signature = signature[7:]
            
        if not verify_signature(body_bytes, signature, subscription.secret_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
    elif subscription.secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature required"
        )
    
    delivery_id = str(uuid.uuid4())
    event_type = x_webhook_event
    
    deliver_webhook.delay(
        delivery_id=delivery_id,
        subscription_id=str(subscription_id),
        payload=payload,
        attempt_number=1,
        event_type=event_type
    )
    
    return {
        "status": "accepted",
        "delivery_id": delivery_id,
        "message": "Webhook queued for delivery"
    }