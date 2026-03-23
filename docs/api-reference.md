# API Reference

Base URL: `/api/v1`

Auth legend: `JWT` = admin token required, `SU` = superuser required, `IOT` = IoT API key required, `—` = no auth.

---

## Auth (`/auth`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/login` | — | Authenticate with phone_number + password. Returns access + refresh tokens. Rate limited: 5/min. |
| POST | `/logout` | JWT | Invalidates refresh token. |
| POST | `/refresh` | — | Exchange refresh token for new access + refresh tokens. |
| POST | `/change-password` | JWT | Change password. Returns new tokens. Rate limited: 3/min. |

**POST /login**
```json
// Request
{ "phone_number": "09171234567", "password": "secret" }

// Response 200
{ "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer" }
```

---

## Admin Users (`/admin-users`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | JWT | List all admin users. |
| POST | `/` | SU | Create new admin user. |
| PUT | `/{user_id}/deactivate` | SU | Deactivate admin user. Invalidates sessions. |
| PUT | `/{user_id}/reactivate` | SU | Reactivate admin user. |

**POST /**
```json
// Request
{ "phone_number": "09171234567", "first_name": "John", "last_name": "Doe", "password": "secret" }

// Response 200
{ "id": "uuid", "phone_number": "09171234567", "first_name": "John", "last_name": "Doe", "is_superuser": false, "is_enabled": true, "last_login": null, "created_by": "admin-uuid" }
```

---

## Admin Audit Logs (`/admin-audit-logs`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/paginated` | JWT | Paginated admin activity logs. Params: `page`, `page_size` (default 10). |

**Response**
```json
{ "logs": [{ "action": "Created admin user", "created_at": "2026-03-20T10:00:00Z", "admin_name": "John Doe" }], "has_more": true }
```

---

## Core (`/core`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/location-details` | JWT | Returns default location (id, name). |
| GET | `/device-details` | JWT | Returns sensor + camera device IDs for location. Param: `location_id`. |

---

## Responders — Admin (`/responders`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/all` | JWT | List all responders. |
| GET | `/additional-details/{responder_id}` | JWT | Detailed responder info (groups, push status, delivery stats). |
| POST | `/bulk` | JWT | Bulk create responders. |

**POST /bulk**
```json
// Request
[{ "first_name": "Jane", "last_name": "Doe", "phone_number": "09171234567" }]

// Response 201
[{ "id": "uuid", "first_name": "Jane", "last_name": "Doe", "phone_number": "09171234567", "status": "pending", "has_push_subscription": false }]
```

---

## Responder App — Self-Service (`/responder`)

Auth legend: `RESP` = responder JWT token required (issued after OTP verification, 90-day expiry).

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/{responder_id}` | RESP | Get responder profile for app. |
| GET | `/unread-alerts-count/{responder_id}` | RESP | Count of unread alerts. |
| GET | `/alerts/{responder_id}` | RESP | Paginated alerts. Params: `page`, `page_size`, `type` (optional filter). |
| POST | `/acknowledge-alert` | RESP | Acknowledge an alert. |
| GET | `/notif-preferences/{responder_id}` | RESP | Get notification preferences. |
| PUT | `/notif-preferences/{responder_id}` | RESP | Update notification preference (key + value). |
| GET | `/water-level-trend/{location_id}` | RESP | Last 24h water level trend (~50 data points). |
| POST | `/for-approval` | — | Phone lookup → sends OTP. |
| POST | `/resend-otp/{responder_id}` | — | Resend OTP (204). |
| POST | `/verify-otp` | — | Verify OTP → activate responder. Returns `responder_token` on success. |
| POST | `/send-sms` | — | Send SMS to multiple responders (204). |

**POST /for-approval**
```json
// Request
{ "phone_number": "09171234567" }

// Response 200
{ "responder_id": "uuid", "first_name": "Jane", "last_name": "Doe", "phone_number": "09171234567", "status": "pending" }
```

**POST /verify-otp**
```json
// Request
{ "responder_id": "uuid", "otp": "123456" }

// Response 200
{ "success": true, "message": "OTP verified successfully.", "requires_resend": false, "responder_token": "eyJ..." }
```

**GET /alerts/{responder_id} Response**
```json
{ "items": [{ "id": "uuid", "type": "critical", "title": "...", "message": "...", "timestamp": "...", "is_acknowledged": false, "acknowledged_at": null, "acknowledge_message": null }], "has_more": true }
```

---

## Responder Groups (`/responder-groups`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/all` | JWT | List all groups with member IDs. |
| POST | `/` | JWT | Create group with initial members. |
| PUT | `/{group_id}` | JWT | Update group name and members. |
| DELETE | `/{group_id}` | JWT | Delete group (204). Cannot delete default group. |

---

## Sensor Devices (`/sensor-devices`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/{id}/status` | JWT | Device connection status, signal strength. |
| GET | `/{id}/config` | JWT | Sensor thresholds (installation_height, warning, critical). |
| PUT | `/{id}/config` | JWT | Update sensor configuration. |
| GET | `/{location_id}/config/by-location` | — | Get config by location (responder app use). |

---

## Sensor Readings (`/sensor-readings`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/paginated` | JWT | Paginated readings. Params: `page`, `page_size`, `sensor_device_id`. |
| GET | `/trend` | JWT | Trend data (bucketed averages). Params: `sensor_device_id`, `duration` (1h/6h/12h/24h/7d). |
| GET | `/available-days` | JWT | Days with recorded data. Params: `sensor_device_id`. |
| GET | `/for-export` | JWT | Readings for date range export. Params: `sensor_device_id`, `start_date`, `end_date`. |
| POST | `/record` | IOT | Record reading from IoT device. Rate limited: 60/min. |

**POST /record**
```json
// Request
{ "sensor_device_id": 1, "raw_distance_cm": 150.5, "signal_strength": -45 }

// Response 201
{ "timestamp": "2026-03-20T10:00:00Z", "status": "success" }
```

**GET /paginated Response**
```json
{ "items": [{ "id": 1, "water_level_cm": 25.5, "status": "normal", "change_rate": 0.3, "timestamp": "..." }], "has_more": true }
```

---

## Weather (`/weather`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/comprehensive-summary/{location_id}` | JWT | Full weather summary with derived fields. |

**Response** includes: precipitation_mm, weather_code, temperature, humidity, wind speed/direction, cloud cover, condition name, comfort level, storm risk level.

---

## Model Reading Logs (`/model-reading-logs`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/paginated` | JWT | Paginated blockage detections. Params: `page`, `page_size`, `camera_device_id`, `blockage_status` (optional filter). |
| GET | `/{reading_id}` | JWT | Full detail including image path. |

---

## Notification Templates (`/notification-templates`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/all` | JWT | List all templates. |
| POST | `/` | JWT | Create template (type uniqueness enforced for warning/critical/blockage). |
| PUT | `/{template_id}` | JWT | Update template. |
| DELETE | `/{template_id}` | JWT | Delete template. |

---

## Notification Logs (`/notification-logs`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/responders-summary` | JWT | Per-responder delivery stats (total, sent, failed, pending, acknowledged). |
| GET | `/responder/{responder_id}/deliveries` | JWT | Paginated delivery history. Optional `type` filter. |
| GET | `/analytics` | JWT | Response time analytics: avg/ack rate, per-type breakdown, top responders. Optional `date_from`, `date_to`. |
| GET | `/export` | JWT | Flat delivery data for Excel export. Optional `date_from`, `date_to`. |

---

## Push Notifications (`/push`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/vapid-public-key` | — | Returns VAPID public key for client subscription. |
| POST | `/subscribe` | RESP | Save push subscription. Validates responder owns the subscription. |
| POST | `/send-notification` | JWT | Send push to selected responders. |

**POST /send-notification**
```json
// Request
{ "responder_ids": ["uuid1", "uuid2"], "template_id": 1, "custom_notification": null }
// OR
{ "responder_ids": ["uuid1"], "template_id": null, "custom_notification": { "title": "Test", "message": "Hello", "type": "announcement" } }
```

---

## Daily Summaries (`/daily-summaries`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | JWT | Summaries for date range. Params: `location_id`, `start_date`, `end_date`. |
| GET | `/available-days/{location_id}` | JWT | Days with summary data. |

---

## Analysis (`/analysis`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/daily-summaries` | JWT | AI analysis via Groq LLM. SSE streaming response. |

---

## Stream (`/stream`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/status` | — | Camera online status. |
| POST | `/upload-image` | IOT | Upload frame, run ML inference, broadcast. Rate limited: 35/min. |

---

## System Settings (`/system-settings`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/{key}` | JWT | Get setting object. |
| GET | `/{key}/value` | JWT | Get setting value only. |
| PUT | `/{key}` | JWT | Update setting (audit logged). |

**Known Settings Keys:**
| Key | Default | Description |
|-----|---------|-------------|
| `data_retention_days` | varies | Days to keep sensor/model/weather readings |
| `alert_thresholds` | JSON | Fusion analysis tier thresholds |
| `escalation_timeout_minutes` | 15 | Minutes before unacknowledged critical alert is escalated |
| `max_escalation_count` | 3 | Maximum re-notification attempts per delivery |

---

## Health (`/health`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | — | System health check. Returns DB, scheduler, WebSocket status. 200 if healthy, 503 if degraded. |

**Response**
```json
{ "status": "healthy", "components": { "database": "healthy", "scheduler": "running", "websocket_connections": 3 } }
```

---

## WebSocket (`/ws`)

| Endpoint | Auth | Description |
|----------|------|-------------|
| `WS /ws?location_id={id}` | — | Client connection. Receives sensor, blockage, weather, fusion updates. |
| `WS /ws/rpi?camera_device_id={id}&location_id={id}` | — | RPi camera. Sends binary frames for ML inference. |

### WebSocket Message Format

All messages follow:
```json
{ "status": "success", "message": "description", "<data_field>": { ... } }
```

| Message type | Data field | Trigger |
|-------------|------------|---------|
| `sensor_update` | `sensor_reading` | New sensor reading recorded |
| `blockage_detection_update` | `blockage_status` | ML inference on camera frame |
| `weather_update` | `weather_condition` | Scheduled weather fetch |
| `fusion_analysis_update` | `fusion_analysis` | Any data source update |
