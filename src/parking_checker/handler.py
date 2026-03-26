"""
Lambda handler for ski resort parking availability checker.
"""

import json
import logging
import os
from typing import Any

from .config import get_tracked_resorts, update_parking_state
from .notifier import send_sms
from .push_notifier import send_parking_alert
from .scraper import check_parking_availability
from .secrets import get_fcm_credentials, get_twilio_credentials

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _build_unsubscribe_url(token: str) -> str:
    """Build the unsubscribe URL for SMS messages."""
    domain = os.environ.get("DOMAIN_NAME", "parking.foxjason.com")
    return f"https://{domain}/unsubscribe.html?token={token}"


def _is_device_subscription(subscription: dict[str, Any]) -> bool:
    """Check if a subscription is device-based (vs phone-based)."""
    sk = subscription.get("sk", "")
    return "#DEVICE#" in sk


def _get_device_fcm_token(device_id: str) -> str | None:
    """Get the FCM token for a device."""
    try:
        from shared.devices import get_device
        device = get_device(device_id)
        if device:
            return device.get("fcm_token")
    except Exception as e:
        logger.error(f"Error getting device FCM token: {e}")
    return None


def _send_notification(
    subscription: dict[str, Any],
    current_status: dict[str, Any],
    twilio_creds: dict[str, str],
    fcm_creds: dict[str, Any],
) -> tuple[bool, str]:
    """
    Send a notification for a subscription based on its type.

    Args:
        subscription: The subscription record
        current_status: Current parking status
        twilio_creds: Twilio credentials
        fcm_creds: FCM credentials

    Returns:
        Tuple of (success, notification_type)
    """
    resort_name = subscription["resort_name"]
    target_date = subscription["date"]
    spots_info = current_status.get("spots", "Unknown")
    unsubscribe_token = subscription.get("unsubscribe_token", "")

    # Determine notification type
    notification_type = subscription.get("notification_type", "sms")

    # For device subscriptions, default to push
    if _is_device_subscription(subscription):
        notification_type = subscription.get("notification_type", "push")

    notifications_sent = []

    # Send SMS notification
    if notification_type in ("sms", "both"):
        phone_number = subscription.get("phone_number")
        if phone_number:
            message = (
                f"Parking available at {resort_name.replace('-', ' ').title()} "
                f"for {target_date}! Spots: {spots_info}"
            )
            if unsubscribe_token:
                unsubscribe_url = _build_unsubscribe_url(unsubscribe_token)
                message += f"\n\nUnsubscribe: {unsubscribe_url}"

            try:
                send_sms(twilio_creds, phone_number, message)
                notifications_sent.append("sms")
                logger.info(f"SMS sent for {resort_name} to {phone_number}")
            except Exception as e:
                logger.error(f"Failed to send SMS: {e}")

    # Send push notification
    if notification_type in ("push", "both"):
        device_id = subscription.get("device_id")
        if device_id:
            fcm_token = _get_device_fcm_token(device_id)
            if fcm_token and fcm_creds:
                success = send_parking_alert(
                    fcm_token=fcm_token,
                    resort_name=resort_name,
                    target_date=target_date,
                    spots_info=spots_info,
                    unsubscribe_token=unsubscribe_token,
                )
                if success:
                    notifications_sent.append("push")
                    logger.info(f"Push sent for {resort_name} to device {device_id[:8]}...")
            else:
                if not fcm_token:
                    logger.warning(f"No FCM token found for device {device_id}")
                if not fcm_creds:
                    logger.warning("FCM credentials not configured")

    return len(notifications_sent) > 0, ",".join(notifications_sent) if notifications_sent else "none"


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main Lambda handler - runs every minute to check parking availability.

    Args:
        event: CloudWatch Events scheduled event
        context: Lambda context object

    Returns:
        Response dict with status and results
    """
    logger.info("Starting parking availability check")

    try:
        # Get all resorts we're tracking for today
        tracked_resorts = get_tracked_resorts()

        if not tracked_resorts:
            logger.info("No resorts being tracked for today")
            return {"statusCode": 200, "body": json.dumps({"message": "No resorts to check"})}

        # Get credentials from Secrets Manager
        twilio_creds = get_twilio_credentials()
        fcm_creds = get_fcm_credentials()

        results = []
        for subscription in tracked_resorts:
            resort_name = subscription["resort_name"]
            target_date = subscription["date"]
            previous_status = subscription.get("last_status", "unknown")

            # Identify subscription target (phone or device)
            is_device = _is_device_subscription(subscription)
            target_id = (
                subscription.get("device_id", "unknown")
                if is_device
                else subscription.get("phone_number", "unknown")
            )

            logger.info(f"Checking parking for {resort_name} on {target_date}")

            # Check current parking availability
            current_status = check_parking_availability(resort_name, target_date)

            notification_sent = False
            notification_type = "none"

            # If parking just became available (was unavailable, now available)
            if current_status["available"] and previous_status != "available":
                notification_sent, notification_type = _send_notification(
                    subscription, current_status, twilio_creds, fcm_creds
                )

            # Update tracking state
            update_parking_state(subscription["pk"], subscription["sk"], current_status)

            results.append({
                "resort": resort_name,
                "date": target_date,
                "target": target_id if not is_device else f"device:{target_id[:8]}...",
                "type": "device" if is_device else "phone",
                "available": current_status["available"],
                "notified": notification_sent,
                "notification_type": notification_type,
            })

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Check complete", "results": results})
        }

    except Exception as e:
        logger.error(f"Error checking parking: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
