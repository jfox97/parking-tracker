"""
Firebase Cloud Messaging (FCM) push notification module.

Uses the FCM HTTP v1 API for sending push notifications.
"""

import logging
from typing import Any

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from parking_checker.secrets import get_fcm_credentials

logger = logging.getLogger(__name__)

# FCM scopes required for sending messages
FCM_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


def _get_access_token(service_account_info: dict[str, Any]) -> str:
    """
    Get an OAuth2 access token for FCM API.

    Args:
        service_account_info: Service account credentials dict

    Returns:
        Access token string
    """
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=FCM_SCOPES,
    )
    credentials.refresh(Request())
    return credentials.token


def send_push_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
    credentials: dict[str, Any] | None = None,
) -> bool:
    """
    Send a push notification via Firebase Cloud Messaging.

    Args:
        fcm_token: The device's FCM registration token
        title: Notification title
        body: Notification body text
        data: Optional data payload (key-value pairs, all strings)
        credentials: FCM credentials dict (if None, will be fetched)

    Returns:
        True if notification sent successfully, False otherwise

    Note:
        This function does not raise exceptions for delivery failures.
        Check the return value to determine success.
    """
    if credentials is None:
        credentials = get_fcm_credentials()

    if not credentials:
        logger.warning("FCM credentials not configured, skipping push notification")
        return False

    project_id = credentials["project_id"]
    service_account_info = credentials["service_account"]

    try:
        # Get access token
        access_token = _get_access_token(service_account_info)

        # Build the FCM message
        message: dict[str, Any] = {
            "message": {
                "token": fcm_token,
                "notification": {
                    "title": title,
                    "body": body,
                },
                "android": {
                    "priority": "high",
                    "notification": {
                        "channel_id": "parking_alerts",
                        "click_action": "OPEN_APP",
                    },
                },
            }
        }

        # Add data payload if provided
        if data:
            message["message"]["data"] = data

        # Send the message via FCM HTTP v1 API
        url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, headers=headers, json=message, timeout=10)

        if response.status_code == 200:
            logger.info(f"Push notification sent successfully to {fcm_token[:20]}...")
            return True
        else:
            logger.error(
                f"Failed to send push notification: {response.status_code} - {response.text}"
            )
            # Check for specific errors that indicate invalid tokens
            if response.status_code == 404 or "UNREGISTERED" in response.text:
                logger.warning(f"FCM token appears to be invalid: {fcm_token[:20]}...")
            return False

    except Exception as e:
        logger.error(f"Error sending push notification: {e}", exc_info=True)
        return False


def send_parking_alert(
    fcm_token: str,
    resort_name: str,
    target_date: str,
    spots_info: str | int | None,
    unsubscribe_token: str | None = None,
) -> bool:
    """
    Send a parking availability alert via push notification.

    This is a convenience wrapper around send_push_notification with
    pre-formatted message content for parking alerts.

    Args:
        fcm_token: The device's FCM registration token
        resort_name: Name of the resort (e.g., "brighton")
        target_date: Date for the reservation (YYYY-MM-DD)
        spots_info: Number of spots or description
        unsubscribe_token: Optional unsubscribe token for data payload

    Returns:
        True if notification sent successfully
    """
    # Format the resort name for display
    display_name = resort_name.replace("-", " ").title()

    title = f"Parking Available!"
    body = f"{display_name} has parking for {target_date}."
    if spots_info:
        body += f" Spots: {spots_info}"

    # Build data payload
    data = {
        "type": "parking_alert",
        "resort": resort_name,
        "date": target_date,
    }
    if unsubscribe_token:
        data["unsubscribe_token"] = unsubscribe_token

    return send_push_notification(fcm_token, title, body, data)
