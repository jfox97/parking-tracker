"""
AWS Secrets Manager integration for retrieving Twilio credentials.
"""

import json
import os
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError


@lru_cache(maxsize=1)
def get_twilio_credentials() -> dict[str, str]:
    """
    Retrieve Twilio credentials from AWS Secrets Manager.

    Returns:
        Dict containing account_sid, auth_token, and from_number

    Raises:
        RuntimeError: If unable to retrieve secrets
    """
    secret_name = os.environ.get("SECRETS_NAME", "parking-tracker/secrets")
    region_name = os.environ.get("AWS_REGION", "us-east-1")

    client = boto3.client("secretsmanager", region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])

        return {
            "account_sid": secret["TWILIO_ACCOUNT_SID"],
            "auth_token": secret["TWILIO_AUTH_TOKEN"],
            "from_number": secret["TWILIO_FROM_NUMBER"],
        }
    except ClientError as e:
        raise RuntimeError(f"Failed to retrieve Twilio credentials: {e}")
