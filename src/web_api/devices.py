"""Device management logic for the web API."""

import os
import re
import uuid

from parking_checker.scraper import RESORT_SCRAPERS
from shared.db import validate_invitation_code, increment_invitation_code_usage
from shared.devices import (
    add_device_subscription,
    get_device,
    get_device_subscription,
    get_subscriptions_by_device,
    is_device_registered,
    register_device,
    remove_all_device_subscriptions,
    remove_device_subscription,
    update_fcm_token,
    delete_device,
    link_device_to_phone,
)

from .tokens import (
    generate_device_auth_token,
    generate_device_unsubscribe_token,
    validate_device_auth_token,
    validate_device_unsubscribe_token,
)
from .validators import validate_date, validate_phone_number, validate_resort


def validate_device_id(device_id: str) -> str | None:
    """
    Validate a device ID format.

    Args:
        device_id: Device identifier (should be a UUID)

    Returns:
        Validated device ID or None if invalid
    """
    if not device_id:
        return None

    # Accept UUIDs with or without hyphens
    cleaned = device_id.strip().lower()

    # Try to parse as UUID to validate format
    try:
        parsed = uuid.UUID(cleaned)
        return str(parsed)
    except ValueError:
        return None


def validate_fcm_token(token: str) -> str | None:
    """
    Validate an FCM token format.

    FCM tokens are typically 150+ characters, alphanumeric with some special chars.

    Args:
        token: FCM token string

    Returns:
        Validated token or None if invalid
    """
    if not token:
        return None

    token = token.strip()

    # FCM tokens are typically 150-200+ characters
    if len(token) < 100 or len(token) > 500:
        return None

    # Should be alphanumeric with some special characters
    if not re.match(r"^[A-Za-z0-9_:=-]+$", token):
        return None

    return token


def validate_platform(platform: str) -> str | None:
    """
    Validate a device platform.

    Args:
        platform: Platform string

    Returns:
        Validated platform or None if invalid
    """
    if not platform:
        return None

    platform = platform.strip().lower()

    valid_platforms = ["android", "ios", "web"]
    if platform not in valid_platforms:
        return None

    return platform


def validate_notification_type(notification_type: str) -> str | None:
    """
    Validate a notification type.

    Args:
        notification_type: Notification type string

    Returns:
        Validated notification type or None if invalid
    """
    if not notification_type:
        return "push"  # Default to push

    notification_type = notification_type.strip().lower()

    valid_types = ["push", "sms", "both"]
    if notification_type not in valid_types:
        return None

    return notification_type


def register_device_with_code(
    device_id: str,
    fcm_token: str,
    platform: str,
    invitation_code: str,
) -> tuple[bool, str, str | None]:
    """
    Register a new device using an invitation code.

    Args:
        device_id: Unique device identifier (UUID)
        fcm_token: Firebase Cloud Messaging token
        platform: Device platform ('android', 'ios', 'web')
        invitation_code: Invitation code for registration

    Returns:
        Tuple of (success, message, auth_token or None)
    """
    # Validate device ID
    validated_device_id = validate_device_id(device_id)
    if not validated_device_id:
        return False, "Invalid device ID format (must be a valid UUID)", None

    # Validate FCM token
    validated_fcm_token = validate_fcm_token(fcm_token)
    if not validated_fcm_token:
        return False, "Invalid FCM token format", None

    # Validate platform
    validated_platform = validate_platform(platform)
    if not validated_platform:
        return False, "Invalid platform. Must be 'android', 'ios', or 'web'", None

    # Check if device already registered
    if is_device_registered(validated_device_id):
        return False, "Device already registered", None

    # Validate invitation code
    if not invitation_code or not invitation_code.strip():
        return False, "Invitation code is required for new devices", None

    if not validate_invitation_code(invitation_code.strip()):
        return False, "Invalid or expired invitation code", None

    # Register the device
    register_device(
        device_id=validated_device_id,
        fcm_token=validated_fcm_token,
        platform=validated_platform,
        invitation_code=invitation_code.strip(),
    )

    # Increment invitation code usage
    increment_invitation_code_usage(invitation_code.strip())

    # Generate auth token
    auth_token = generate_device_auth_token(validated_device_id)

    return True, "Device registered successfully", auth_token


def refresh_device_token(
    device_id: str,
    new_fcm_token: str,
    auth_token: str,
) -> tuple[bool, str]:
    """
    Update the FCM token for a device.

    Args:
        device_id: Device identifier
        new_fcm_token: New FCM token
        auth_token: Device auth token for verification

    Returns:
        Tuple of (success, message)
    """
    # Validate auth token
    token_device_id = validate_device_auth_token(auth_token)
    if not token_device_id:
        return False, "Invalid auth token"

    # Validate device ID matches token
    validated_device_id = validate_device_id(device_id)
    if not validated_device_id or validated_device_id != token_device_id:
        return False, "Device ID does not match auth token"

    # Validate new FCM token
    validated_fcm_token = validate_fcm_token(new_fcm_token)
    if not validated_fcm_token:
        return False, "Invalid FCM token format"

    # Update the token
    updated = update_fcm_token(validated_device_id, validated_fcm_token)
    if not updated:
        return False, "Device not found"

    return True, "FCM token updated successfully"


def unregister_device(device_id: str, auth_token: str) -> tuple[bool, str]:
    """
    Unregister a device.

    Args:
        device_id: Device identifier
        auth_token: Device auth token for verification

    Returns:
        Tuple of (success, message)
    """
    # Validate auth token
    token_device_id = validate_device_auth_token(auth_token)
    if not token_device_id:
        return False, "Invalid auth token"

    # Validate device ID matches token
    validated_device_id = validate_device_id(device_id)
    if not validated_device_id or validated_device_id != token_device_id:
        return False, "Device ID does not match auth token"

    # Remove all subscriptions first
    remove_all_device_subscriptions(validated_device_id)

    # Delete the device
    deleted = delete_device(validated_device_id)
    if not deleted:
        return False, "Device not found"

    return True, "Device unregistered successfully"


def subscribe_device_to_alerts(
    device_id: str,
    resort: str,
    date: str,
    auth_token: str,
    notification_type: str = "push",
    phone_number: str | None = None,
) -> tuple[bool, str, str | None]:
    """
    Subscribe a device to parking alerts for a resort/date.

    Args:
        device_id: Device identifier
        resort: Resort name
        date: Date in YYYY-MM-DD format
        auth_token: Device auth token for verification
        notification_type: Type of notification ('push', 'sms', 'both')
        phone_number: Phone number (required if notification_type is 'sms' or 'both')

    Returns:
        Tuple of (success, message, unsubscribe_token or None)
    """
    # Validate auth token
    token_device_id = validate_device_auth_token(auth_token)
    if not token_device_id:
        return False, "Invalid auth token", None

    # Validate device ID matches token
    validated_device_id = validate_device_id(device_id)
    if not validated_device_id or validated_device_id != token_device_id:
        return False, "Device ID does not match auth token", None

    # Validate resort
    available = list(RESORT_SCRAPERS.keys())
    validated_resort = validate_resort(resort, available)
    if not validated_resort:
        return False, f"Invalid resort. Available: {', '.join(available)}", None

    # Validate date
    validated_date = validate_date(date)
    if not validated_date:
        return False, "Invalid date. Must be YYYY-MM-DD format and not in the past", None

    # Validate notification type
    validated_notification_type = validate_notification_type(notification_type)
    if not validated_notification_type:
        return False, "Invalid notification type. Must be 'push', 'sms', or 'both'", None

    # If SMS or both, phone number is required
    if validated_notification_type in ("sms", "both"):
        if not phone_number:
            return False, "Phone number is required for SMS notifications", None
        normalized_phone = validate_phone_number(phone_number)
        if not normalized_phone:
            return False, "Invalid phone number format", None
        # Link phone to device if not already linked
        device = get_device(validated_device_id)
        if device and not device.get("phone_number"):
            link_device_to_phone(normalized_phone, validated_device_id)

    # Check if already subscribed
    existing = get_device_subscription(validated_device_id, validated_resort, validated_date)
    if existing:
        return False, "Already subscribed to this resort/date", None

    # Generate unsubscribe token and add subscription
    unsubscribe_token = generate_device_unsubscribe_token(
        validated_device_id, validated_resort, validated_date
    )
    add_device_subscription(
        validated_device_id,
        validated_resort,
        validated_date,
        unsubscribe_token,
        validated_notification_type,
    )

    return True, "Successfully subscribed to parking alerts", unsubscribe_token


def unsubscribe_device_with_token(token: str) -> tuple[bool, str]:
    """
    Unsubscribe a device from a specific alert using an unsubscribe token.

    Args:
        token: The unsubscribe token

    Returns:
        Tuple of (success, message)
    """
    # Validate the token
    data = validate_device_unsubscribe_token(token)
    if not data:
        return False, "Invalid or expired unsubscribe token"

    device_id = data["device_id"]
    resort = data["resort"]
    date = data["date"]

    # Remove the subscription
    removed = remove_device_subscription(device_id, resort, date)
    if not removed:
        return False, "Subscription not found (may have already been removed)"

    return True, f"Unsubscribed from {resort} on {date}"


def get_device_subscriptions_list(
    device_id: str, auth_token: str
) -> tuple[bool, str, list[dict]]:
    """
    Get all subscriptions for a device.

    Args:
        device_id: Device identifier
        auth_token: Device auth token for verification

    Returns:
        Tuple of (success, message, subscriptions)
    """
    # Validate auth token
    token_device_id = validate_device_auth_token(auth_token)
    if not token_device_id:
        return False, "Invalid auth token", []

    # Validate device ID matches token
    validated_device_id = validate_device_id(device_id)
    if not validated_device_id or validated_device_id != token_device_id:
        return False, "Device ID does not match auth token", []

    subscriptions = get_subscriptions_by_device(validated_device_id)

    return (
        True,
        f"Found {len(subscriptions)} subscription(s)",
        [
            {
                "resort": s["resort_name"],
                "date": s["date"],
                "status": s.get("last_status", "unknown"),
                "notification_type": s.get("notification_type", "push"),
                "unsubscribe_token": s.get("unsubscribe_token", ""),
            }
            for s in subscriptions
        ],
    )


def get_device_info(device_id: str, auth_token: str) -> tuple[bool, str, dict | None]:
    """
    Get device information.

    Args:
        device_id: Device identifier
        auth_token: Device auth token for verification

    Returns:
        Tuple of (success, message, device_info or None)
    """
    # Validate auth token
    token_device_id = validate_device_auth_token(auth_token)
    if not token_device_id:
        return False, "Invalid auth token", None

    # Validate device ID matches token
    validated_device_id = validate_device_id(device_id)
    if not validated_device_id or validated_device_id != token_device_id:
        return False, "Device ID does not match auth token", None

    device = get_device(validated_device_id)
    if not device:
        return False, "Device not found", None

    return (
        True,
        "Device found",
        {
            "device_id": device["device_id"],
            "platform": device["platform"],
            "phone_number": device.get("phone_number"),
            "created_at": device["created_at"],
        },
    )
