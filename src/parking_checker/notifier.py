"""
Twilio SMS notification module.
"""

import logging

from twilio.rest import Client

logger = logging.getLogger(__name__)


def send_sms(credentials: dict[str, str], to_number: str, message: str) -> bool:
    """
    Send an SMS notification via Twilio.

    Args:
        credentials: Dict with account_sid, auth_token, from_number
        to_number: Recipient phone number (E.164 format)
        message: Message text to send

    Returns:
        True if message sent successfully

    Raises:
        Exception: If SMS sending fails
    """
    client = Client(credentials["account_sid"], credentials["auth_token"])

    msg = client.messages.create(
        body=message,
        from_=credentials["from_number"],
        to=to_number
    )

    logger.info(f"SMS sent successfully. SID: {msg.sid}")
    return True
