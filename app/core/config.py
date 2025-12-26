from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pydantic import field_validator
from typing import Union

class Settings(BaseSettings):

    FFMPEG_PATH: str = "ffmpeg"  # Default to 'ffmpeg' in PATH

    # Stream Configuration
    STREAM_URL: str
    HLS_OUTPUT_DIR: str = "app/storage/hls_output"
    FRAMES_OUTPUT_DIR: str = "app/storage/captured_frames"
    FRAME_CAPTURE_INTERVAL_SECONDS: int = 60 * 2  # seconds
    FRAME_WIDTH: int = 640
    FRAME_HEIGHT: int = 360
    FRAME_QUALITY: int = 3  # 1-31, lower is better

    # HLS Settings
    HLS_TIME: int = 6  # seconds per segment (Increased to prevent keyframe mismatch)
    HLS_LIST_SIZE: int = 10  # number of segments in playlist

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 2

    SENSOR_GRACE_PERIOD_MINUTES: int = 4
    SENSOR_WARNING_PERIOD_MINUTES: int = 8

    DETECTION_GRACE_PERIOD_MINUTES: int = 5
    DETECTION_WARNING_PERIOD_MINUTES: int = 10

    FRONTEND_URLS: Union[list[str], str] = ["http://localhost:5173"]

    #runs implicitly before model initialization
    @field_validator('FRONTEND_URLS', mode='before')
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(',')]
        return v

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()