from datetime import datetime, timezone
from app.core.config import settings


class CameraStatusService:
    """
    Tracks the last time a frame was received per location.
    A camera is considered online if a frame arrived within
    2 × FRAME_CAPTURE_INTERVAL_SECONDS.
    """

    def __init__(self):
        self._last_seen: dict[int, datetime] = {}

    def record_frame(self, location_id: int) -> None:
        self._last_seen[location_id] = datetime.now(timezone.utc)

    def get_status(self, location_id: int) -> dict:
        last_seen = self._last_seen.get(location_id)
        is_online = False
        if last_seen is not None:
            elapsed = (datetime.now(timezone.utc) - last_seen).total_seconds()
            is_online = elapsed < settings.FRAME_CAPTURE_INTERVAL_SECONDS * 2
        return {
            "is_online": is_online,
            "last_seen": last_seen,
        }


camera_status_service = CameraStatusService()
