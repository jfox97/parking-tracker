# Parking Tracker

A serverless application that monitors ski resort parking availability and sends SMS and push notification alerts. Subscribe to a resort and date, and get notified when parking status changes.

**Live at:** [parking.foxjason.com](https://parking.foxjason.com)

## Supported Resorts

- Brighton
- Alta
- Solitude

Parking data is sourced from the Honk Mobile API. New resorts can be added by configuring their Honk GUID and facility ID in `src/parking_checker/scraper.py`.

## How It Works

1. Users visit the web interface or mobile app and enter an invitation code
2. They subscribe to parking alerts for a specific resort and date
3. A Lambda function runs every minute, scraping parking availability for all active subscriptions
4. When parking status changes, subscribers receive an SMS (via Twilio) or push notification (via Firebase Cloud Messaging)

## Architecture

- **AWS Lambda** (Python 3.12) — Scheduled parking checker + REST API
- **API Gateway + CloudFront** — Serves the API and static frontend
- **DynamoDB** — Stores subscriptions, phone registry, device registry, and invitation codes
- **S3** — Hosts the static web interface
- **Twilio** — Sends SMS alerts
- **Firebase Cloud Messaging** — Sends push notifications to the mobile app
- **AWS SAM** — Infrastructure as code

## Local Development

### Prerequisites

- Python 3.12+
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- [Docker](https://www.docker.com/) (for `sam local`)
- Node.js 18+ (for the mobile app)

### Setup

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src/parking_checker --cov=src/web_api
```

### Linting and Formatting

```bash
ruff check src/ tests/
ruff format src/ tests/
mypy src/
```

### Invoke Locally

```bash
sam build
sam local invoke ParkingCheckerFunction
```

### Mobile App

```bash
cd mobile
npm install
npx expo start
```

## Deploying Your Own Instance

### 1. Configure Secrets

Create a secret in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
    --name parking-tracker/secrets \
    --secret-string '{
        "TWILIO_ACCOUNT_SID": "...",
        "TWILIO_AUTH_TOKEN": "...",
        "TWILIO_FROM_NUMBER": "+1234567890",
        "TOKEN_SECRET": "your-32-byte-random-secret-here"
    }'
```

Optionally add Firebase credentials for push notifications:
- `FCM_PROJECT_ID`
- `FCM_SERVICE_ACCOUNT_JSON`

### 2. Configure Deployment

Create a `samconfig.toml` with your settings:

```toml
[default.deploy.parameters]
stack_name = "parking-tracker"
resolve_s3 = true
s3_prefix = "parking-tracker"
region = "us-east-1"
capabilities = "CAPABILITY_IAM"
parameter_overrides = "DomainName=your-domain.com HostedZoneId=YOUR_ZONE_ID"
```

### 3. Build and Deploy

```bash
sam build
sam deploy
```

The first deploy creates the CloudFront distribution (takes 15-20 minutes). Then deploy the frontend:

```bash
aws s3 sync frontend/ s3://$(aws cloudformation describe-stacks \
    --stack-name parking-tracker \
    --query 'Stacks[0].Outputs[?OutputKey==`WebBucketName`].OutputValue' \
    --output text)/ --delete
```

### 4. Create Invitation Codes

```bash
aws dynamodb put-item \
    --table-name parking-tracker-config \
    --item '{
        "pk": {"S": "INVITE#MYCODE"},
        "sk": {"S": "CODE"},
        "code": {"S": "MYCODE"},
        "max_uses": {"N": "10"},
        "current_uses": {"N": "0"}
    }'
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/resorts | List available resorts |
| POST | /api/verify-code | Validate invitation code |
| POST | /api/subscribe | Subscribe to alerts |
| GET | /api/subscriptions | Get subscriptions |
| POST | /api/unsubscribe | Unsubscribe from an alert |
| POST | /api/unsubscribe-all | Unsubscribe from all alerts |
| POST | /api/devices/register | Register device for push notifications |
| POST | /api/devices/refresh-token | Update FCM token |
| DELETE | /api/devices/{device_id} | Unregister a device |
| GET | /api/devices/{device_id}/subscriptions | Get device subscriptions |
| POST | /api/devices/{device_id}/subscribe | Subscribe device to alerts |
| POST | /api/devices/unsubscribe | Unsubscribe device from an alert |

## License

MIT
