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
        # One most-recent encoded frame per monitored location. This is bounded
        # in-memory state (not history) and is replaced on every incoming frame.
        self._latest_frames: dict[int, dict] = {}

    def record_frame(self, location_id: int, encoded_image: str | None = None) -> None:
        received_at = datetime.now(timezone.utc)
        self._last_seen[location_id] = received_at
        if encoded_image is not None:
            self._latest_frames[location_id] = {
                "image": encoded_image,
                "timestamp": received_at,
            }

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

    def get_latest_frame(self, location_id: int) -> dict | None:
        return self._latest_frames.get(location_id)


camera_status_service = CameraStatusService()
