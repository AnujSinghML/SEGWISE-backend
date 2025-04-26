from fastapi import APIRouter, Body
import json
from app.utils import generate_hmac_signature

router = APIRouter()

@router.post("/signature-generator", summary="Generate webhook signature")
async def signature_generator(
    payload: dict = Body(..., 
                       example={"event": "order.created", "data": {"id": 123}}),
    secret_key: str = Body(..., 
                         example="yourSecretKey123")
):
    """
    Tool to generate valid webhook signatures for testing.
    
    ## How to use:
    1. Enter your webhook payload and the secret key
    2. Copy the generated x-hub-signature-256 header value
    3. Use this header when sending requests to /ingest/{subscription_id}
    
    This makes testing webhook signature verification easy!
    """
    payload_bytes = json.dumps(payload).encode('utf-8')
    signature = generate_hmac_signature(payload_bytes, secret_key)
    
    return {
        "x_hub_signature_256": f"sha256={signature}",
        "instructions": "Add this header to your webhook request",
        "curl_example": f"""
curl -X POST "http://yourapi.com/ingest/YOUR_SUBSCRIPTION_ID" \\
     -H "Content-Type: application/json" \\
     -H "x-hub-signature-256: sha256={signature}" \\
     -d '{json.dumps(payload)}'
        """
    }