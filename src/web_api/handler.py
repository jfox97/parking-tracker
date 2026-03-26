"""
Lambda handler for the web API.

Handles API Gateway requests for subscription management.
"""

import logging
from typing import Any

from .routes import route_request

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main Lambda handler for web API requests.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    logger.info(f"Received event: {event.get('httpMethod')} {event.get('path')}")

    return route_request(event)
