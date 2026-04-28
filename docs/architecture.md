# Backend Architecture

## Overview

The AGOS backend is a FastAPI application serving as the central API for both the admin dashboard and the responder PWA. It ingests data from IoT sensors, cameras, and weather APIs, processes it through ML and fusion analysis, and broadcasts real-time updates via WebSocket.

## Three-Layer Architecture

```
Endpoints (app/api/v1/endpoints/)
    │
    ▼
Services (app/services/)
    │
    ▼
CRUD (app/crud/)
    │
    ▼
Database (PostgreSQL via async SQLAlchemy)
```

**Endpoints** — Thin route handlers. Declare auth dependencies, validate input via Pydantic schemas, delegate to services, return response models.

**Services** — Business logic. Instantiated as module-level singletons (e.g., `responder_app_service = ResponderAppService()`). Handle orchestration, external API calls, data transformation.

**CRUD** — Data access. Extend `CRUDBase` generic class. Each CRUD class is a singleton exported from `app/crud/__init__.py`. Use async SQLAlchemy with `select()`, `joinedload()`, and window functions.

## Registration Pattern

New features must be registered in multiple `__init__.py` files:

| What | Register in |
|------|------------|
| CRUD class | `app/crud/__init__.py` |
| Service class | `app/services/__init__.py` |
| Pydantic schema | `app/schemas/__init__.py` |
| Router | `app/api/v1/router.py` (include_router) |

## Authentication

Four auth levels:

| Level | Mechanism | Dependency | Used by |
|-------|-----------|------------|---------|
| Admin (read) | JWT Bearer | `Depends(require_auth)` | Most admin endpoints |
| Admin (superuser write) | JWT Bearer + superuser | `Depends(require_superuser)` | Admin user creation, deactivation, reactivation |
| IoT device | API key header | `Depends(require_iot_api_key)` | Sensor readings, frame upload |
| Responder | JWT Bearer with `type=responder` claim | `Depends(require_responder_auth)` | Responder app endpoints, push subscription |

Admin JWT tokens use 15-minute access tokens plus 7-day refresh tokens. Responder JWT tokens are issued after OTP verification and expire after 90 days. Passwords and OTPs are hashed with Argon2.

## Real-Time Data Flow

### WebSocket Architecture

Two WebSocket endpoints:

1. **`/ws?location_id={id}`** — Frontend/responder clients. Receives real-time updates.
2. **`/ws/rpi?camera_device_id={id}&location_id={id}`** — Raspberry Pi camera. Sends binary frames for ML inference.

### Message Types

| Type | Source | Description |
|------|--------|-------------|
| `sensor_update` | `POST /sensor-readings/record` | Water level reading + calculated summary |
| `blockage_detection_update` | ML inference on camera frame | Blockage status + percentage |
| `weather_update` | Scheduled weather fetch (APScheduler) | Weather conditions from OpenMeteo |
| `fusion_analysis_update` | Any of the above triggers recalculation | Combined risk score |
| `camera_update` | `POST /stream/upload-image` or `WS /ws/rpi` binary frame | Base64 JPEG frame for the admin live camera panel |

### Data Ingestion → Broadcast Flow

```
IoT Sensor ──POST /sensor-readings/record──► SensorReadingService
                                                │
                                                ├──► Store in DB
                                                ├──► Calculate summary (water level, trend, alert)
                                                ├──► Update fusion state
                                                └──► WebSocket broadcast (sensor_update + fusion_analysis_update)

Camera ──WS /ws/rpi or POST /stream/upload-image──► MLService
                                        │
                                        ├──► Throttle (2-min interval per camera)
                                        ├──► Broadcast raw frame as camera_update
                                        ├──► Run inference (blockage detection)
                                        ├──► Upload image to Cloudinary
                                        ├──► Store ModelReading in DB
                                        ├──► Update fusion state
                                        └──► WebSocket broadcast (blockage_detection_update + fusion_analysis_update)

APScheduler ──every N minutes──► WeatherService
                                    │
                                    ├──► Fetch from OpenMeteo API
                                    ├──► Store in DB
                                    ├──► Update fusion state
                                    └──► WebSocket broadcast (weather_update + fusion_analysis_update)
```

## Notification System

### Push Notification Flow

1. Admin triggers notification → `POST /push/send-notification`
2. `NotificationService` creates `NotificationDispatch` record
3. Looks up active responders with push subscriptions
4. Sends Web Push to each subscription via `pywebpush`
5. Creates `NotificationDelivery` records (PENDING → SENT/FAILED)
6. Responder's service worker receives push → native notification
7. Responder acknowledges → `POST /responder/acknowledge-alert`

### SMS OTP Flow

1. Responder enters phone → `POST /responder/for-approval`
2. Service generates 6-digit OTP, hashes with Argon2, stores with 10-min expiry
3. Sends plaintext OTP via `SMSService` → Android SMS Gateway (SMSGate app)
4. Responder enters OTP → `POST /responder/verify-otp`
5. Service verifies hash, checks expiry and attempt count (max 5)
6. On success: activate responder, add to default group, delete OTP record, return a 90-day responder JWT

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Weather fetch | Configurable interval | Fetches from OpenMeteo, stores, broadcasts |
| Daily summary | Midnight (UTC+8) | Aggregates sensor, model, weather data per location |
| Data cleanup | 1:00 AM (UTC+8) | Purges old data based on retention settings |
| Alert escalation | Every 5 minutes | Re-notifies unacknowledged critical alert deliveries |

## Caching

`CacheService` provides in-memory caching for frequently accessed, rarely changing data:

- Device IDs (sensor, camera)
- Location coordinates
- Sensor configuration (thresholds)
- Alert thresholds

Cache is populated on first access and invalidated on config updates.

## External Integrations

| Service | Purpose | Module |
|---------|---------|--------|
| OpenMeteo | Weather data | `app/services/weather/api_client.py` |
| Cloudinary | Image storage (blockage frames) | `app/services/upload_service.py`, `app/services/ml_service.py` |
| Groq | LLM analysis of daily summaries (SSE) | `app/services/analysis_service.py` |
| SMSGate | SMS OTP delivery via Android phone | `app/services/sms_service.py` |
| Web Push | VAPID-based push notifications | `app/services/notification_service.py` |

## Rate Limiting

| Endpoint | Limit | Reason |
|----------|-------|--------|
| `POST /auth/login` | 5/minute | Brute force prevention |
| `POST /auth/change-password` | 3/minute | Brute force prevention |
| `POST /sensor-readings/record` | 60/minute | IoT device throttle |
| `POST /stream/upload-image` | 35/minute | Camera frame throttle |
| `POST /responder/for-approval` | 5/minute | OTP abuse prevention |
| `POST /responder/resend-otp/{id}` | 3/minute | OTP resend abuse prevention |
| `POST /responder/verify-otp` | 5/minute | OTP brute force prevention |

## File Structure

```
app/
├── api/v1/
│   ├── endpoints/          # 21 route handler files
│   └── router.py           # Central route registration
├── core/
│   ├── config.py           # Pydantic settings (env vars)
│   ├── database.py         # Async engine + session factory
│   ├── security.py         # JWT + Argon2
│   └── exceptions.py       # Custom SMS exceptions
├── crud/                   # 22 CRUD classes + CRUDBase
├── models/
│   ├── data_sources/       # Location, SensorDevice, SensorReading, Weather, etc.
│   └── responder_related/  # Responder, Group, NotificationDelivery, etc.
├── schemas/
│   └── reading_summary_response/  # WebSocket response types
└── services/
    ├── daily_summary/      # Daily aggregation + risk scoring
    ├── responder/          # Admin management + responder self-service
    ├── responder_group/    # Group CRUD + validation
    ├── sensor_reading/     # Recording, trends, export
    ├── stream/             # Camera frame ingestion helpers
    └── weather/            # OpenMeteo fetch, persistence, scheduling
```
