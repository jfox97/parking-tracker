"""
Request routing for the web API.

Maps HTTP methods and paths to handler functions.
"""

import json
import logging
import re
from typing import Any, Callable

from .devices import (
    get_device_info,
    get_device_subscriptions_list,
    refresh_device_token,
    register_device_with_code,
    subscribe_device_to_alerts,
    unregister_device,
    unsubscribe_device_with_token,
)
from .invitation import verify_invitation_code
from .subscribe import (
    get_available_resorts,
    get_subscriptions_for_phone,
    send_unsubscribe_link,
    subscribe_to_alerts,
    unsubscribe_all_with_token,
    unsubscribe_with_token,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Type alias for route handlers
RouteHandler = Callable[[dict[str, Any]], dict[str, Any]]


def make_response(
    status_code: int,
    body: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a standardized API response."""
    import os

    domain = os.environ.get("DOMAIN_NAME", "parking.foxjason.com")

    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": f"https://{domain}",
        "Access-Control-Allow-Headers": "Content-Type,X-Unsubscribe-Token",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    }

    if headers:
        default_headers.update(headers)

    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(body),
    }


def parse_body(event: dict[str, Any]) -> dict[str, Any]:
    """Parse the request body from an API Gateway event."""
    body = event.get("body", "{}")
    if body is None:
        return {}

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {}


def get_query_params(event: dict[str, Any]) -> dict[str, str]:
    """Get query string parameters from an API Gateway event."""
    return event.get("queryStringParameters") or {}


# =============================================================================
# Route Handlers
# =============================================================================


def handle_get_resorts(event: dict[str, Any]) -> dict[str, Any]:
    """GET /api/resorts - List available resorts."""
    resorts = get_available_resorts()
    return make_response(200, {"resorts": resorts})


def handle_verify_code(event: dict[str, Any]) -> dict[str, Any]:
    """POST /api/verify-code - Validate an invitation code."""
    body = parse_body(event)
    code = body.get("code", "").strip()

    if not code:
        return make_response(400, {"valid": False, "error": "Code is required"})

    is_valid = verify_invitation_code(code)

    if is_valid:
        return make_response(200, {"valid": True})
    else:
        return make_response(200, {"valid": False, "error": "Invalid or expired code"})


def handle_subscribe(event: dict[str, Any]) -> dict[str, Any]:
    """POST /api/subscribe - Subscribe to parking alerts."""
    body = parse_body(event)

    phone = body.get("phone_number", "").strip()
    resort = body.get("resort", "").strip()
    date = body.get("date", "").strip()
    invitation_code = body.get("invitation_code", "").strip() or None

    if not phone or not resort or not date:
        return make_response(
            400,
            {"success": False, "error": "phone_number, resort, and date are required"},
        )

    success, message, unsubscribe_url = subscribe_to_alerts(
        phone, resort, date, invitation_code
    )

    if success:
        return make_response(
            201,
            {
                "success": True,
                "message": message,
                "unsubscribe_url": unsubscribe_url,
            },
        )
    else:
        return make_response(400, {"success": False, "error": message})


def handle_get_subscriptions(event: dict[str, Any]) -> dict[str, Any]:
    """GET /api/subscriptions - Get subscriptions for a phone (requires token)."""
    params = get_query_params(event)
    token = params.get("token", "")

    if not token:
        # Also check header
        headers = event.get("headers") or {}
        token = headers.get("X-Unsubscribe-Token", "")

    if not token:
        return make_response(400, {"success": False, "error": "Token is required"})

    success, message, subscriptions = get_subscriptions_for_phone(token)

    if success:
        return make_response(
            200,
            {
                "success": True,
                "message": message,
                "subscriptions": subscriptions,
            },
        )
    else:
        return make_response(400, {"success": False, "error": message})


def handle_unsubscribe(event: dict[str, Any]) -> dict[str, Any]:
    """POST /api/unsubscribe - Unsubscribe from a specific alert."""
    body = parse_body(event)
    token = body.get("token", "").strip()

    if not token:
        return make_response(400, {"success": False, "error": "Token is required"})

    success, message = unsubscribe_with_token(token)

    if success:
        return make_response(200, {"success": True, "message": message})
    else:
        return make_response(400, {"success": False, "error": message})


def handle_unsubscribe_all(event: dict[str, Any]) -> dict[str, Any]:
    """POST /api/unsubscribe-all - Unsubscribe from all alerts."""
    body = parse_body(event)
    token = body.get("token", "").strip()

    if not token:
        return make_response(400, {"success": False, "error": "Token is required"})

    success, message, count = unsubscribe_all_with_token(token)

    if success:
        return make_response(
            200,
            {
                "success": True,
                "message": message,
                "removed_count": count,
            },
        )
    else:
        return make_response(400, {"success": False, "error": message})


def handle_send_unsubscribe_link(event: dict[str, Any]) -> dict[str, Any]:
    """POST /api/send-unsubscribe-link - Send unsubscribe link via SMS."""
    body = parse_body(event)
    phone = body.get("phone_number", "").strip()

    if not phone:
        return make_response(400, {"success": False, "error": "Phone number is required"})

    success, message = send_unsubscribe_link(phone)

    if success:
        return make_response(200, {"success": True, "message": message})
    else:
        return make_response(400, {"success": False, "error": message})


def handle_options(event: dict[str, Any]) -> dict[str, Any]:
    """Handle CORS preflight requests."""
    return make_response(200, {})


# =============================================================================
# Device Route Handlers
# =============================================================================


def handle_register_device(event: dict[str, Any]) -> dict[str, Any]:
    """POST /api/devices/register - Register a new device for push notifications."""
    body = parse_body(event)

    device_id = body.get("device_id", "").strip()
    fcm_token = body.get("fcm_token", "").strip()
    platform = body.get("platform", "").strip()
    invitation_code = body.get("invitation_code", "").strip()

    if not device_id or not fcm_token or not platform:
        return make_response(
            400,
            {"success": False, "error": "device_id, fcm_token, and platform are required"},
        )

    success, message, auth_token = register_device_with_code(
        device_id, fcm_token, platform, invitation_code
    )

    if success:
        return make_response(
            201,
            {
                "success": True,
                "message": message,
                "auth_token": auth_token,
                "device_id": device_id,
            },
        )
    else:
        return make_response(400, {"success": False, "error": message})


def handle_refresh_device_token(event: dict[str, Any]) -> dict[str, Any]:
    """POST /api/devices/refresh-token - Update FCM token for a device."""
    body = parse_body(event)

    device_id = body.get("device_id", "").strip()
    fcm_token = body.get("fcm_token", "").strip()
    auth_token = _get_auth_token(event)

    if not device_id or not fcm_token:
        return make_response(
            400,
            {"success": False, "error": "device_id and fcm_token are required"},
        )

    if not auth_token:
        return make_response(401, {"success": False, "error": "Authorization required"})

    success, message = refresh_device_token(device_id, fcm_token, auth_token)

    if success:
        return make_response(200, {"success": True, "message": message})
    else:
        status = 401 if "auth" in message.lower() else 400
        return make_response(status, {"success": False, "error": message})


def handle_unregister_device(event: dict[str, Any]) -> dict[str, Any]:
    """DELETE /api/devices/{device_id} - Unregister a device."""
    device_id = _get_path_param(event, "device_id")
    auth_token = _get_auth_token(event)

    if not device_id:
        return make_response(400, {"success": False, "error": "device_id is required"})

    if not auth_token:
        return make_response(401, {"success": False, "error": "Authorization required"})

    success, message = unregister_device(device_id, auth_token)

    if success:
        return make_response(200, {"success": True, "message": message})
    else:
        status = 401 if "auth" in message.lower() else 400
        return make_response(status, {"success": False, "error": message})


def handle_get_device_subscriptions(event: dict[str, Any]) -> dict[str, Any]:
    """GET /api/devices/{device_id}/subscriptions - Get subscriptions for a device."""
    device_id = _get_path_param(event, "device_id")
    auth_token = _get_auth_token(event)

    if not device_id:
        return make_response(400, {"success": False, "error": "device_id is required"})

    if not auth_token:
        return make_response(401, {"success": False, "error": "Authorization required"})

    success, message, subscriptions = get_device_subscriptions_list(device_id, auth_token)

    if success:
        return make_response(
            200,
            {
                "success": True,
                "message": message,
                "subscriptions": subscriptions,
            },
        )
    else:
        status = 401 if "auth" in message.lower() else 400
        return make_response(status, {"success": False, "error": message})


def handle_device_subscribe(event: dict[str, Any]) -> dict[str, Any]:
    """POST /api/devices/{device_id}/subscribe - Subscribe a device to alerts."""
    device_id = _get_path_param(event, "device_id")
    auth_token = _get_auth_token(event)
    body = parse_body(event)

    resort = body.get("resort", "").strip()
    date = body.get("date", "").strip()
    notification_type = body.get("notification_type", "push").strip()
    phone_number = body.get("phone_number", "").strip() or None

    if not device_id:
        return make_response(400, {"success": False, "error": "device_id is required"})

    if not auth_token:
        return make_response(401, {"success": False, "error": "Authorization required"})

    if not resort or not date:
        return make_response(
            400,
            {"success": False, "error": "resort and date are required"},
        )

    success, message, unsubscribe_token = subscribe_device_to_alerts(
        device_id, resort, date, auth_token, notification_type, phone_number
    )

    if success:
        return make_response(
            201,
            {
                "success": True,
                "message": message,
                "unsubscribe_token": unsubscribe_token,
            },
        )
    else:
        status = 401 if "auth" in message.lower() else 400
        return make_response(status, {"success": False, "error": message})


def handle_device_unsubscribe(event: dict[str, Any]) -> dict[str, Any]:
    """POST /api/devices/unsubscribe - Unsubscribe a device from a specific alert."""
    body = parse_body(event)
    token = body.get("token", "").strip()

    if not token:
        return make_response(400, {"success": False, "error": "Token is required"})

    success, message = unsubscribe_device_with_token(token)

    if success:
        return make_response(200, {"success": True, "message": message})
    else:
        return make_response(400, {"success": False, "error": message})


def _get_auth_token(event: dict[str, Any]) -> str | None:
    """Extract auth token from Authorization header or query params."""
    # Check Authorization header first
    headers = event.get("headers") or {}
    auth_header = headers.get("Authorization") or headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Fall back to query parameter
    params = get_query_params(event)
    return params.get("auth_token") or None


def _get_path_param(event: dict[str, Any], param_name: str) -> str | None:
    """Extract a path parameter from the event."""
    path_params = event.get("pathParameters") or {}
    return path_params.get(param_name)


# =============================================================================
# Router
# =============================================================================

# Route definitions: (method, path_pattern, handler)
ROUTES: list[tuple[str, str, RouteHandler]] = [
    ("GET", r"^/api/resorts$", handle_get_resorts),
    ("POST", r"^/api/verify-code$", handle_verify_code),
    ("POST", r"^/api/subscribe$", handle_subscribe),
    ("GET", r"^/api/subscriptions$", handle_get_subscriptions),
    ("POST", r"^/api/unsubscribe$", handle_unsubscribe),
    ("POST", r"^/api/unsubscribe-all$", handle_unsubscribe_all),
    ("POST", r"^/api/send-unsubscribe-link$", handle_send_unsubscribe_link),
    # Device management routes
    ("POST", r"^/api/devices/register$", handle_register_device),
    ("POST", r"^/api/devices/refresh-token$", handle_refresh_device_token),
    ("DELETE", r"^/api/devices/(?P<device_id>[^/]+)$", handle_unregister_device),
    ("GET", r"^/api/devices/(?P<device_id>[^/]+)/subscriptions$", handle_get_device_subscriptions),
    ("POST", r"^/api/devices/(?P<device_id>[^/]+)/subscribe$", handle_device_subscribe),
    ("POST", r"^/api/devices/unsubscribe$", handle_device_unsubscribe),
    ("OPTIONS", r"^/api/.*$", handle_options),
]


def route_request(event: dict[str, Any]) -> dict[str, Any]:
    """
    Route an incoming API Gateway request to the appropriate handler.

    Args:
        event: API Gateway event

    Returns:
        API Gateway response
    """
    method = event.get("httpMethod", "").upper()
    path = event.get("path", "")

    logger.info(f"Routing request: {method} {path}")

    for route_method, route_pattern, handler in ROUTES:
        if method == route_method:
            match = re.match(route_pattern, path)
            if match:
                # Extract path parameters from regex groups and merge with event
                path_params = match.groupdict()
                if path_params:
                    existing_params = event.get("pathParameters") or {}
                    event["pathParameters"] = {**existing_params, **path_params}
                try:
                    return handler(event)
                except Exception as e:
                    logger.error(f"Error handling {method} {path}: {e}", exc_info=True)
                    return make_response(
                        500,
                        {"success": False, "error": "Internal server error"},
                    )

    return make_response(404, {"success": False, "error": "Not found"})
