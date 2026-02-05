"""
Tests for the parking availability scraper.
"""

from unittest.mock import Mock, patch

import pytest

from parking_checker.scraper import (
    HONK_RESORTS,
    HonkResortConfig,
    _parse_honk_response,
    _query_honk_availability,
    check_parking_availability,
)


class TestHonkResortConfig:
    """Tests for HonkResortConfig dataclass."""

    def test_brighton_config_exists(self):
        """Brighton resort should be configured."""
        assert "brighton" in HONK_RESORTS
        config = HONK_RESORTS["brighton"]
        assert config.honk_guid == "utzat5o9dbsfzynnkzwv0d"
        assert config.facility_id == "rrIb"
        assert config.timezone_offset == "-07:00"


class TestParseHonkResponse:
    """Tests for _parse_honk_response function."""

    def test_parse_available_spots(self):
        """Should correctly parse response with available parking."""
        response = {
            "data": {
                "publicParkingAvailability": {
                    "2026-02-01T00:00:00-07:00": {
                        "status": {
                            "sold_out": False,
                            "unavailable": False,
                            "reservation_not_needed": False
                        },
                        "V342VTX": {
                            "available": True,
                            "hashid": "V342VTX",
                            "description": "Carpool (4+)",
                            "price": "5.0"
                        }
                    }
                }
            }
        }
        result = _parse_honk_response(response, "2026-02-01")

        assert result["available"] is True
        assert result["spots"] is None  # API doesn't provide spot counts
        assert "Carpool (4+)" in result["details"]
        assert "$5.0" in result["details"]

    def test_parse_sold_out(self):
        """Should correctly parse response when parking is sold out."""
        response = {
            "data": {
                "publicParkingAvailability": {
                    "2026-02-01T00:00:00-07:00": {
                        "status": {
                            "sold_out": True,
                            "unavailable": False,
                            "reservation_not_needed": False
                        }
                    }
                }
            }
        }
        result = _parse_honk_response(response, "2026-02-01")

        assert result["available"] is False
        assert result["details"] == "Sold out"

    def test_parse_unavailable(self):
        """Should correctly parse response when parking is unavailable."""
        response = {
            "data": {
                "publicParkingAvailability": {
                    "2026-02-01T00:00:00-07:00": {
                        "status": {
                            "sold_out": False,
                            "unavailable": True,
                            "reservation_not_needed": False
                        }
                    }
                }
            }
        }
        result = _parse_honk_response(response, "2026-02-01")

        assert result["available"] is False
        assert result["details"] == "Unavailable"

    def test_parse_missing_date(self):
        """Should handle missing date in response."""
        response = {
            "data": {
                "publicParkingAvailability": {
                    "2026-01-15T00:00:00-07:00": {  # Different day
                        "status": {"sold_out": False, "unavailable": False}
                    }
                }
            }
        }
        result = _parse_honk_response(response, "2026-02-01")

        assert result["available"] is False
        assert "Date not found" in result["details"]

    def test_parse_null_response(self):
        """Should handle null availability data."""
        response = {"data": {"publicParkingAvailability": None}}
        result = _parse_honk_response(response, "2026-02-01")

        assert result["available"] is False
        assert "No data returned" in result["details"]

    def test_parse_empty_response(self):
        """Should handle empty response."""
        response = {"data": {}}
        result = _parse_honk_response(response, "2026-02-01")

        assert result["available"] is False


class TestCheckParkingAvailability:
    """Tests for check_parking_availability function."""

    def test_unknown_resort_raises_error(self):
        """Should raise ValueError for unknown resort."""
        with pytest.raises(ValueError, match="No scraper registered"):
            check_parking_availability("unknown-resort", "2026-02-01")

    @patch("parking_checker.scraper._query_honk_availability")
    def test_brighton_scraper_registered(self, mock_query):
        """Brighton scraper should be registered and callable."""
        mock_query.return_value = {
            "data": {
                "publicParkingAvailability": {
                    "2026-02-01T00:00:00-07:00": {
                        "status": {"sold_out": False, "unavailable": False}
                    }
                }
            }
        }

        result = check_parking_availability("brighton", "2026-02-01")

        assert "available" in result
        assert "checked_at" in result
        mock_query.assert_called_once()


class TestQueryHonkAvailability:
    """Tests for _query_honk_availability function."""

    @patch("parking_checker.scraper.requests.post")
    def test_builds_correct_request(self, mock_post):
        """Should build correct GraphQL request."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {}}
        mock_post.return_value = mock_response

        config = HonkResortConfig(
            honk_guid="test-guid",
            facility_id="test-id",
            timezone_offset="-07:00",
        )

        _query_honk_availability(config, "2026-02-01")

        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check URL (first positional argument)
        url = call_args[0][0]
        assert "honkGUID=test-guid" in url

        # Check payload (keyword argument)
        payload = call_args[1]["json"]
        assert payload["variables"]["id"] == "test-id"
        assert payload["variables"]["year"] == 2026
        assert payload["variables"]["startDay"] == 32  # Feb 1 is day 32
        assert payload["variables"]["endDay"] == 32

    @patch("parking_checker.scraper.requests.post")
    def test_handles_request_timeout(self, mock_post):
        """Should pass timeout to requests."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {}}
        mock_post.return_value = mock_response

        config = HONK_RESORTS["brighton"]
        _query_honk_availability(config, "2026-02-01")

        call_args = mock_post.call_args
        assert call_args[1]["timeout"] == 10
