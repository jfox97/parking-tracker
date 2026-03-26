"""Subscription management logic for the web API."""

from parking_checker.scraper import RESORT_SCRAPERS
from shared.db import (
    add_subscription,
    get_phone_record,
    get_subscription,
    get_subscriptions_by_phone,
    remove_all_subscriptions,
    remove_subscription,
)

from .invitation import check_invitation_required, process_invitation
from .tokens import (
    generate_unsubscribe_token,
    validate_master_unsubscribe_token,
    validate_unsubscribe_token,
)
from .validators import validate_date, validate_phone_number, validate_resort


def get_available_resorts() -> list[dict[str, str]]:
    """
    Get list of available resorts that can be tracked.

    Returns:
        List of resort info dicts with name and display_name
    """
    return [
        {"name": name, "display_name": name.replace("-", " ").title()}
        for name in RESORT_SCRAPERS.keys()
    ]


def subscribe_to_alerts(
    phone_number: str,
    resort: str,
    date: str,
    invitation_code: str | None = None,
) -> tuple[bool, str, str | None]:
    """
    Subscribe a phone number to parking alerts for a resort/date.

    Args:
        phone_number: Phone number (will be normalized)
        resort: Resort name
        date: Date in YYYY-MM-DD format
        invitation_code: Invitation code (required for new phones)

    Returns:
        Tuple of (success, message, unsubscribe_url or None)
    """
    # Validate phone number
    normalized_phone = validate_phone_number(phone_number)
    if not normalized_phone:
        return False, "Invalid phone number format", None

    # Validate resort
    available = list(RESORT_SCRAPERS.keys())
    validated_resort = validate_resort(resort, available)
    if not validated_resort:
        return False, f"Invalid resort. Available: {', '.join(available)}", None

    # Validate date
    validated_date = validate_date(date)
    if not validated_date:
        return False, "Invalid date. Must be YYYY-MM-DD format and not in the past", None

    # Check if invitation code is required
    if check_invitation_required(normalized_phone):
        success, error = process_invitation(normalized_phone, invitation_code or "")
        if not success:
            return False, error, None

    # Check if already subscribed
    existing = get_subscription(normalized_phone, validated_resort, validated_date)
    if existing:
        return False, "Already subscribed to this resort/date", None

    # Generate unsubscribe token and add subscription
    token = generate_unsubscribe_token(normalized_phone, validated_resort, validated_date)
    add_subscription(normalized_phone, validated_resort, validated_date, token)

    # Build unsubscribe URL
    import os

    domain = os.environ.get("DOMAIN_NAME", "parking.foxjason.com")
    unsubscribe_url = f"https://{domain}/unsubscribe.html?token={token}"

    return True, "Successfully subscribed to parking alerts", unsubscribe_url


def unsubscribe_with_token(token: str) -> tuple[bool, str]:
    """
    Unsubscribe from a specific alert using an unsubscribe token.

    Args:
        token: The unsubscribe token

    Returns:
        Tuple of (success, message)
    """
    # Validate the token
    data = validate_unsubscribe_token(token)
    if not data:
        return False, "Invalid or expired unsubscribe token"

    phone = data["phone"]
    resort = data["resort"]
    date = data["date"]

    # Remove the subscription
    removed = remove_subscription(phone, resort, date)
    if not removed:
        return False, "Subscription not found (may have already been removed)"

    return True, f"Unsubscribed from {resort} on {date}"


def unsubscribe_all_with_token(token: str) -> tuple[bool, str, int]:
    """
    Unsubscribe from all alerts using a master unsubscribe token.

    Args:
        token: The master unsubscribe token

    Returns:
        Tuple of (success, message, count_removed)
    """
    # Validate the token
    phone = validate_master_unsubscribe_token(token)
    if not phone:
        return False, "Invalid or expired unsubscribe token", 0

    # Remove all subscriptions
    count = remove_all_subscriptions(phone)

    if count == 0:
        return True, "No active subscriptions found", 0

    return True, f"Unsubscribed from all {count} alert(s)", count


def get_subscriptions_for_phone(token: str) -> tuple[bool, str, list[dict]]:
    """
    Get all subscriptions for a phone using a master unsubscribe token.

    Args:
        token: The master unsubscribe token

    Returns:
        Tuple of (success, message, subscriptions)
    """
    # Validate the token
    phone = validate_master_unsubscribe_token(token)
    if not phone:
        return False, "Invalid or expired token", []

    subscriptions = get_subscriptions_by_phone(phone)

    return (
        True,
        f"Found {len(subscriptions)} subscription(s)",
        [
            {
                "resort": s["resort_name"],
                "date": s["date"],
                "status": s.get("last_status", "unknown"),
            }
            for s in subscriptions
        ],
    )


def get_master_token_for_phone(phone_number: str) -> str | None:
    """
    Get the master unsubscribe token for a registered phone.

    Args:
        phone_number: Phone number in E.164 format

    Returns:
        Master unsubscribe token or None if not registered
    """
    normalized = validate_phone_number(phone_number)
    if not normalized:
        return None

    record = get_phone_record(normalized)
    if not record:
        return None

    return record.get("master_unsubscribe_token")


def send_unsubscribe_link(phone_number: str) -> tuple[bool, str]:
    """
    Send an SMS with the master unsubscribe link to a phone number.

    Args:
        phone_number: Phone number to send the link to

    Returns:
        Tuple of (success, message)
    """
    import logging
    import os

    from parking_checker.notifier import send_sms
    from parking_checker.secrets import get_twilio_credentials

    # Validate phone number
    normalized_phone = validate_phone_number(phone_number)
    if not normalized_phone:
        return False, "Invalid phone number format"

    # Get master token for this phone
    token = get_master_token_for_phone(normalized_phone)
    if not token:
        # Don't reveal whether the phone exists or not for security
        return True, "If this phone has active subscriptions, you'll receive an SMS shortly"

    # Check if they have any subscriptions
    subscriptions = get_subscriptions_by_phone(normalized_phone)
    if not subscriptions:
        return True, "If this phone has active subscriptions, you'll receive an SMS shortly"

    # Build unsubscribe URL
    domain = os.environ.get("DOMAIN_NAME", "parking.foxjason.com")
    unsubscribe_url = f"https://{domain}/unsubscribe.html?token={token}"

    # Send SMS
    try:
        credentials = get_twilio_credentials()
        message = (
            f"Parking Tracker: Click to manage your {len(subscriptions)} subscription(s): "
            f"{unsubscribe_url}"
        )
        send_sms(credentials, normalized_phone, message)
        return True, "Unsubscribe link sent! Check your phone for an SMS."
    except Exception as e:
        logging.error(f"Failed to send unsubscribe SMS: {e}")
        return False, "Failed to send SMS. Please try again later."
