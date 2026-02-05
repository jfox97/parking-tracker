"""
Resort parking availability scraper using Honk Mobile GraphQL API.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import requests

logger = logging.getLogger(__name__)

# Registry of supported resorts and their scraping functions
RESORT_SCRAPERS: dict[str, Callable[[str], dict[str, Any]]] = {}


@dataclass
class HonkResortConfig:
    """Configuration for a Honk Mobile-powered resort."""

    honk_guid: str  # GUID in the query parameter
    facility_id: str  # ID used in the GraphQL variables
    timezone_offset: str  # e.g., "-07:00" for Mountain Time


# Honk Mobile resort configurations
# Add new resorts here as they are discovered
HONK_RESORTS: dict[str, HonkResortConfig] = {
    "brighton": HonkResortConfig(
        honk_guid="utzat5o9dbsfzynnkzwv0d",
        facility_id="rrIb",
        timezone_offset="-07:00",
    ),
    # Add more resorts as needed:
    # "solitude": HonkResortConfig(
    #     honk_guid="...",
    #     facility_id="...",
    #     timezone_offset="-07:00",
    # ),
}

GRAPHQL_QUERY = """
query PublicParkingAvailability($id: ID!, $cartStartTime: String!, $startDay: Int!, $endDay: Int!, $year: Int!) {
  publicParkingAvailability(
    id: $id
    cartStartTime: $cartStartTime
    startDay: $startDay
    endDay: $endDay
    year: $year
  )
}
"""


def register_resort(name: str):
    """Decorator to register a resort scraper function."""

    def decorator(func):
        RESORT_SCRAPERS[name.lower()] = func
        return func

    return decorator


def check_parking_availability(resort_name: str, target_date: str) -> dict[str, Any]:
    """
    Check parking availability for a specific resort and date.

    Args:
        resort_name: Name of the resort
        target_date: Date to check (YYYY-MM-DD format)

    Returns:
        Dict with availability info:
        {
            "available": bool,
            "spots": int or None,
            "checked_at": ISO timestamp,
            "details": str or None
        }
    """
    scraper = RESORT_SCRAPERS.get(resort_name.lower())

    if not scraper:
        raise ValueError(f"No scraper registered for resort: {resort_name}")

    result = scraper(target_date)
    result["checked_at"] = datetime.now(timezone.utc).isoformat()

    return result


def _query_honk_availability(config: HonkResortConfig, target_date: str) -> dict[str, Any]:
    """
    Query the Honk Mobile GraphQL API for parking availability.

    Args:
        config: Resort configuration
        target_date: Date to check (YYYY-MM-DD format)

    Returns:
        Raw API response data
    """
    # Parse target date
    date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    year = date_obj.year
    day_of_year = date_obj.timetuple().tm_yday

    # Build cart start time (6 AM on the target date in resort's timezone)
    cart_start_time = f"{target_date}T06:00:00{config.timezone_offset}"

    url = f"https://platform.honkmobile.com/graphql?honkGUID={config.honk_guid}"

    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
    }

    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {
            "id": config.facility_id,
            "cartStartTime": cart_start_time,
            "startDay": day_of_year,
            "endDay": day_of_year,
            "year": year,
        },
    }

    response = requests.post(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()

    result: dict[str, Any] = response.json()
    return result


def _parse_honk_response(
    data: dict[str, Any], target_date: str, timezone_offset: str = "-07:00"
) -> dict[str, Any]:
    """
    Parse the Honk Mobile API response to extract availability.

    The response format contains availability keyed by ISO datetime:
    {
        "data": {
            "publicParkingAvailability": {
                "2026-02-20T00:00:00-07:00": {
                    "status": {"sold_out": false, "unavailable": false, ...},
                    "V342VTX": {"available": true, "description": "...", "price": "5.0"},
                    ...
                }
            }
        }
    }

    Args:
        data: Raw API response
        target_date: Date being checked (YYYY-MM-DD format)
        timezone_offset: Timezone offset for the date key (e.g., "-07:00")

    Returns:
        Parsed availability dict
    """
    try:
        availability_data = data.get("data", {}).get("publicParkingAvailability")

        if availability_data is None:
            logger.warning("No availability data in response")
            return {"available": False, "spots": None, "details": "No data returned"}

        # The API returns a JSON string that needs to be parsed
        if isinstance(availability_data, str):
            import json

            availability_data = json.loads(availability_data)

        # Build the date key in the format used by the API: "YYYY-MM-DDT00:00:00-07:00"
        date_key = f"{target_date}T00:00:00{timezone_offset}"

        day_data = availability_data.get(date_key)

        if not day_data:
            logger.warning(f"No data for date key {date_key}")
            return {"available": False, "spots": None, "details": "Date not found in response"}

        # Extract the status object
        status = day_data.get("status", {})
        sold_out = status.get("sold_out", False)
        unavailable = status.get("unavailable", False)

        # Parking is available if it's not sold out and not unavailable
        is_available = not sold_out and not unavailable

        # Build details about available options
        details = None
        if is_available:
            options = []
            for key, value in day_data.items():
                if key != "status" and isinstance(value, dict) and value.get("available"):
                    desc = value.get("description", key)
                    price = value.get("price")
                    if price:
                        options.append(f"{desc} (${price})")
                    else:
                        options.append(desc)
            if options:
                details = "; ".join(options)
        else:
            if sold_out:
                details = "Sold out"
            elif unavailable:
                details = "Unavailable"

        return {
            "available": is_available,
            "spots": None,  # API doesn't provide spot counts
            "details": details,
        }

    except Exception as e:
        logger.error(f"Error parsing Honk response: {e}")
        return {"available": False, "spots": None, "details": f"Parse error: {e}"}


# ============================================================
# Resort-specific scrapers
# ============================================================


@register_resort("brighton")
def check_brighton(target_date: str) -> dict[str, Any]:
    """
    Check parking availability at Brighton Resort (Utah).

    Args:
        target_date: Date to check (YYYY-MM-DD format)

    Returns:
        Availability dict with available, spots, and details
    """
    config = HONK_RESORTS["brighton"]

    try:
        response = _query_honk_availability(config, target_date)
        return _parse_honk_response(response, target_date, config.timezone_offset)
    except requests.RequestException as e:
        logger.error(f"Failed to query Brighton parking: {e}")
        return {"available": False, "spots": None, "details": f"Request failed: {e}"}


# Generic factory for adding more Honk-based resorts
def _create_honk_scraper(resort_key: str):
    """Create a scraper function for a Honk Mobile resort."""

    def scraper(target_date: str) -> dict[str, Any]:
        config = HONK_RESORTS[resort_key]
        try:
            response = _query_honk_availability(config, target_date)
            return _parse_honk_response(response, target_date, config.timezone_offset)
        except requests.RequestException as e:
            logger.error(f"Failed to query {resort_key} parking: {e}")
            return {"available": False, "spots": None, "details": f"Request failed: {e}"}

    return scraper


# Auto-register all Honk resorts that aren't already registered
for _resort_name in HONK_RESORTS:
    if _resort_name not in RESORT_SCRAPERS:
        RESORT_SCRAPERS[_resort_name] = _create_honk_scraper(_resort_name)
