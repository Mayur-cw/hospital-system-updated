import hashlib
import hmac
import os
import uuid
from abc import ABC, abstractmethod
from decimal import Decimal


class GatewayError(Exception):
    pass


class PaymentGateway(ABC):
    @abstractmethod
    def create_order(self, amount: Decimal, currency: str = "INR", receipt: str = "") -> dict:
        """Create payment order."""
        pass

    @abstractmethod
    def verify_payment(self, payload: dict) -> bool:
        """Verify signature or transaction authenticity."""
        pass


class MockGateway(PaymentGateway):
    """Deterministic Mock Gateway for local development and CI tests."""

    def create_order(self, amount: Decimal, currency: str = "INR", receipt: str = "") -> dict:
        order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
        return {
            "order_id": order_id,
            "amount": float(amount),
            "currency": currency,
            "receipt": receipt,
            "status": "created"
        }

    def verify_payment(self, payload: dict) -> bool:
        # Mock payment succeeds unless explicitly marked failure in payload
        return payload.get("status") != "failed"


class RazorpayGateway(PaymentGateway):
    """Razorpay adapter using HMAC-SHA256 signature verification."""

    def __init__(self, key_id: str | None = None, key_secret: str | None = None):
        self.key_id = key_id or os.environ.get("RAZORPAY_KEY_ID", "rzp_test_placeholder")
        self.key_secret = key_secret or os.environ.get("RAZORPAY_KEY_SECRET", "rzp_secret_placeholder")

    def create_order(self, amount: Decimal, currency: str = "INR", receipt: str = "") -> dict:
        # Amount in paise (integer)
        amount_paise = int(amount * 100)
        order_id = f"order_rzp_{uuid.uuid4().hex[:14]}"
        return {
            "order_id": order_id,
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "status": "created",
            "key_id": self.key_id
        }

    def verify_payment(self, payload: dict) -> bool:
        order_id = payload.get("razorpay_order_id", "")
        payment_id = payload.get("razorpay_payment_id", "")
        signature = payload.get("razorpay_signature", "")

        if not (order_id and payment_id and signature):
            return False

        message = f"{order_id}|{payment_id}".encode("utf-8")
        expected_signature = hmac.new(
            self.key_secret.encode("utf-8"),
            message,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)


def get_payment_gateway() -> PaymentGateway:
    """Factory function for payment gateway based on config."""
    gateway_type = os.environ.get("PAYMENT_GATEWAY", "mock").lower()
    if gateway_type == "razorpay":
        return RazorpayGateway()
    return MockGateway()
