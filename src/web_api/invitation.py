"""Invitation code management for the web API."""

from shared.db import (
    increment_invitation_code_usage,
    is_phone_registered,
    register_phone,
    validate_invitation_code,
)

from .tokens import generate_master_unsubscribe_token


def check_invitation_required(phone_number: str) -> bool:
    """
    Check if an invitation code is required for this phone number.

    New phone numbers require an invitation code.
    Already registered phones can subscribe without one.

    Args:
        phone_number: Phone number in E.164 format

    Returns:
        True if invitation code is required
    """
    return not is_phone_registered(phone_number)


def process_invitation(phone_number: str, invitation_code: str) -> tuple[bool, str]:
    """
    Process an invitation code for a new phone number registration.

    Args:
        phone_number: Phone number in E.164 format
        invitation_code: The invitation code to use

    Returns:
        Tuple of (success, error_message)
    """
    if not invitation_code:
        return False, "Invitation code is required for new phone numbers"

    if not validate_invitation_code(invitation_code):
        return False, "Invalid or expired invitation code"

    # Generate master unsubscribe token for this phone
    master_token = generate_master_unsubscribe_token(phone_number)

    # Register the phone number
    register_phone(phone_number, master_token, invitation_code)

    # Increment the invitation code usage
    increment_invitation_code_usage(invitation_code)

    return True, ""


def verify_invitation_code(code: str) -> bool:
    """
    Verify if an invitation code is valid.

    Args:
        code: The invitation code to verify

    Returns:
        True if the code is valid and has remaining uses
    """
    return validate_invitation_code(code)
