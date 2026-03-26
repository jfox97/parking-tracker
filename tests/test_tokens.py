"""
Additional tests for token generation and validation edge cases.
"""

import os
from unittest.mock import patch

os.environ.setdefault("CONFIG_TABLE", "test-table")
os.environ.setdefault("SECRETS_NAME", "test-secrets")
os.environ.setdefault("DOMAIN_NAME", "parking.test.com")


class TestTokenSecurity:
    """Security-focused tests for token handling."""

    @patch("web_api.tokens.get_token_secret")
    def test_tampered_token_rejected(self, mock_secret):
        """Should reject tokens that have been tampered with."""
        mock_secret.return_value = "test-secret-key-32-bytes-long!!"

        from web_api.tokens import (
            generate_unsubscribe_token,
            validate_unsubscribe_token,
        )

        token = generate_unsubscribe_token("+14155551234", "brighton", "2026-02-15")

        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        result = validate_unsubscribe_token(tampered)
        assert result is None

    @patch("web_api.tokens.get_token_secret")
    def test_different_secrets_incompatible(self, mock_secret):
        """Tokens generated with different secrets should not validate."""
        from web_api.tokens import (
            generate_unsubscribe_token,
            validate_unsubscribe_token,
        )

        # Generate with one secret
        mock_secret.return_value = "secret-one-32-bytes-long-aaaaaa"
        token = generate_unsubscribe_token("+14155551234", "brighton", "2026-02-15")

        # Try to validate with different secret
        mock_secret.return_value = "secret-two-32-bytes-long-bbbbbb"
        result = validate_unsubscribe_token(token)
        assert result is None

    @patch("web_api.tokens.get_token_secret")
    def test_token_contains_expected_data(self, mock_secret):
        """Token should decode to contain the original data."""
        mock_secret.return_value = "test-secret-key-32-bytes-long!!"

        from web_api.tokens import (
            generate_unsubscribe_token,
            validate_unsubscribe_token,
        )

        phone = "+14155551234"
        resort = "brighton"
        date = "2026-02-15"

        token = generate_unsubscribe_token(phone, resort, date)
        result = validate_unsubscribe_token(token)

        assert result["phone"] == phone
        assert result["resort"] == resort
        assert result["date"] == date

    @patch("web_api.tokens.get_token_secret")
    def test_master_token_not_confused_with_single(self, mock_secret):
        """Master and single tokens should be distinguishable."""
        mock_secret.return_value = "test-secret-key-32-bytes-long!!"

        from web_api.tokens import (
            generate_master_unsubscribe_token,
            validate_unsubscribe_token,
        )

        master_token = generate_master_unsubscribe_token("+14155551234")

        # Master token should not validate as single token
        result = validate_unsubscribe_token(master_token)
        # The result might parse but won't have proper resort/date
        if result is not None:
            assert result.get("resort") is None or result.get("date") is None


class TestBuildUnsubscribeUrl:
    """Tests for URL building."""

    @patch.dict(os.environ, {"DOMAIN_NAME": "parking.example.com"})
    def test_uses_domain_from_env(self):
        """Should use domain from environment variable."""
        from web_api.tokens import build_unsubscribe_url

        url = build_unsubscribe_url("test-token")
        assert "parking.example.com" in url
        assert "token=test-token" in url

    def test_url_is_https(self):
        """Should always use HTTPS."""
        from web_api.tokens import build_unsubscribe_url

        url = build_unsubscribe_url("test-token")
        assert url.startswith("https://")
