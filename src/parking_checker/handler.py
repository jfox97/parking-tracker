"""
Lambda handler for ski resort parking availability checker.
"""

import json
import logging
from typing import Any

from .config import get_tracked_resorts, update_parking_state
from .notifier import send_sms
from .scraper import check_parking_availability
from .secrets import get_twilio_credentials

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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

        # Get Twilio credentials from Secrets Manager
        twilio_creds = get_twilio_credentials()

        results = []
        for resort in tracked_resorts:
            resort_name = resort["resort_name"]
            target_date = resort["date"]
            phone_number = resort["phone_number"]
            previous_status = resort.get("last_status", "unknown")

            logger.info(f"Checking parking for {resort_name} on {target_date}")

            # Check current parking availability
            current_status = check_parking_availability(resort_name, target_date)

            # If parking just became available (was unavailable, now available)
            if current_status["available"] and previous_status != "available":
                message = (
                    f"🎿 Parking available at {resort_name} for {target_date}! "
                    f"Spots: {current_status.get('spots', 'Unknown')}"
                )
                send_sms(twilio_creds, phone_number, message)
                logger.info(f"Alert sent for {resort_name}")

            # Update tracking state
            update_parking_state(resort["pk"], resort["sk"], current_status)

            results.append({
                "resort": resort_name,
                "date": target_date,
                "available": current_status["available"],
                "notified": current_status["available"] and previous_status != "available"
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
