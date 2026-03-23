# AGOS Backend

FastAPI backend for AGOS — a real-time water management and flood monitoring platform.

## Stack

- **Framework**: FastAPI 0.124
- **Database**: PostgreSQL (async via SQLAlchemy 2.0 + asyncpg)
- **Migrations**: Alembic
- **Auth**: JWT (access + refresh tokens) with Argon2 password hashing
- **AI**: Groq API for daily summary analysis (SSE streaming)
- **Push Notifications**: Web Push (pywebpush + VAPID)
- **SMS OTP**: Android SMS Gateway (SMSGate) via HTTP
- **Video**: FFmpeg-based HLS stream processing
- **Weather**: OpenMeteo API integration
- **Image Storage**: Cloudinary
- **Monitoring**: Prometheus metrics

## Prerequisites

- Python 3.12+
- PostgreSQL 15+
- FFmpeg (for video stream processing)

## Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your values (see Environment Variables below)

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `SECRET_KEY` | Yes | — | JWT signing secret |
| `GROQ_API_KEYS` | Yes | — | Comma-separated Groq API keys for AI analysis |
| `VAPID_PRIVATE_KEY` | Yes | — | VAPID private key for Web Push |
| `VAPID_PUBLIC_KEY` | Yes | — | VAPID public key for Web Push |
| `VAPID_CLAIM_EMAIL` | Yes | — | VAPID claim email (mailto:) |
| `FRONTEND_URLS` | Yes | — | Comma-separated allowed CORS origins |
| `IOT_API_KEY` | No | `""` | API key for IoT sensor authentication |
| `ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `SMS_GATEWAY_URL` | No | `""` | SMS Gateway URL (local: `http://<ip>:8080`, cloud: `https://api.sms-gate.app`) |
| `SMS_GATEWAY_API_KEY` | No | `""` | SMS Gateway credentials (`username:password`) |
| `CLOUDINARY_CLOUD_NAME` | No | — | Cloudinary cloud name for image uploads |
| `CLOUDINARY_API_KEY` | No | — | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | No | — | Cloudinary API secret |

## SMS Gateway Setup

AGOS uses an Android phone as an SMS gateway for OTP delivery via the [SMSGate](https://github.com/capcom6/android-sms-gateway) app.

**Local mode** (same network):
```
SMS_GATEWAY_URL=http://192.168.x.x:8080
SMS_GATEWAY_API_KEY=username:password
```

**Cloud mode** (deployed):
```
SMS_GATEWAY_URL=https://api.sms-gate.app
SMS_GATEWAY_API_KEY=username:password
```

If `SMS_GATEWAY_URL` is empty, OTPs are logged to the console instead of being sent via SMS.

## Project Structure

```
app/
├── api/v1/
│   ├── endpoints/       # Route handlers (20 files)
│   └── router.py        # Route registration
├── core/
│   ├── config.py        # Settings (pydantic-settings)
│   ├── security.py      # JWT + Argon2 hashing (admin + responder tokens)
│   ├── state.py         # Fusion analysis state manager (auto-notify on critical)
│   ├── scheduler.py     # APScheduler (daily summary, cleanup, escalation)
│   ├── escalation.py    # Automated escalation for unacknowledged alerts
│   ├── fusion_scoring.py # Combined risk score calculation
│   └── exceptions.py    # Custom exceptions
├── crud/                # Data access layer (21 CRUD classes)
├── models/              # SQLAlchemy models
│   ├── data_sources/    # Location, SensorDevice, SensorReading, Weather, etc.
│   └── responder_related/  # Responder, Group, NotificationDelivery, etc.
├── schemas/             # Pydantic request/response schemas
└── services/            # Business logic layer
    ├── daily_summary/
    ├── responder/
    ├── responder_group/
    ├── sensor_reading/
    ├── stream/
    └── weather/
```

## API Overview

| Prefix | Description |
|--------|-------------|
| `/auth` | Admin login, logout, token refresh |
| `/admin-users` | Admin user management (create, deactivate, reactivate) |
| `/admin-audit-logs` | Admin activity logs |
| `/responders` | Admin responder management (bulk create, list, details) |
| `/responder` | Responder self-service (OTP verify + JWT token, paginated alerts, preferences, water level trend) |
| `/responder-groups` | Responder group CRUD |
| `/sensor-devices` | Sensor device config and status |
| `/sensor-readings` | Sensor data (paginated, trends, export) |
| `/weather` | Weather data (OpenMeteo) |
| `/model-reading-logs` | AI blockage detection history |
| `/notification-logs` | Notification delivery history, analytics, export |
| `/notification-templates` | Notification template CRUD |
| `/push` | VAPID key + push subscription |
| `/daily-summaries` | AI-generated daily reading summaries |
| `/analysis` | AI streaming analysis (SSE) |
| `/stream` | HLS video stream management |
| `/system-settings` | System configuration |
| `/health` | System health check (DB, scheduler, WebSocket) |
| `/ws` | WebSocket (real-time sensor, weather, blockage, fusion data) |
