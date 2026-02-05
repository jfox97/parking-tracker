"""
Tests for the parking checker Lambda handler.
"""

import json
from unittest.mock import patch


class TestLambdaHandler:
    """Tests for the main Lambda handler."""

    @patch("parking_checker.handler.get_tracked_resorts")
    def test_no_resorts_returns_success(self, mock_get_resorts):
        """Should return success when no resorts are tracked."""
        mock_get_resorts.return_value = []

        from parking_checker.handler import lambda_handler

        result = lambda_handler({}, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "No resorts to check" in body["message"]

    @patch("parking_checker.handler.update_parking_state")
    @patch("parking_checker.handler.check_parking_availability")
    @patch("parking_checker.handler.send_sms")
    @patch("parking_checker.handler.get_twilio_credentials")
    @patch("parking_checker.handler.get_tracked_resorts")
    def test_sends_sms_when_parking_becomes_available(
        self,
        mock_get_resorts,
        mock_get_creds,
        mock_send_sms,
        mock_check_parking,
        mock_update_state,
    ):
        """Should send SMS when parking becomes available."""
        mock_get_resorts.return_value = [
            {
                "pk": "DATE#2026-02-01",
                "sk": "RESORT#brighton",
                "resort_name": "brighton",
                "date": "2026-02-01",
                "phone_number": "+12065551234",
                "last_status": "unavailable",
            }
        ]
        mock_get_creds.return_value = {
            "account_sid": "test",
            "auth_token": "test",
            "from_number": "+10001112222",
        }
        mock_check_parking.return_value = {
            "available": True,
            "spots": 5,
            "checked_at": "2026-02-01T12:00:00Z",
        }

        from parking_checker.handler import lambda_handler

        result = lambda_handler({}, None)

        assert result["statusCode"] == 200
        mock_send_sms.assert_called_once()

        # Verify SMS content
        call_args = mock_send_sms.call_args
        assert "+12065551234" in call_args[0]
        assert "brighton" in call_args[0][2].lower()

    @patch("parking_checker.handler.update_parking_state")
    @patch("parking_checker.handler.check_parking_availability")
    @patch("parking_checker.handler.send_sms")
    @patch("parking_checker.handler.get_twilio_credentials")
    @patch("parking_checker.handler.get_tracked_resorts")
    def test_no_sms_when_already_available(
        self,
        mock_get_resorts,
        mock_get_creds,
        mock_send_sms,
        mock_check_parking,
        mock_update_state,
    ):
        """Should NOT send SMS when parking was already available."""
        mock_get_resorts.return_value = [
            {
                "pk": "DATE#2026-02-01",
                "sk": "RESORT#brighton",
                "resort_name": "brighton",
                "date": "2026-02-01",
                "phone_number": "+12065551234",
                "last_status": "available",  # Already available
            }
        ]
        mock_get_creds.return_value = {
            "account_sid": "test",
            "auth_token": "test",
            "from_number": "+10001112222",
        }
        mock_check_parking.return_value = {
            "available": True,
            "spots": 5,
            "checked_at": "2026-02-01T12:00:00Z",
        }

        from parking_checker.handler import lambda_handler

        result = lambda_handler({}, None)

        assert result["statusCode"] == 200
        mock_send_sms.assert_not_called()

    @patch("parking_checker.handler.get_tracked_resorts")
    def test_handles_exception(self, mock_get_resorts):
        """Should return 500 on exception."""
        mock_get_resorts.side_effect = Exception("Database error")

        from parking_checker.handler import lambda_handler

        result = lambda_handler({}, None)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "error" in body
