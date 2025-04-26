from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
import logging

from app.api import subscriptions, ingest, status
from app.db import Base, engine
from app.cache.redis import is_redis_available  # health
from app.api import subscriptions, ingest, status, tools 

# Initialize database tables 
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Webhook Delivery Service",
    description="""
    A reliable webhook delivery service that ingests, queues, and delivers webhooks with 
    automatic retries and comprehensive delivery tracking.
    
    ## Key Features
    * 📝 Create and manage webhook subscriptions
    * 📨 Ingest and queue webhook payloads
    * 🔄 Automatic retries with exponential backoff
    * 🔐 Payload signature verification 
    * 🔍 Delivery status tracking
    * 📊 Analytics on webhook deliveries
    
    Use the interactive API documentation below to explore and test the service.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
        "syntaxHighlight.theme": "monokai"
    }
)
# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(subscriptions.router, prefix="/subscriptions", tags=["CRUD Ops for Subscriptions"])
app.include_router(tools.router, prefix="/tools", tags=["Generate Signature for payload"])
app.include_router(ingest.router, prefix="/ingest", tags=["Webhook Ingestion (Payload)"])
app.include_router(status.router, prefix="/status", tags=["Delivery Status"])

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


# Temporary Redis health check
# @app.get("/redis-health", tags=["health"])
# async def redis_health_check():
#     if is_redis_available():
#         return {"status": "Redis connected"}
#     else:
#         return {"status": "Redis not connected"}


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    logging.info("Starting Webhook Delivery Service")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Shutting down Webhook Delivery Service")
