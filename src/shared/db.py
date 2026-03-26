"""
DynamoDB operations for parking tracker.

Schema:
- Subscriptions: pk=DATE#{date}, sk=RESORT#{resort}#PHONE#{phone}
- Phone registry: pk=PHONE#{phone}, sk=META
- Invitation codes: pk=INVITE#{code}, sk=CODE
"""

import os
from datetime import datetime
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key


def get_dynamodb_table():
    """Get the DynamoDB table resource."""
    table_name = os.environ.get("CONFIG_TABLE")
    if not table_name:
        raise RuntimeError("CONFIG_TABLE environment variable not set")

    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)


# =============================================================================
# Subscription Operations
# =============================================================================


def get_tracked_resorts() -> list[dict[str, Any]]:
    """
    Get all resorts being tracked for today or future dates.

    Returns:
        List of subscription records
    """
    table = get_dynamodb_table()
    today = datetime.now().strftime("%Y-%m-%d")

    # Scan for all tracking entries with dates >= today
    response = table.scan(
        FilterExpression=Attr("date").gte(today) & Attr("sk").begins_with("RESORT#")
    )

    items: list[dict[str, Any]] = response.get("Items", [])
    return items


def add_subscription(
    phone_number: str,
    resort_name: str,
    target_date: str,
    unsubscribe_token: str,
) -> None:
    """
    Add a new subscription for parking alerts.

    Args:
        phone_number: Phone number in E.164 format
        resort_name: Name of the resort
        target_date: Date to track (YYYY-MM-DD format)
        unsubscribe_token: Token for unsubscribing from this specific alert
    """
    table = get_dynamodb_table()

    table.put_item(
        Item={
            "pk": f"DATE#{target_date}",
            "sk": f"RESORT#{resort_name}#PHONE#{phone_number}",
            "phone_number": phone_number,
            "resort_name": resort_name,
            "date": target_date,
            "unsubscribe_token": unsubscribe_token,
            "last_status": "unknown",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
    )


def get_subscription(
    phone_number: str, resort_name: str, target_date: str
) -> dict[str, Any] | None:
    """
    Get a specific subscription.

    Returns:
        Subscription record or None if not found
    """
    table = get_dynamodb_table()

    response = table.get_item(
        Key={
            "pk": f"DATE#{target_date}",
            "sk": f"RESORT#{resort_name}#PHONE#{phone_number}",
        }
    )

    return response.get("Item")


def remove_subscription(phone_number: str, resort_name: str, target_date: str) -> bool:
    """
    Remove a subscription.

    Returns:
        True if deleted, False if not found
    """
    table = get_dynamodb_table()

    response = table.delete_item(
        Key={
            "pk": f"DATE#{target_date}",
            "sk": f"RESORT#{resort_name}#PHONE#{phone_number}",
        },
        ReturnValues="ALL_OLD",
    )

    return "Attributes" in response


def get_subscriptions_by_phone(phone_number: str) -> list[dict[str, Any]]:
    """
    Get all subscriptions for a phone number using the GSI.

    Returns:
        List of subscription records
    """
    table = get_dynamodb_table()

    response = table.query(
        IndexName="phone-number-index",
        KeyConditionExpression=Key("phone_number").eq(phone_number),
    )

    # Filter to only return subscription records (not phone META records)
    items = [
        item
        for item in response.get("Items", [])
        if item.get("sk", "").startswith("RESORT#")
    ]

    return items


def remove_all_subscriptions(phone_number: str) -> int:
    """
    Remove all subscriptions for a phone number.

    Returns:
        Number of subscriptions removed
    """
    subscriptions = get_subscriptions_by_phone(phone_number)
    table = get_dynamodb_table()

    for sub in subscriptions:
        table.delete_item(Key={"pk": sub["pk"], "sk": sub["sk"]})

    return len(subscriptions)


def update_subscription_status(pk: str, sk: str, status: dict[str, Any]) -> None:
    """
    Update the parking status for a subscription.

    Args:
        pk: Partition key
        sk: Sort key
        status: Current parking status dict with 'available' and optional 'checked_at'
    """
    table = get_dynamodb_table()

    table.update_item(
        Key={"pk": pk, "sk": sk},
        UpdateExpression="SET last_status = :status, last_checked = :checked",
        ExpressionAttributeValues={
            ":status": "available" if status["available"] else "unavailable",
            ":checked": status.get("checked_at", ""),
        },
    )


# =============================================================================
# Phone Registry Operations
# =============================================================================


def get_phone_record(phone_number: str) -> dict[str, Any] | None:
    """
    Get the phone registry record.

    Returns:
        Phone record or None if phone not registered
    """
    table = get_dynamodb_table()

    response = table.get_item(Key={"pk": f"PHONE#{phone_number}", "sk": "META"})

    return response.get("Item")


def register_phone(
    phone_number: str,
    master_unsubscribe_token: str,
    invitation_code: str,
) -> None:
    """
    Register a new phone number.

    Args:
        phone_number: Phone number in E.164 format
        master_unsubscribe_token: Token for unsubscribing from all alerts
        invitation_code: The invitation code used to register
    """
    table = get_dynamodb_table()

    table.put_item(
        Item={
            "pk": f"PHONE#{phone_number}",
            "sk": "META",
            "phone_number": phone_number,
            "master_unsubscribe_token": master_unsubscribe_token,
            "invitation_code_used": invitation_code,
            "registered_at": datetime.utcnow().isoformat() + "Z",
        }
    )


def is_phone_registered(phone_number: str) -> bool:
    """Check if a phone number is already registered."""
    return get_phone_record(phone_number) is not None


# =============================================================================
# Invitation Code Operations
# =============================================================================


def get_invitation_code(code: str) -> dict[str, Any] | None:
    """
    Get an invitation code record.

    Returns:
        Invitation code record or None if not found
    """
    table = get_dynamodb_table()

    response = table.get_item(Key={"pk": f"INVITE#{code}", "sk": "CODE"})

    return response.get("Item")


def validate_invitation_code(code: str) -> bool:
    """
    Check if an invitation code is valid and has remaining uses.

    Returns:
        True if valid and has uses remaining
    """
    record = get_invitation_code(code)

    if not record:
        return False

    # Check expiration
    expires_at = record.get("expires_at")
    if expires_at:
        if datetime.utcnow().isoformat() > expires_at:
            return False

    # Check usage limit
    max_uses = record.get("max_uses", 0)
    current_uses = record.get("current_uses", 0)

    if max_uses > 0 and current_uses >= max_uses:
        return False

    return True


def increment_invitation_code_usage(code: str) -> None:
    """Increment the usage count for an invitation code."""
    table = get_dynamodb_table()

    table.update_item(
        Key={"pk": f"INVITE#{code}", "sk": "CODE"},
        UpdateExpression="SET current_uses = if_not_exists(current_uses, :zero) + :one",
        ExpressionAttributeValues={":zero": 0, ":one": 1},
    )


def create_invitation_code(
    code: str,
    max_uses: int = 0,
    expires_at: str | None = None,
) -> None:
    """
    Create a new invitation code.

    Args:
        code: The invitation code string
        max_uses: Maximum number of uses (0 = unlimited)
        expires_at: Expiration timestamp (ISO format) or None for no expiration
    """
    table = get_dynamodb_table()

    item: dict[str, Any] = {
        "pk": f"INVITE#{code}",
        "sk": "CODE",
        "code": code,
        "max_uses": max_uses,
        "current_uses": 0,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    if expires_at:
        item["expires_at"] = expires_at

    table.put_item(Item=item)
