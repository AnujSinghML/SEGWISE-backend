from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.subscription import Subscription
from app.schemas.subscription import (
    SubscriptionCreate, 
    SubscriptionUpdate, 
    SubscriptionResponse
)
from app.cache.redis import invalidate_subscription_cache

router = APIRouter(
    prefix="/subscriptions",
    tags=["CRUD Ops for Subscriptions"],
)

@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    subscription: SubscriptionCreate,
    db: Session = Depends(get_db)
):
    # Convert event_types from list to comma-separated string
    event_types_str = None
    if subscription.event_types:
        event_types_str = ",".join(subscription.event_types)
    
    # Create new subscription
    db_subscription = Subscription(
        target_url=str(subscription.target_url),
        secret_key=subscription.secret_key,
        event_types=event_types_str
    )
    
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    
    return db_subscription

@router.get("/", response_model=List[SubscriptionResponse])
def get_subscriptions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    subscriptions = db.query(Subscription).offset(skip).limit(limit).all()
    return subscriptions

@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db)
):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription with ID {subscription_id} not found"
        )
    return subscription

@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(
    subscription_id: UUID,
    subscription_update: SubscriptionUpdate,
    db: Session = Depends(get_db)
):
    db_subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not db_subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription with ID {subscription_id} not found"
        )
    
    # Handle event_types conversion from list to string
    if subscription_update.event_types is not None:
        subscription_update_dict = subscription_update.dict(exclude_unset=True)
        if "event_types" in subscription_update_dict:
            subscription_update_dict["event_types"] = ",".join(subscription_update.event_types)
    else:
        subscription_update_dict = subscription_update.dict(exclude_unset=True)
    
    # Update subscription
    for key, value in subscription_update_dict.items():
        setattr(db_subscription, key, value)
    
    db.commit()
    db.refresh(db_subscription)
    
    # Invalidate cache
    invalidate_subscription_cache(str(subscription_id))
    
    return db_subscription

@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    subscription_id: UUID,
    db: Session = Depends(get_db)
):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription with ID {subscription_id} not found"
        )
    
    db.delete(subscription)
    db.commit()
    
    # Invalidate cache
    invalidate_subscription_cache(str(subscription_id))
    
    return None