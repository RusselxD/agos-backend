from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pydantic import field_validator
from typing import Union
from datetime import timedelta, timezone, tzinfo


class Settings(BaseSettings):
    UTC_OFFSET_HOURS: float = 8

    OTP_LENGTH: int = 6
    OTP_ATTEMPT_LIMIT: int = 5
    OTP_EXPIRY_MINUTES: int = 10
    OTP_RESEND_COOLDOWN_SECONDS: int = 60

    # Camera / ML Settings
    FRAME_CAPTURE_INTERVAL_SECONDS: int = 60 * 2  # ML inference throttle interval (seconds)
    # F1 — adaptive sampling: shortened interval while fusion risk is elevated.
    FRAME_CAPTURE_INTERVAL_ELEVATED_SECONDS: int = 30
    MAX_IMAGE_UPLOAD_BYTES: int = 5 * 1024 * 1024  # 5 MB

    # F1 — surface-obstruction confidence engine (rolling window over inference readings)
    OBSTRUCTION_WINDOW_K: int = 5              # readings considered per confidence window
    OBSTRUCTION_TIER_LIKELY: float = 0.6      # >= fraction flagged -> "likely"
    OBSTRUCTION_TIER_CONFIRMED: float = 0.8   # >= fraction flagged -> "confirmed"
    OBSTRUCTION_PARTIAL_WEIGHT: float = 0.5   # weight of a "partial" reading vs a full "blocked"

    # F2 — weather provider abstraction + sub-hourly refresh
    WEATHER_PROVIDER: str = "openmeteo"       # "openweathermap" | "weatherapi" | "openmeteo"
    OPENWEATHERMAP_API_KEY: str = ""
    WEATHERAPI_API_KEY: str = ""
    WEATHER_FETCH_INTERVAL_MINUTES: int = 10

    # F4 — score at/above which an evacuation_recommendation is emitted to admins
    EVACUATION_RECOMMEND_MIN_SCORE: int = 70
    EVACUATION_RECOMMEND_COOLDOWN_SECONDS: int = 15 * 60

    DATABASE_URL: str
    SECRET_KEY: str
    IOT_API_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RESPONDER_TOKEN_EXPIRE_DAYS: int = 90
    GROQ_API_KEYS: Union[list[str], str]
    VAPID_PRIVATE_KEY: str
    VAPID_PUBLIC_KEY: str
    VAPID_CLAIM_EMAIL: str

    SENSOR_GRACE_PERIOD_MINUTES: int = 4
    SENSOR_WARNING_PERIOD_MINUTES: int = 8

    DETECTION_GRACE_PERIOD_MINUTES: int = 5
    DETECTION_WARNING_PERIOD_MINUTES: int = 10

    WEATHER_CONDITION_GRACE_PERIOD_MINUTES: int = 90  # 1.5 hours
    WEATHER_CONDITION_WARNING_PERIOD_MINUTES: int = 120  # 2 hours

    # SMS Gateway (Android phone running SMS Gateway API app)
    SMS_GATEWAY_URL: str = ""
    SMS_GATEWAY_API_KEY: str = ""
    SMS_GATEWAY_TIMEOUT_SECONDS: int = 30
    SMS_BULK_DELAY_SECONDS: float = 1.5

    FRONTEND_URLS: Union[list[str], str]

    SENTRY_DSN: str = ""
    ENVIRONMENT: str = "development"

    # runs implicitly before model initialization
    @field_validator("FRONTEND_URLS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v

    @field_validator("GROQ_API_KEYS", mode="before")
    @classmethod
    def parse_api_keys(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v

    @field_validator("UTC_OFFSET_HOURS")
    @classmethod
    def validate_utc_offset_hours(cls, v):
        if v < -12 or v > 14:
            raise ValueError("UTC_OFFSET_HOURS must be between -12 and 14")
        return v

    @property
    def APP_TIMEZONE(self) -> tzinfo:
        return timezone(timedelta(hours=self.UTC_OFFSET_HOURS))

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
