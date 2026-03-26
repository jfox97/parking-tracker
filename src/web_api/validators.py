"""Input validation for web API requests."""

import re
from datetime import datetime


def validate_phone_number(phone: str) -> str | None:
    """
    Validate and normalize a phone number to E.164 format.

    Args:
        phone: Phone number input

    Returns:
        Normalized phone number or None if invalid
    """
    if not phone:
        return None

    # Remove common formatting characters
    cleaned = re.sub(r"[\s\-\.\(\)]", "", phone)

    # Handle US numbers without country code
    if cleaned.startswith("1") and len(cleaned) == 11:
        cleaned = "+" + cleaned
    elif len(cleaned) == 10 and cleaned[0] != "+":
        cleaned = "+1" + cleaned

    # Ensure it starts with +
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    # Validate E.164 format: + followed by 10-15 digits
    if not re.match(r"^\+[1-9]\d{9,14}$", cleaned):
        return None

    return cleaned


def validate_date(date_str: str) -> str | None:
    """
    Validate a date string and ensure it's not in the past.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Validated date string or None if invalid
    """
    if not date_str:
        return None

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

    # Don't allow dates in the past
    if date_obj < datetime.now().date():
        return None

    return date_str


def validate_resort(resort: str, available_resorts: list[str]) -> str | None:
    """
    Validate a resort name against available resorts.

    Args:
        resort: Resort name input
        available_resorts: List of valid resort names

    Returns:
        Validated resort name or None if invalid
    """
    if not resort:
        return None

    # Normalize to lowercase for comparison
    resort_lower = resort.lower().strip()

    for available in available_resorts:
        if available.lower() == resort_lower:
            return available

    return None
