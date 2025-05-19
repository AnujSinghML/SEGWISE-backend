# Webhook Delivery Service
Link: [https://bit.ly/segwise_anujsingh](https://bit.ly/segwise_anujsingh)

A robust backend system that functions as a reliable webhook delivery service. It ingests incoming webhooks, queues them, and attempts delivery to subscribed target URLs, handling failures with retries and providing visibility into the delivery status.

## Table of Contents
- [Setup & Installation](#setup--installation)
- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [Webhook Service API Guide](#webhook-service-api-guide)
- [Features](#features)
- [Libraries and Tools](#libraries-and-tools)
- [Credits](#credits)

## Setup & Installation

### Prerequisites

- Docker and Docker Compose

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/AnujSinghML/SEGWISE-backend.git
   ```

2. Start the containers:
   ```bash
   docker-compose up --build -d
   ```

3. Access the API documentation at http://localhost:8000/docs

### Live Demo
You can also try the live demo at [https://bit.ly/segwise_anujsingh](https://bit.ly/segwise_anujsingh)

## Architecture

This webhook delivery service is designed with the following components:

- **FastAPI REST API**: Provides endpoints for subscription management, webhook ingestion, and status checking
- **PostgreSQL Database**: Stores subscription data and webhook delivery logs (running in Docker)
- **Redis**: Used for caching subscription details and as a message broker for Celery (running in Docker)
- **Celery Workers**: Processes webhook delivery tasks asynchronously with retry capabilities
- **Celery Beat**: Schedules periodic tasks such as log cleanup

### Key Design Decisions

- **FastAPI**: Chosen for its high performance, automatic documentation via Swagger UI, and async support
- **PostgreSQL**: Used for its reliability and ability to handle complex queries for webhook logs
- **Celery with Redis**: Provides robust task queueing with retry mechanisms
- **Docker & Docker Compose**: Containerizes all components for easy deployment and local development

## Database Schema

- **Subscriptions**:
  - `id` (UUID): Unique identifier for the subscription
  - `target_url` (String): URL where webhooks will be delivered
  - `secret_key` (String, optional): Used for signature verification
  - `event_types` (Text, optional): Comma-separated list of event types
  - `is_active` (Boolean): Indicates if the subscription is active
  - `created_at` (DateTime): When the subscription was created
  - `updated_at` (DateTime): When the subscription was last updated

- **Webhook Logs**:
  - `id` (UUID): Unique identifier for the log entry
  - `delivery_id` (UUID): Identifier for tracking all attempts of a specific webhook delivery
  - `subscription_id` (UUID): References the subscription
  - `target_url` (String): URL where delivery was attempted
  - `event_type` (String, optional): Type of event
  - `payload` (JSONB): The webhook payload
  - `attempt_number` (Integer): Which attempt this is (1 for initial, 2+ for retries)
  - `status_code` (Integer, optional): HTTP status code received
  - `status` (String): SUCCESS, FAILED_ATTEMPT, or FAILURE
  - `error_details` (Text, optional): Error details if applicable
  - `created_at` (DateTime): When this attempt was made

### Indexing Strategy

- Index on `webhook_logs.delivery_id` for fast lookup of delivery attempts
- Index on `webhook_logs.subscription_id` for subscription delivery history
- Index on `webhook_logs.created_at` for efficient log retention cleanup
- Index on `subscriptions.id` for fast subscription lookup

## Webhook Service API Guide

### Interactive API Documentation

The fastest way to explore this API is through our interactive documentation at http://localhost:8000/docs

This Swagger UI lets you test all endpoints directly without writing a line of code. Perfect for a quick demonstration!

### Setting Up Webhook Subscriptions

#### Create a new subscription with event filtering and send your own secret key (used in payload verification)

```bash
curl -X POST "http://localhost:8000/subscriptions/" \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://your-service.com/webhook-endpoint",
    "secret_key": "your-secret-key",
    "event_types": ["order.created", "payment.successful"]
  }'
```

The `event_types` array lets you specify exactly which events this subscription should receive.
The `secret_key` here can be set to `null` if you do not want verification.

The API will return a subscription ID - you'll need this for the next steps!

#### Manage your subscriptions

```bash
# Get all subscriptions
curl -X GET "http://localhost:8000/subscriptions/"

# Get details for a specific subscription
curl -X GET "http://localhost:8000/subscriptions/{subscription_id}"

# Update a subscription
curl -X PATCH "http://localhost:8000/subscriptions/{subscription_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "event_types": ["order.created", "order.updated", "order.canceled"],
    "is_active": true
  }'
```

### Event Type Filtering 

One of the key features implemented is intelligent event type filtering:

- When creating a subscription, specify which event types you want to receive
- When sending a webhook, include the event type in the `x-webhook-event` header
- The system will automatically route webhooks only to subscriptions that have registered interest in that event type

This prevents subscribers from receiving irrelevant events and reduces unnecessary traffic.

### Webhook Signature Verification Made Easy 

The most impressive part of this implementation is the secure webhook signature verification. Let me show you how it works:

#### 1. Generate a Signature with Our Helper Tool

We've made security easy with a built-in signature generator (make sure to use same secret-key as before):

```bash
curl -X POST "http://localhost:8000/tools/signature-generator" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "event": "order.created",
      "data": {
        "order_id": "12345",
        "amount": 99.99
      }
    },
    "secret_key": "your-secret-key"
  }'
```

The tool will give you the exact signature header you need - no cryptography knowledge required!

#### 2. Send a Signed Webhook with Event Type

Using the signature from the previous step:

```bash
curl -X POST "http://localhost:8000/ingest/{subscription_id}" \
  -H "Content-Type: application/json" \
  -H "x-webhook-event: order.created" \
  -H "x-hub-signature-256: sha256=generated_signature_value" \
  -d '{
    "event": "order.created",
    "data": {
      "order_id": "12345",
      "amount": 99.99
    }
  }'
```

The system will:

- Verify the signature matches the payload (using HMAC-SHA256)
- Check if the subscription is interested in the "order.created" event type
- Only deliver the webhook if both conditions are met

### Security Features Implemented

This webhook service includes:

- HMAC-SHA256 signature verification
- Secure secret key handling
- Event type filtering and matching
- Comprehensive delivery logs
- Automatic retry logic

### Testing the Complete Flow

For a quick demonstration of the full system:

1. Create a subscription with a secret key and specific event types
2. Generate a signature for your test payload
3. Send the webhook with the correct signature and event type
4. Try sending an event type not in the subscription's list (it should be filtered)
5. Try an invalid signature to confirm security works
6. Check the delivery logs to see successful processing

## Features

✅ Subscription Management (CRUD operations)  
✅ Webhook Ingestion  
✅ Asynchronous Delivery Processing  
✅ Exponential Backoff Retry Mechanism  
✅ Comprehensive Delivery Logging  
✅ Log Retention Policy  
✅ Status/Analytics Endpoints  
✅ Caching for Performance Optimization  
✅ Payload Signature Verification (Bonus) [using SHA-256]  
✅ Event Type Filtering (Bonus)  

## Libraries and Tools

- FastAPI: High-performance web framework
- SQLAlchemy: SQL toolkit and ORM
- Celery: Distributed task queue
- Redis: In-memory data store and message broker
- PostgreSQL: Robust relational database
- Docker & Docker Compose: Containerization and orchestration
- Alembic: Database migration tool
- Pydantic: Data validation and settings management
- httpx: HTTP client
- Webhook.site: For testing ingestions (payload)

## Credits

Libraries and tools are acknowledged inline. Assignment developed with assistance from online documentation and best practices.
