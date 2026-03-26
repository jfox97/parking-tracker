"""
DynamoDB configuration management for tracked resorts.

Note: This module now uses the updated schema with:
- pk: DATE#{YYYY-MM-DD}
- sk: RESORT#{resort-name}#PHONE#{phone-number}

For the full database operations, see shared.db module.
"""

import os
from datetime import date
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr


def get_dynamodb_table():
    """Get the DynamoDB table resource."""
    table_name = os.environ.get("CONFIG_TABLE")
    if not table_name:
        raise RuntimeError("CONFIG_TABLE environment variable not set")

    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)


def get_tracked_resorts() -> list[dict[str, Any]]:
    """
    Get all resorts being tracked for today or future dates.

    Returns:
        List of resort tracking configurations
    """
    table = get_dynamodb_table()
    today = date.today().isoformat()

    # Scan for all subscription entries with dates >= today
    # Filter by sk pattern to only get subscription records
    response = table.scan(
        FilterExpression=Attr("date").gte(today) & Attr("sk").begins_with("RESORT#")
    )

    items: list[dict[str, Any]] = response.get("Items", [])
    return items


def update_parking_state(pk: str, sk: str, status: dict[str, Any]) -> None:
    """
    Update the parking state for a tracked resort.

    Args:
        pk: Partition key
        sk: Sort key
        status: Current parking status dict
    """
    table = get_dynamodb_table()

    table.update_item(
        Key={"pk": pk, "sk": sk},
        UpdateExpression="SET last_status = :status, last_checked = :checked",
        ExpressionAttributeValues={
            ":status": "available" if status["available"] else "unavailable",
            ":checked": status.get("checked_at", ""),
        }
    )


def add_tracking(
    resort_name: str,
    target_date: str,
    phone_number: str,
    unsubscribe_token: str = "",
) -> None:
    """
    Add a new resort/date to track.

    Args:
        resort_name: Name of the resort
        target_date: Date to track (YYYY-MM-DD format)
        phone_number: Phone number to notify (E.164 format)
        unsubscribe_token: Token for unsubscribing (optional)
    """
    table = get_dynamodb_table()

    item: dict[str, Any] = {
        "pk": f"DATE#{target_date}",
        "sk": f"RESORT#{resort_name}#PHONE#{phone_number}",
        "resort_name": resort_name,
        "date": target_date,
        "phone_number": phone_number,
        "last_status": "unknown",
    }

    if unsubscribe_token:
        item["unsubscribe_token"] = unsubscribe_token

    table.put_item(Item=item)


def remove_tracking(resort_name: str, target_date: str, phone_number: str) -> None:
    """
    Remove a resort/date from tracking.

    Args:
        resort_name: Name of the resort
        target_date: Date to stop tracking (YYYY-MM-DD format)
        phone_number: Phone number (E.164 format)
    """
    table = get_dynamodb_table()

    table.delete_item(
        Key={
            "pk": f"DATE#{target_date}",
            "sk": f"RESORT#{resort_name}#PHONE#{phone_number}",
        }
    )
