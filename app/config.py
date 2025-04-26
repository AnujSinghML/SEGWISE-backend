import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL")

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND")
    BROKER_USE_SSL: bool = os.getenv("BROKER_USE_SSL", "false").lower() == "true"
    RESULT_BACKEND_USE_SSL: bool = os.getenv("RESULT_BACKEND_USE_SSL", "false").lower() == "true"

    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", 8000))

    # Webhook Delivery
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "5"))
    RETRY_BACKOFF_FACTOR: int = int(os.getenv("RETRY_BACKOFF_FACTOR", "2"))
    INITIAL_RETRY_DELAY: int = int(os.getenv("INITIAL_RETRY_DELAY", "10"))
    WEBHOOK_TIMEOUT: int = int(os.getenv("WEBHOOK_TIMEOUT", "5"))

    # Log Retention
    LOG_RETENTION_HOURS: int = int(os.getenv("LOG_RETENTION_HOURS", "72"))

settings = Settings()
