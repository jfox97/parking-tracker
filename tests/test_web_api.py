"""
Tests for the web API Lambda handler.
"""

import json
import os
from unittest.mock import patch

# Set environment variables before imports
os.environ.setdefault("CONFIG_TABLE", "test-table")
os.environ.setdefault("SECRETS_NAME", "test-secrets")
os.environ.setdefault("DOMAIN_NAME", "parking.test.com")


class TestValidators:
    """Tests for input validators."""

    def test_validate_phone_number_valid_formats(self):
        """Should accept various valid phone number formats."""
        from web_api.validators import validate_phone_number

        # Standard US format with country code
        assert validate_phone_number("+14155551234") == "+14155551234"

        # US format without plus
        assert validate_phone_number("14155551234") == "+14155551234"

        # 10-digit US number
        assert validate_phone_number("4155551234") == "+14155551234"

        # With formatting
        assert validate_phone_number("(415) 555-1234") == "+14155551234"
        assert validate_phone_number("415-555-1234") == "+14155551234"
        assert validate_phone_number("415.555.1234") == "+14155551234"

    def test_validate_phone_number_invalid(self):
        """Should reject invalid phone numbers."""
        from web_api.validators import validate_phone_number

        assert validate_phone_number("") is None
        assert validate_phone_number("123") is None
        assert validate_phone_number("not-a-number") is None

    def test_validate_date_valid(self):
        """Should accept valid future dates."""
        from datetime import datetime, timedelta

        from web_api.validators import validate_date

        # Tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert validate_date(tomorrow) == tomorrow

        # Next week
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        assert validate_date(next_week) == next_week

    def test_validate_date_invalid(self):
        """Should reject invalid or past dates."""
        from datetime import datetime, timedelta

        from web_api.validators import validate_date

        assert validate_date("") is None
        assert validate_date("not-a-date") is None
        assert validate_date("2020-01-01") is None  # Past date

        # Yesterday
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        assert validate_date(yesterday) is None

    def test_validate_resort_valid(self):
        """Should accept valid resort names."""
        from web_api.validators import validate_resort

        available = ["brighton", "snowbird", "alta"]
        assert validate_resort("brighton", available) == "brighton"
        assert validate_resort("BRIGHTON", available) == "brighton"
        assert validate_resort(" Brighton ", available) == "brighton"

    def test_validate_resort_invalid(self):
        """Should reject invalid resort names."""
        from web_api.validators import validate_resort

        available = ["brighton", "snowbird"]
        assert validate_resort("unknown-resort", available) is None
        assert validate_resort("", available) is None


class TestTokens:
    """Tests for token generation and validation."""

    @patch("web_api.tokens.get_token_secret")
    def test_generate_and_validate_unsubscribe_token(self, mock_secret):
        """Should generate tokens that can be validated."""
        mock_secret.return_value = "test-secret-key-32-bytes-long!!"

        from web_api.tokens import (
            generate_unsubscribe_token,
            validate_unsubscribe_token,
        )

        token = generate_unsubscribe_token("+14155551234", "brighton", "2026-02-15")
        assert token is not None

        result = validate_unsubscribe_token(token)
        assert result is not None
        assert result["phone"] == "+14155551234"
        assert result["resort"] == "brighton"
        assert result["date"] == "2026-02-15"

    @patch("web_api.tokens.get_token_secret")
    def test_validate_invalid_token(self, mock_secret):
        """Should reject invalid tokens."""
        mock_secret.return_value = "test-secret-key-32-bytes-long!!"

        from web_api.tokens import validate_unsubscribe_token

        assert validate_unsubscribe_token("invalid-token") is None
        assert validate_unsubscribe_token("") is None

    @patch("web_api.tokens.get_token_secret")
    def test_generate_and_validate_master_token(self, mock_secret):
        """Should generate master tokens that can be validated."""
        mock_secret.return_value = "test-secret-key-32-bytes-long!!"

        from web_api.tokens import (
            generate_master_unsubscribe_token,
            validate_master_unsubscribe_token,
        )

        token = generate_master_unsubscribe_token("+14155551234")
        assert token is not None

        phone = validate_master_unsubscribe_token(token)
        assert phone == "+14155551234"

    @patch("web_api.tokens.get_token_secret")
    def test_unsubscribe_token_cannot_be_used_as_master(self, mock_secret):
        """Single unsubscribe token should not work as master token."""
        mock_secret.return_value = "test-secret-key-32-bytes-long!!"

        from web_api.tokens import (
            generate_unsubscribe_token,
            validate_master_unsubscribe_token,
        )

        token = generate_unsubscribe_token("+14155551234", "brighton", "2026-02-15")
        result = validate_master_unsubscribe_token(token)
        assert result is None


class TestRoutes:
    """Tests for API route handlers."""

    def test_handle_get_resorts(self):
        """Should return list of available resorts."""
        from web_api.routes import handle_get_resorts

        result = handle_get_resorts({})

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "resorts" in body
        assert isinstance(body["resorts"], list)

    @patch("web_api.routes.verify_invitation_code")
    def test_handle_verify_code_valid(self, mock_verify):
        """Should return valid=true for valid codes."""
        mock_verify.return_value = True

        from web_api.routes import handle_verify_code

        event = {"body": json.dumps({"code": "TEST123"})}
        result = handle_verify_code(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["valid"] is True

    @patch("web_api.routes.verify_invitation_code")
    def test_handle_verify_code_invalid(self, mock_verify):
        """Should return valid=false for invalid codes."""
        mock_verify.return_value = False

        from web_api.routes import handle_verify_code

        event = {"body": json.dumps({"code": "BADCODE"})}
        result = handle_verify_code(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["valid"] is False

    def test_handle_verify_code_missing(self):
        """Should return error for missing code."""
        from web_api.routes import handle_verify_code

        event = {"body": json.dumps({})}
        result = handle_verify_code(event)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["valid"] is False

    @patch("web_api.routes.subscribe_to_alerts")
    def test_handle_subscribe_success(self, mock_subscribe):
        """Should handle successful subscription."""
        mock_subscribe.return_value = (
            True,
            "Subscribed successfully",
            "https://parking.test.com/unsubscribe?token=abc123",
        )

        from web_api.routes import handle_subscribe

        event = {
            "body": json.dumps({
                "phone_number": "+14155551234",
                "resort": "brighton",
                "date": "2026-02-15",
            })
        }
        result = handle_subscribe(event)

        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert body["success"] is True
        assert "unsubscribe_url" in body

    @patch("web_api.routes.subscribe_to_alerts")
    def test_handle_subscribe_missing_fields(self, mock_subscribe):
        """Should return error for missing required fields."""
        from web_api.routes import handle_subscribe

        event = {"body": json.dumps({"phone_number": "+14155551234"})}
        result = handle_subscribe(event)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["success"] is False
        mock_subscribe.assert_not_called()

    @patch("web_api.routes.unsubscribe_with_token")
    def test_handle_unsubscribe_success(self, mock_unsubscribe):
        """Should handle successful unsubscribe."""
        mock_unsubscribe.return_value = (True, "Unsubscribed from brighton on 2026-02-15")

        from web_api.routes import handle_unsubscribe

        event = {"body": json.dumps({"token": "valid-token"})}
        result = handle_unsubscribe(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["success"] is True

    @patch("web_api.routes.unsubscribe_all_with_token")
    def test_handle_unsubscribe_all_success(self, mock_unsubscribe):
        """Should handle successful unsubscribe all."""
        mock_unsubscribe.return_value = (True, "Unsubscribed from all 3 alert(s)", 3)

        from web_api.routes import handle_unsubscribe_all

        event = {"body": json.dumps({"token": "master-token"})}
        result = handle_unsubscribe_all(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["success"] is True
        assert body["removed_count"] == 3

    @patch("web_api.routes.send_unsubscribe_link")
    def test_handle_send_unsubscribe_link_success(self, mock_send):
        """Should handle successful send unsubscribe link request."""
        mock_send.return_value = (True, "Unsubscribe link sent!")

        from web_api.routes import handle_send_unsubscribe_link

        event = {"body": json.dumps({"phone_number": "+14155551234"})}
        result = handle_send_unsubscribe_link(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["success"] is True

    def test_handle_send_unsubscribe_link_missing_phone(self):
        """Should return error for missing phone number."""
        from web_api.routes import handle_send_unsubscribe_link

        event = {"body": json.dumps({})}
        result = handle_send_unsubscribe_link(event)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["success"] is False


class TestWebApiHandler:
    """Tests for the main web API Lambda handler."""

    def test_routes_to_get_resorts(self):
        """Should route GET /api/resorts correctly."""
        from web_api.handler import lambda_handler

        event = {"httpMethod": "GET", "path": "/api/resorts"}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "resorts" in body

    def test_returns_404_for_unknown_route(self):
        """Should return 404 for unknown routes."""
        from web_api.handler import lambda_handler

        event = {"httpMethod": "GET", "path": "/api/unknown"}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 404

    def test_handles_options_for_cors(self):
        """Should handle OPTIONS requests for CORS preflight."""
        from web_api.handler import lambda_handler

        event = {"httpMethod": "OPTIONS", "path": "/api/subscribe"}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in result["headers"]
