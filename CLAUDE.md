# Parking Tracker

Serverless AWS application that monitors ski resort parking availability and sends SMS alerts via Twilio.

## Architecture

- **AWS Lambda** (Python 3.12): Runs every minute to check parking availability
- **Amazon DynamoDB**: Stores resort tracking configurations and state
- **AWS Secrets Manager**: Stores Twilio credentials securely
- **Amazon EventBridge**: Schedules the Lambda function
- **Twilio**: Sends SMS notifications

## Project Structure

```
parking-tracker/
├── src/
│   └── parking_checker/       # Lambda function code
│       ├── handler.py         # Main Lambda entry point
│       ├── scraper.py         # Resort-specific scrapers
│       ├── notifier.py        # Twilio SMS integration
│       ├── config.py          # DynamoDB operations
│       └── secrets.py         # Secrets Manager integration
├── tests/                     # Unit tests
├── template.yaml              # AWS SAM template
├── samconfig.toml             # SAM deployment config
└── requirements-dev.txt       # Development dependencies
```

## Development Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/parking_checker

# Lint code
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Type check
mypy src/

# Build the Lambda package
sam build --profile personal

# Deploy to AWS
sam deploy --profile personal --no-confirm-changeset

# Deploy with guided prompts (first time)
sam deploy --guided --profile personal --no-confirm-changeset

# Invoke function locally
sam local invoke ParkingCheckerFunction

# View CloudWatch logs
sam logs -n ParkingCheckerFunction --stack-name parking-tracker --tail
```

## Secrets Management

Twilio credentials are stored in AWS Secrets Manager under the key `parking-tracker/secrets`.

Required secret keys:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`

Create the secret:
```bash
aws secretsmanager create-secret \
    --name parking-tracker/secrets \
    --secret-string '{"TWILIO_ACCOUNT_SID":"xxx","TWILIO_AUTH_TOKEN":"xxx","TWILIO_FROM_NUMBER":"+1234567890"}'
```

## DynamoDB Schema

**Table**: `{stack-name}-config`

| pk | sk | Attributes |
|----|----|------------|
| DATE#{YYYY-MM-DD} | RESORT#{name} | resort_name, date, phone_number, last_status |

## Adding Resort Scrapers

Add new scrapers in `src/parking_checker/scraper.py` using the `@register_resort` decorator:

```python
@register_resort("resort-name")
def check_resort_name(target_date: str) -> dict[str, Any]:
    # Implementation
    return {"available": bool, "spots": int|None, "details": str|None}
```

## Environment Variables

Set by SAM template:
- `SECRETS_NAME`: Secrets Manager secret name
- `CONFIG_TABLE`: DynamoDB table name
