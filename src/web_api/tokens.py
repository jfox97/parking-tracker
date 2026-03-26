"""
HMAC-based token generation and validation for unsubscribe links.

Tokens are self-contained and can be validated without a database lookup.
"""

import base64
import hashlib
import hmac
import os
from typing import Any

from parking_checker.secrets import get_token_secret


def generate_unsubscribe_token(phone: str, resort: str, date: str) -> str:
    """
    Generate a secure unsubscribe token for a specific subscription.

    The token encodes phone:resort:date and a signature, allowing
    validation without a database lookup.

    Args:
        phone: Phone number (E.164 format)
        resort: Resort name
        date: Date (YYYY-MM-DD format)

    Returns:
        URL-safe base64 encoded token
    """
    secret = get_token_secret()
    payload = f"{phone}:{resort}:{date}"

    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    # Combine payload and signature
    token_data = payload + "|" + base64.b64encode(signature).decode("utf-8")
    return base64.urlsafe_b64encode(token_data.encode("utf-8")).decode("utf-8")


def validate_unsubscribe_token(token: str) -> dict[str, Any] | None:
    """
    Validate an unsubscribe token and extract the subscription details.

    Args:
        token: The token to validate

    Returns:
        Dict with phone, resort, date if valid; None if invalid
    """
    try:
        secret = get_token_secret()

        # Decode the token
        token_data = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        payload, provided_sig_b64 = token_data.rsplit("|", 1)
        provided_sig = base64.b64decode(provided_sig_b64)

        # Verify the signature
        expected_sig = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(provided_sig, expected_sig):
            return None

        # Extract the data
        phone, resort, date = payload.split(":")
        return {"phone": phone, "resort": resort, "date": date}

    except Exception:
        return None


def generate_master_unsubscribe_token(phone: str) -> str:
    """
    Generate a master unsubscribe token that unsubscribes from all alerts.

    Args:
        phone: Phone number (E.164 format)

    Returns:
        URL-safe base64 encoded token
    """
    secret = get_token_secret()
    payload = f"MASTER:{phone}"

    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    token_data = payload + "|" + base64.b64encode(signature).decode("utf-8")
    return base64.urlsafe_b64encode(token_data.encode("utf-8")).decode("utf-8")


def validate_master_unsubscribe_token(token: str) -> str | None:
    """
    Validate a master unsubscribe token.

    Args:
        token: The token to validate

    Returns:
        Phone number if valid; None if invalid
    """
    try:
        secret = get_token_secret()

        token_data = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        payload, provided_sig_b64 = token_data.rsplit("|", 1)
        provided_sig = base64.b64decode(provided_sig_b64)

        expected_sig = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(provided_sig, expected_sig):
            return None

        if not payload.startswith("MASTER:"):
            return None

        return payload[7:]  # Remove "MASTER:" prefix

    except Exception:
        return None


def build_unsubscribe_url(token: str) -> str:
    """
    Build the full unsubscribe URL for inclusion in SMS messages.

    Args:
        token: The unsubscribe token

    Returns:
        Full URL to the unsubscribe page
    """
    domain = os.environ.get("DOMAIN_NAME", "parking.foxjason.com")
    return f"https://{domain}/unsubscribe.html?token={token}"


# =============================================================================
# Device Authentication Tokens
# =============================================================================


def generate_device_auth_token(device_id: str) -> str:
    """
    Generate an auth token for a device.

    The token encodes DEVICE:device_id and a signature, allowing
    validation without a database lookup.

    Args:
        device_id: Unique device identifier

    Returns:
        URL-safe base64 encoded token
    """
    secret = get_token_secret()
    payload = f"DEVICE:{device_id}"

    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    token_data = payload + "|" + base64.b64encode(signature).decode("utf-8")
    return base64.urlsafe_b64encode(token_data.encode("utf-8")).decode("utf-8")


def validate_device_auth_token(token: str) -> str | None:
    """
    Validate a device auth token and extract the device ID.

    Args:
        token: The token to validate

    Returns:
        Device ID if valid; None if invalid
    """
    try:
        secret = get_token_secret()

        token_data = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        payload, provided_sig_b64 = token_data.rsplit("|", 1)
        provided_sig = base64.b64decode(provided_sig_b64)

        expected_sig = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(provided_sig, expected_sig):
            return None

        if not payload.startswith("DEVICE:"):
            return None

        return payload[7:]  # Remove "DEVICE:" prefix

    except Exception:
        return None


def generate_device_unsubscribe_token(device_id: str, resort: str, date: str) -> str:
    """
    Generate a secure unsubscribe token for a device subscription.

    Args:
        device_id: Device identifier
        resort: Resort name
        date: Date (YYYY-MM-DD format)

    Returns:
        URL-safe base64 encoded token
    """
    secret = get_token_secret()
    payload = f"DEVICE_SUB:{device_id}:{resort}:{date}"

    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    token_data = payload + "|" + base64.b64encode(signature).decode("utf-8")
    return base64.urlsafe_b64encode(token_data.encode("utf-8")).decode("utf-8")


def validate_device_unsubscribe_token(token: str) -> dict[str, Any] | None:
    """
    Validate a device unsubscribe token and extract the subscription details.

    Args:
        token: The token to validate

    Returns:
        Dict with device_id, resort, date if valid; None if invalid
    """
    try:
        secret = get_token_secret()

        token_data = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        payload, provided_sig_b64 = token_data.rsplit("|", 1)
        provided_sig = base64.b64decode(provided_sig_b64)

        expected_sig = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(provided_sig, expected_sig):
            return None

        if not payload.startswith("DEVICE_SUB:"):
            return None

        # Remove prefix and split
        parts = payload[11:].split(":")
        if len(parts) != 3:
            return None

        device_id, resort, date = parts
        return {"device_id": device_id, "resort": resort, "date": date}

    except Exception:
        return None
