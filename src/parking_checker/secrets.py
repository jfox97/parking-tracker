"""
AWS Secrets Manager integration for retrieving application secrets.
"""

import json
import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import ClientError


@lru_cache(maxsize=1)
def _get_all_secrets() -> dict[str, Any]:
    """
    Retrieve all secrets from AWS Secrets Manager.

    This is the single source of truth for all application secrets.
    Individual getter functions should use this to extract what they need.

    Returns:
        Dict containing all secret key-value pairs

    Raises:
        RuntimeError: If unable to retrieve secrets
    """
    secret_name = os.environ.get("SECRETS_NAME", "parking-tracker/secrets")
    region_name = os.environ.get("AWS_REGION", "us-east-1")

    client = boto3.client("secretsmanager", region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except ClientError as e:
        raise RuntimeError(f"Failed to retrieve secrets: {e}")


def get_twilio_credentials() -> dict[str, str]:
    """
    Retrieve Twilio credentials from AWS Secrets Manager.

    Returns:
        Dict containing account_sid, auth_token, and from_number
    """
    secret = _get_all_secrets()
    return {
        "account_sid": secret["TWILIO_ACCOUNT_SID"],
        "auth_token": secret["TWILIO_AUTH_TOKEN"],
        "from_number": secret["TWILIO_FROM_NUMBER"],
    }


def get_token_secret() -> str:
    """
    Retrieve the TOKEN_SECRET for HMAC token generation.

    Returns:
        The token secret string

    Raises:
        RuntimeError: If TOKEN_SECRET is not configured
    """
    secret = _get_all_secrets()
    token_secret = secret.get("TOKEN_SECRET")
    if not token_secret:
        raise RuntimeError("TOKEN_SECRET not found in secrets")
    return token_secret


def get_fcm_credentials() -> dict[str, Any]:
    """
    Retrieve FCM credentials from AWS Secrets Manager.

    Returns:
        Dict containing project_id and service_account, or empty dict if not configured
    """
    secret = _get_all_secrets()

    fcm_project_id = secret.get("FCM_PROJECT_ID")
    fcm_service_account = secret.get("FCM_SERVICE_ACCOUNT_JSON")

    if not fcm_project_id or not fcm_service_account:
        return {}

    # Parse the service account JSON (it may be stored as a JSON string)
    if isinstance(fcm_service_account, str):
        fcm_service_account = json.loads(fcm_service_account)

    return {
        "project_id": fcm_project_id,
        "service_account": fcm_service_account,
    }
