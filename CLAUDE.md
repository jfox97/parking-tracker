# Parking Tracker

Serverless AWS application that monitors ski resort parking availability and sends SMS alerts via Twilio. Includes a public web interface for subscription management.

## Architecture

- **AWS Lambda** (Python 3.12): Scheduled checker + Web API
- **Amazon API Gateway**: REST API for web interface
- **Amazon DynamoDB**: Stores subscriptions, phone registry, and invitation codes
- **Amazon S3 + CloudFront**: Hosts static web interface
- **AWS Secrets Manager**: Stores Twilio credentials and token secret
- **Amazon EventBridge**: Schedules the parking checker Lambda
- **Amazon Route 53**: DNS for parking.foxjason.com
- **AWS Certificate Manager**: SSL certificate for HTTPS
- **Twilio**: Sends SMS notifications

## Project Structure

```
parking-tracker/
├── src/
│   ├── parking_checker/       # Scheduled checker Lambda
│   │   ├── handler.py         # Main Lambda entry point
│   │   ├── scraper.py         # Resort-specific scrapers
│   │   ├── notifier.py        # Twilio SMS integration
│   │   ├── push_notifier.py   # Firebase push notifications
│   │   ├── config.py          # DynamoDB operations
│   │   └── secrets.py         # Secrets Manager integration
│   ├── web_api/               # Web API Lambda
│   │   ├── handler.py         # API Lambda entry point
│   │   ├── routes.py          # Request routing
│   │   ├── subscribe.py       # Subscribe/unsubscribe logic
│   │   ├── devices.py         # Device registration logic
│   │   ├── tokens.py          # HMAC token generation
│   │   ├── invitation.py      # Invitation code management
│   │   └── validators.py      # Input validation
│   └── shared/                # Shared modules
│       ├── db.py              # DynamoDB operations
│       └── devices.py         # Device DynamoDB operations
├── frontend/                  # Static web interface
│   ├── index.html             # Subscription page
│   ├── unsubscribe.html       # Unsubscribe page
│   ├── css/styles.css
│   └── js/
│       ├── api.js             # API client
│       └── app.js             # Application logic
├── mobile/                    # React Native mobile app
│   ├── app/                   # Expo Router screens
│   │   ├── _layout.tsx        # Root layout
│   │   ├── index.tsx          # Subscription list
│   │   ├── subscribe.tsx      # New subscription form
│   │   ├── settings.tsx       # Settings page
│   │   └── onboarding/        # Onboarding flow
│   ├── services/              # App services
│   │   ├── api.ts             # API client
│   │   ├── auth.ts            # Device authentication
│   │   ├── notifications.ts   # Push notification setup
│   │   └── storage.ts         # AsyncStorage wrapper
│   └── app.json               # Expo configuration
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
pytest --cov=src/parking_checker --cov=src/web_api

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

# Deploy frontend to S3
aws s3 sync frontend/ s3://parking-tracker-web-{ACCOUNT_ID}/ --delete --profile personal

# Invalidate CloudFront cache after frontend deploy
aws cloudfront create-invalidation --distribution-id {DIST_ID} --paths "/*" --profile personal

# Invoke checker function locally
sam local invoke ParkingCheckerFunction

# View CloudWatch logs
sam logs -n ParkingCheckerFunction --stack-name parking-tracker --tail --profile personal
sam logs -n WebApiFunction --stack-name parking-tracker --tail -- profile personal
```

## Secrets Management

Credentials are stored in AWS Secrets Manager under the key `parking-tracker/secrets`.

Required secret keys:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`
- `TOKEN_SECRET` (32+ character random string for HMAC tokens)
- `FCM_PROJECT_ID` (Firebase project ID, optional for push notifications)
- `FCM_SERVICE_ACCOUNT_JSON` (Firebase service account key JSON, optional)

Create/update the secret:
```bash
aws secretsmanager create-secret \
    --name parking-tracker/secrets \
    --secret-string '{"TWILIO_ACCOUNT_SID":"xxx","TWILIO_AUTH_TOKEN":"xxx","TWILIO_FROM_NUMBER":"+1234567890","TOKEN_SECRET":"your-32-byte-random-secret-here"}'
```

## DynamoDB Schema

**Table**: `{stack-name}-config`

**Subscriptions**:
| pk | sk | Attributes |
|----|----|------------|
| DATE#{YYYY-MM-DD} | RESORT#{resort}#PHONE#{phone} | resort_name, date, phone_number, last_status, unsubscribe_token |

**Phone Registry**:
| pk | sk | Attributes |
|----|----|------------|
| PHONE#{phone} | META | phone_number, master_unsubscribe_token, invitation_code_used |

**Invitation Codes**:
| pk | sk | Attributes |
|----|----|------------|
| INVITE#{code} | CODE | code, max_uses, current_uses, expires_at |

**Global Secondary Index**: `phone-number-index` (phone_number -> pk)

## Managing Invitation Codes

Create invitation codes directly in DynamoDB:
```bash
aws dynamodb put-item \
    --table-name parking-tracker-config \
    --item '{
        "pk": {"S": "INVITE#MYCODE123"},
        "sk": {"S": "CODE"},
        "code": {"S": "MYCODE123"},
        "max_uses": {"N": "10"},
        "current_uses": {"N": "0"}
    }' \
    --profile personal
```

## API Endpoints

### Phone/Web Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/resorts | List available resorts |
| POST | /api/verify-code | Validate invitation code |
| POST | /api/subscribe | Subscribe to alerts (phone-based) |
| GET | /api/subscriptions | Get subscriptions (with token) |
| POST | /api/unsubscribe | Unsubscribe from specific alert |
| POST | /api/unsubscribe-all | Unsubscribe from all alerts |

### Device/Mobile Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/devices/register | Register device for push notifications |
| POST | /api/devices/refresh-token | Update FCM token |
| DELETE | /api/devices/{device_id} | Unregister a device |
| GET | /api/devices/{device_id}/subscriptions | Get device subscriptions |
| POST | /api/devices/{device_id}/subscribe | Subscribe device to alerts |
| POST | /api/devices/unsubscribe | Unsubscribe from specific alert |

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
- `DOMAIN_NAME`: Web interface domain (parking.foxjason.com)

## First-Time Deployment

1. Update `samconfig.toml` with your Route 53 HostedZoneId
2. Add `TOKEN_SECRET` to Secrets Manager
3. Run `sam build && sam deploy`
4. Wait for CloudFront distribution (15-20 min)
5. Deploy frontend: `aws s3 sync frontend/ s3://{bucket}/ --delete`
6. Create invitation codes in DynamoDB

## Mobile App (React Native)

### Development Commands

```bash
# Navigate to mobile directory
cd mobile

# Install dependencies
npm install

# Start Expo development server
npx expo start

# Run on Android emulator
npx expo run:android

# Run on iOS simulator (macOS only)
npx expo run:ios

# Build for production (requires EAS CLI)
npx eas build --platform android
npx eas build --platform ios
```

### Firebase Cloud Messaging Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project named `parking-tracker`
3. Add an Android app:
   - Package name: `com.parkingtracker.app`
   - Download `google-services.json` → place in `mobile/`
4. Go to Project Settings → Service Accounts → Generate new private key
5. Add FCM credentials to Secrets Manager:

```bash
# Update existing secret with FCM credentials
aws secretsmanager update-secret \
    --secret-id parking-tracker/secrets \
    --secret-string "$(jq -s '.[0] * .[1]' \
        <(aws secretsmanager get-secret-value --secret-id parking-tracker/secrets --query SecretString --output text) \
        <(echo '{"FCM_PROJECT_ID":"your-project-id","FCM_SERVICE_ACCOUNT_JSON":"{...}"}')\
    )" \
    --profile personal
```

### Device API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/devices/register | Register device for push notifications |
| POST | /api/devices/refresh-token | Update FCM token |
| DELETE | /api/devices/{device_id} | Unregister a device |
| GET | /api/devices/{device_id}/subscriptions | Get device subscriptions |
| POST | /api/devices/{device_id}/subscribe | Subscribe device to alerts |
| POST | /api/devices/unsubscribe | Unsubscribe from specific alert |

### DynamoDB Device Schema

**Device Registry**:
| pk | sk | Attributes |
|----|----|------------|
| DEVICE#{device_id} | META | device_id, fcm_token, platform, invitation_code_used, created_at |

**Device Subscriptions**:
| pk | sk | Attributes |
|----|----|------------|
| DATE#{YYYY-MM-DD} | RESORT#{resort}#DEVICE#{device_id} | device_id, resort_name, date, notification_type, unsubscribe_token |

**Phone-Device Link** (optional):
| pk | sk | Attributes |
|----|----|------------|
| PHONE#{phone} | DEVICE#{device_id} | phone_number, device_id, linked_at |
