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
- **Camera Feed**: WebSocket-delivered JPEG frames with ML blockage inference
- **Weather**: OpenMeteo API integration
- **Image Storage**: Cloudinary
- **Monitoring**: Prometheus metrics

## Prerequisites

- Python 3.12+
- PostgreSQL 15+

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
| `GROQ_MODELS` | No | `openai/gpt-oss-120b,openai/gpt-oss-20b` | Ordered Groq model fallback list |
| `VAPID_PRIVATE_KEY` | Yes | — | VAPID private key for Web Push |
| `VAPID_PUBLIC_KEY` | Yes | — | VAPID public key for Web Push |
| `VAPID_CLAIM_EMAIL` | Yes | — | VAPID claim email (mailto:) |
| `FRONTEND_URLS` | Yes | — | Comma-separated allowed CORS origins |
| `ORS_API_KEY` | For in-app directions | `""` | Server-side openrouteservice key; create one at https://account.heigit.org/ |
| `IOT_API_KEY` | No | `""` | API key for IoT sensor authentication |
| `ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `SMS_GATEWAY_URL` | No | `""` | SMS Gateway URL (local: `http://<ip>:8080`, cloud: `https://api.sms-gate.app`) |
| `SMS_GATEWAY_API_KEY` | No | `""` | SMS Gateway credentials (`username:password`) |
| `EXPOSE_DEV_OTP` | No | `false` | Development only: return the OTP to Patrol as `dev_otp` |
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

If `SMS_GATEWAY_URL` is empty, SMS delivery is disabled. For local demos, set `EXPOSE_DEV_OTP=true` so Patrol displays the code.

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
├── crud/                # Data access layer (22 CRUD classes)
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
| `/daily-summaries` | Aggregated daily sensor, weather, blockage, and risk summaries |
| `/analysis` | AI streaming analysis (SSE) |
| `/stream` | Camera frame upload/status; broadcasts live frames and runs ML inference |
| `/system-settings` | System configuration |
| `/health` | System health check (DB, scheduler, WebSocket) |
| `/ws` | WebSocket (real-time sensor, weather, blockage, fusion data) |
| `/iot` | IoT-facing current risk score |
| `/public` | Anonymous citizen-safe status and server-proxied evacuation routes |

## Daily Summaries

At midnight in the configured application timezone (UTC+8 by default), the
scheduler summarizes the completed day. Backfill runs daily at 12:30 AM,
before the 1:00 AM raw-data cleanup. Each run reads the
current `data_retention_days` setting and checks that many completed days
for missing summaries. Existing summaries are preserved;
days without retained raw readings are skipped. A failed backfill is logged;
missing summaries are checked again on the next scheduled run.

New summaries replay sensor, camera, and weather updates chronologically using
the shared live risk-scoring and camera-confidence rules, including anomaly
suppression and the rising-water bonus. Pre-midnight readings seed the trend
and confidence window. Stale inputs are excluded using the configured source
warning periods. Reconstruction uses current configuration and retained raw
data; it is not an exact archive of past live scores or server restart state.
The summary API accepts inclusive `YYYY-MM-DD` ranges and returns available
days in the same date-only format.

## Reading Logs PDF reports

The admin's AI overview creates an owner-scoped report before generating analysis.
`POST /api/v1/analysis/reports` accepts an idempotency `request_id` UUID plus
`location_id`, `start_date`, and `end_date`; the server reads and saves the daily
summaries itself. Dates are inclusive, cover completed days, and are limited to
366 days. The response supplies the canonical summaries, card statistics, timezone,
missing dates, and snapshot hash used by the admin and the PDF.

`POST /api/v1/analysis/reports/{id}/stream` analyzes that snapshot. The backend
persists the exact text and model before signaling completion. Interrupted,
empty, or token-truncated output cannot be exported. Retries use the same data;
a completed report returns its saved overview without another AI request.
`GET /api/v1/analysis/reports/{id}` restores status and completed text.
`GET /api/v1/analysis/reports/{id}/pdf` returns a private attachment only to its
creator. The first successful PDF is stored, so subsequent downloads use identical
bytes even if live summaries change. Closing the drawer keeps a completed report
for the current page session; changing the location or dates starts a new report.

PDFs contain the selected period, capture/export timestamps in the application's
timezone, cards, four vector charts, every daily summary, extrema observation times,
weather codes, missing dates, provenance, and the saved AI overview. Long ranges
use consecutive 30-day chart panels; missing observations stay as gaps. Tables
repeat their headers and the A4 layout numbers every page. HTML/AI text is escaped;
reports contain no scripts or remote assets.

Run `alembic upgrade head` before using these endpoints. The Docker image installs
Chromium and local fonts; local development needs Chromium 131+ installed and
`REPORT_CHROMIUM_EXECUTABLE_PATH` set to its executable. Rendering uses the
[Chrome DevTools print API](https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-printToPDF)
with an isolated temporary profile, an ephemeral loopback-only connection, explicit
load/font readiness, and CSS page sizing/background printing. Existing `websockets`
provides the connection; no additional Python package is needed.

| Setting | Default | Purpose |
|---------|---------|---------|
| `REPORT_CHROMIUM_EXECUTABLE_PATH` | auto-detect | `/usr/bin/chromium` in Docker |
| `REPORT_CHROMIUM_NO_SANDBOX` | `false` | Docker sets `true` for its root process; leave `false` for a compatible non-root Chromium sandbox |
| `REPORT_RETENTION_DAYS` | `30` | Lifetime of snapshots, analysis and cached PDFs; separate from raw-reading retention |
| `REPORT_MAX_DAYS` | `366` | Maximum inclusive reporting period |
| `REPORT_ANALYSIS_TIMEOUT_SECONDS` | `120` | Provider time limit; interrupted claims become retryable |
| `REPORT_PDF_TIMEOUT_SECONDS` | `60` | Whole renderer time limit; process groups and temporary files are cleaned on failure/cancellation |

Report creation and analysis are limited to 6 requests/minute; downloads to
10/minute using the existing API limiter. One PDF renders per backend worker;
busy workers return a retryable 503 rather than building an unbounded queue. PDFs
are capped at 20 MiB. Expired reports are inaccessible immediately and are deleted
by the existing 01:00 cleanup job. A crashed analysis claim may be recovered after
its timeout plus a 30-second grace period. For heavier export traffic, use a
separate bounded worker queue and object storage rather than raising these limits.

Focused validation (no live database or AI requests):

```bash
venv/bin/python -m pytest app/tests/services/test_reading_report.py app/tests/endpoints/test_reading_report.py app/tests/services/test_analysis_service.py
# Optional native rendering checks: 1, 31, and 366 days, null metrics, long AI text.
REPORT_TEST_CHROMIUM=/usr/bin/chromium venv/bin/python -m pytest app/tests/services/test_reading_report.py -k native
# Native checks also require the pdftotext command (poppler-utils on Debian).
```
