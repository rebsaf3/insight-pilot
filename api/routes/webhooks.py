"""Webhook endpoints — Stripe payment webhooks."""

from fastapi import APIRouter, Request, HTTPException

from services.stripe_service import handle_webhook

router = APIRouter()


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle incoming Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    result = handle_webhook(payload, sig_header)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Webhook error"))

    return {"status": "ok"}
