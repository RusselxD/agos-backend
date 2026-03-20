# Database Schema

PostgreSQL with async SQLAlchemy (asyncpg). All timestamps default to UTC.

## Entity Relationship Diagram

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────────┐
│ admin_users  │──┬──│ admin_audit_logs   │     │ system_settings  │
│              │  │  └───────────────────┘     │ (key: PK, JSONB) │
│ UUID PK      │  │                            └──────────────────┘
│ phone_number │  ├──│ refresh_tokens     │
│ hashed_pass  │  │  └───────────────────┘
│ is_superuser │  │
│ created_by   │──┘  ┌───────────────────┐
│              │─────│ notification_      │
│              │     │ templates          │
│              │─────│ notification_      │     ┌──────────────────┐
│              │     │ dispatches         │─────│ notification_    │
└──────┬───────┘     └───────────────────┘     │ deliveries       │
       │                                        │                  │
       │ created_by                             │ dispatch_id FK   │
       ▼                                        │ responder_id FK  │
┌──────────────┐                                │ subscription_id  │
│ responders   │────────────────────────────────│ status (enum)    │
│              │                                └────────┬─────────┘
│ UUID PK      │     ┌───────────────────┐               │
│ phone_number │─────│ responder_groups   │     ┌────────▼─────────┐
│ status       │     │ (M2M join table)  │     │ acknowledgements │
│ location_id  │     └───────────────────┘     │                  │
│ notif_prefs  │                                │ delivery_id FK   │
│              │─────┌───────────────────┐     │ responder_id FK  │
│              │     │ push_subscriptions │     │ message          │
│              │     └───────────────────┘     └──────────────────┘
│              │
│              │─────┌───────────────────┐
│              │     │ responders_otp_    │
└──────┬───────┘     │ verification      │
       │             └───────────────────┘
       │ location_id FK
       ▼
┌──────────────┐
│ locations    │
│              │
│ INT PK       │──┬──┌───────────────────┐
│ name         │  │  │ sensor_devices    │──── sensor_readings
│ latitude     │  │  └───────────────────┘
│ longitude    │  │
│              │  ├──┌───────────────────┐
│              │  │  │ camera_devices    │──── model_readings
│              │  │  └───────────────────┘
│              │  │
│              │  ├──│ weather           │
│              │  │  └───────────────────┘
│              │  │
│              │  └──│ daily_summaries   │
└──────────────┘     └───────────────────┘
```

## Tables

### admin_users

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| phone_number | VARCHAR | UNIQUE, NOT NULL |
| first_name | VARCHAR | NOT NULL |
| last_name | VARCHAR | NOT NULL |
| hashed_password | VARCHAR | NOT NULL |
| is_superuser | BOOLEAN | DEFAULT false |
| is_enabled | BOOLEAN | DEFAULT true |
| force_password_change | BOOLEAN | DEFAULT true |
| created_at | TIMESTAMP | DEFAULT UTC now |
| last_login | TIMESTAMP | NULLABLE |
| deactivated_at | TIMESTAMP | NULLABLE |
| created_by | UUID | FK → admin_users.id, NULLABLE |
| deactivated_by | UUID | FK → admin_users.id, NULLABLE |

### admin_audit_logs

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, AUTO |
| admin_user_id | UUID | FK → admin_users.id, CASCADE |
| action | VARCHAR(225) | NOT NULL |
| created_at | TIMESTAMP | DEFAULT UTC now |

### refresh_tokens

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| admin_user_id | UUID | FK → admin_users.id, CASCADE |
| token | VARCHAR | UNIQUE |
| expires_at | TIMESTAMP | NOT NULL |

### locations

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, AUTO |
| name | VARCHAR(100) | UNIQUE |
| latitude | FLOAT | NOT NULL |
| longitude | FLOAT | NOT NULL |

### sensor_devices

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, AUTO |
| location_id | INTEGER | FK → locations.id, UNIQUE |
| device_name | VARCHAR | NOT NULL |
| sensor_config | JSON | SensorConfig (installation_height, warning_threshold, critical_threshold) |

### sensor_readings

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, AUTO |
| sensor_device_id | INTEGER | FK → sensor_devices.id, CASCADE |
| water_level_cm | NUMERIC(5,2) | NOT NULL |
| raw_distance_cm | NUMERIC(5,2) | NOT NULL |
| signal_strength | INTEGER | NOT NULL |
| timestamp | TIMESTAMP | DEFAULT UTC now, INDEXED |
| created_at | TIMESTAMP | DEFAULT UTC now |

### camera_devices

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, AUTO |
| location_id | INTEGER | FK → locations.id, UNIQUE |
| device_name | VARCHAR | NOT NULL |

### model_readings

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, AUTO |
| camera_device_id | INTEGER | FK → camera_devices.id, CASCADE |
| image_path | VARCHAR | NOT NULL |
| blockage_percentage | FLOAT | 0-100 |
| blockage_status | VARCHAR | "clear" / "partial" / "blocked" |
| total_debris_count | INTEGER | DEFAULT 0 |
| timestamp | TIMESTAMP | DEFAULT UTC now |
| created_at | TIMESTAMP | DEFAULT UTC now |

### weather

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, AUTO |
| location_id | INTEGER | FK → locations.id |
| precipitation_mm | FLOAT | |
| weather_code | INTEGER | WMO code |
| temperature_2m | FLOAT | Celsius |
| relative_humidity_2m | FLOAT | Percentage |
| wind_speed_10m | FLOAT | km/h |
| wind_direction_10m | FLOAT | Degrees |
| cloud_cover | FLOAT | Percentage |
| created_at | TIMESTAMP | DEFAULT UTC now |

### daily_summaries

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, AUTO |
| location_id | INTEGER | FK → locations.id, CASCADE |
| summary_date | DATE | INDEXED |
| min/max_risk_score | FLOAT | |
| min/max_risk_timestamp | TIMESTAMP | |
| min/max_debris_count | INTEGER | |
| least/most_severe_blockage | VARCHAR | |
| min/max_water_level_cm | NUMERIC(5,2) | |
| min/max_precipitation_mm | FLOAT | |
| most_severe_weather_code | INTEGER | |
| created_at | TIMESTAMP | DEFAULT UTC now |

**Unique constraint:** `(location_id, summary_date)`

### responders

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| phone_number | VARCHAR(20) | UNIQUE |
| first_name | VARCHAR | NOT NULL |
| last_name | VARCHAR | NOT NULL |
| status | ENUM | "pending" / "active" |
| location_id | INTEGER | FK → locations.id, DEFAULT 1 |
| notif_preferences | JSON | NotificationPreference (warning, critical, blockage, announcement booleans) |
| created_by | UUID | FK → admin_users.id, NULLABLE |
| activated_at | TIMESTAMP | NULLABLE |
| created_at | TIMESTAMP | DEFAULT UTC now |

### groups

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, AUTO |
| name | VARCHAR(100) | UNIQUE |

Default group: "All Active Responders" (auto-created, cannot be deleted).

### responder_groups (join table)

| Column | Type | Constraints |
|--------|------|-------------|
| responder_id | UUID | FK → responders.id |
| group_id | INTEGER | FK → groups.id |

### responders_otp_verification

| Column | Type | Constraints |
|--------|------|-------------|
| responder_id | UUID | PK, FK → responders.id |
| otp_hash | VARCHAR | NOT NULL (Argon2) |
| attempt_count | INTEGER | DEFAULT 0 |
| created_at | TIMESTAMP | DEFAULT UTC now |
| expires_at | TIMESTAMP | NOT NULL |

### notification_templates

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, AUTO |
| type | ENUM | "warning" / "critical" / "blockage" / "announcement" |
| title | VARCHAR | NOT NULL |
| message | VARCHAR | NOT NULL |
| created_by_id | UUID | FK → admin_users.id |

**Partial unique index:** Only one template per type for warning, critical, blockage. Announcement allows multiple.

### notification_dispatches

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, AUTO |
| type | ENUM | NotificationType |
| title | VARCHAR | NOT NULL |
| message | VARCHAR | NOT NULL |
| created_at | TIMESTAMP | DEFAULT UTC now |

### notification_deliveries

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| dispatch_id | INTEGER | FK → notification_dispatches.id |
| responder_id | UUID | FK → responders.id |
| subscription_id | UUID | FK → push_subscriptions.id, NULLABLE |
| status | ENUM | "pending" / "sent" / "failed" |
| sent_at | TIMESTAMP | NULLABLE |
| error_message | TEXT | NULLABLE |
| created_at | TIMESTAMP | DEFAULT UTC now |

**Unique constraints:** `(dispatch_id, responder_id)`, `(id, responder_id)`
**Index:** `(responder_id, status)`

### acknowledgements

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| delivery_id | UUID | FK → notification_deliveries.id |
| responder_id | UUID | FK → responders.id |
| message | VARCHAR | NULLABLE |
| acknowledged_at | TIMESTAMP | DEFAULT UTC now |

**Unique constraint:** `delivery_id` (one ack per delivery)
**Composite FK:** `(delivery_id, responder_id)` → `(notification_deliveries.id, notification_deliveries.responder_id)`

### push_subscriptions

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| responder_id | UUID | FK → responders.id, CASCADE |
| endpoint | TEXT | NOT NULL |
| p256dh | TEXT | NOT NULL |
| auth | TEXT | NOT NULL |
| created_at | TIMESTAMP | DEFAULT UTC now |

**Unique constraint:** `(responder_id, endpoint)`

### system_settings

| Column | Type | Constraints |
|--------|------|-------------|
| key | TEXT | PK |
| json_value | JSONB | NOT NULL |

### password_reset_otps

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PK, AUTO |
| admin_user_id | UUID | FK → admin_users.id |
| otp_code | VARCHAR(6) | NOT NULL |
| expires_at | TIMESTAMP | NOT NULL |
