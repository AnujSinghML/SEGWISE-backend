#!/usr/bin/env python
import sys
import os
import logging
from datetime import datetime, timedelta

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from app.models.webhook_log import WebhookLog
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_old_logs():
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

if __name__ == "__main__":
    cleanup_old_logs()