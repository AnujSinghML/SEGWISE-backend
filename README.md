# Webhook Delivery Service
Link : [https://bit.ly/segwise_anujsingh](https://bit.ly/segwise_anujsingh)

A robust backend system that functions as a reliable webhook delivery service. It ingests incoming webhooks, queues them, and attempts delivery to subscribed target URLs, handling failures with retries and providing visibility into the delivery status.

> **Note for Recruiters:**
> 
> A very, very rare case scenario — but I'm mentioning it anyway, because better safe than sorry!
> 
> If you ever encounter a **500: Internal Server Error**, or face some issue connecting to **Redis** during the Docker build, please know it's not due to any problem in the application itself.  
> It’s because I'm using **free-tier databases**, and well... they sometimes go to sleep!  
> 
> Kindly **try again** in such cases.  
> 
> - For webhook ingestion, **retry logic** is implemented using **Celery**, so it should handle temporary failures smoothly.  
> - For CRUD operations, I can only hope the DB stays awake! 😅
> 
> As much as free tiers are advertised, we all know they like to nap from time to time. xD



## Table of Contents
- [Setup & Installation](#setup--installation)
- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [Webhook Service API Guide](#webhook-service-api-guide)
- [Deployment Components](#deployment-components)
- [Cost Estimate](#cost-estimate-247-operation)
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

2. Start the containers: (make sure you are in correct directory for composing the docker image : cd SEGWISE-backend)
   ```bash
   docker-compose up --build -d
   ```

3. Access the website at http://localhost:8000/docs in your local machine.

## Architecture

This webhook delivery service is designed with the following components:

- **FastAPI REST API**: Provides endpoints for subscription management, webhook ingestion, and status checking
- **Neon (PostgreSQL) Database**: Stores subscription data and webhook delivery logs
- **Redis**: Used for caching subscription details and as a message broker for Celery
- **Celery Workers**: Processes webhook delivery tasks asynchronously with retry capabilities
- **Celery Beat**: Schedules periodic tasks such as log cleanup

### Key Design Decisions

- **FastAPI**: Chosen for its high performance, automatic documentation via Swagger UI, and async support
- **Neon (Cloud PostgreSQL)**: Used for its reliability and ability to handle complex queries for webhook logs
- **Celery with Redis**: Provides robust task queueing with retry mechanisms
- **Docker & Docker Compose**: Containerizes all components for easy deployment

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

### Try it in Your Browser! 
[https://bit.ly/segwise_anujsingh](https://bit.ly/segwise_anujsingh)

The fastest way to explore this API is through our interactive documentation!

In case my AWS EC2 instance goes to sleep for xyz reason; can never trust free tiers much..

Just clone,build and go to--> 

```
http://localhost:8000/docs
```

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
(although you can find implementation related info further in the documentation about our utils.py)

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

### Utility Functions

The implementation includes robust utility functions in the `utils.py` file:

- `generate_hmac_signature()`: Creates HMAC-SHA256 signatures for webhook payloads
- `verify_signature()`: Securely compares computed signatures with provided ones
- Event type parsing and filtering logic

These utilities follow industry best practices for webhook security and event filtering.

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

I've implemented industry-standard security practices while keeping the API intuitive and developer-friendly. The signature verification follows the same patterns used by GitHub, Stripe, and other major platforms, while the event filtering system provides an efficient way to route only relevant events to subscribers.

## Deployment Components


### **Virtual Machine Alternative**
  - **AWS EC2 t3.micro**: AWS Free Tier covers 750 hr/mo for 12 months. So that is what I did : [https://bit.ly/segwise_anujsingh](https://bit.ly/segwise_anujsingh)

### Render Option (paid for celery)
- **Celery Worker** (background task processor)
  - **Render**: Basic-256 MB background worker at \$6/month. Free plan is a 30‑day trial only.
  - Must run on a persistent host—serverless/free dynos will suspend idle workers.

- **Redis Broker & Cache**
  - **Redis Cloud Essentials**: Free 30 MB plan (30 connections, ~5 GB/mo bandwidth). Suitable for development; consider the \$5/mo 1 GB tier for heavier loads.

- **PostgreSQL Database**
  - **Neon Cloud Free Plan**: 0.5 GB storage, ~190 compute hours/mo, auto‑scale‑to‑zero. Ideal for prototyping but capped beyond free limits.

## Cost Estimate (24×7 Operation)

Assuming 5000 ingested webhooks/day with 1.2 delivery attempts each (≈6,000 attempts/day, 180,000/mo) and ~1 KB payloads (~0.18 GB egress/mo):

- **Render Background Worker**: \$6.00/mo
- **Redis Cloud Essentials**: \$0.00/mo
- **Neon Cloud Free Plan**: \$0.00/mo

**Total with Render**: \$6.00 per month

### Assumptions

1. **Webhook Volume:** 5,000/day → ~6,000 delivery attempts/day.
2. **Payload Size:** ~1 KB per request.
3. **Redis Free Tier:** 30 MB, 30 connections.
4. **Neon Free Plan:** 0.5 GB storage, 190 compute hours/mo.
5. **Persistent Workers:** Celery must run on always‑on infrastructure.

*All prices are current as of April 2025.*

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

- FastAPI: Web framework
- SQLAlchemy: ORM for database access
- Celery: Task queue
- Redis: Cache and message broker
- Pydantic: Data validation
- httpx: HTTP client
- Docker & Docker Compose: Containerization
- Webhook.site: For testing ingestions (payload)

## Credits

Libraries and tools are acknowledged inline. Assignment developed with assistance from online documentation and best practices.
