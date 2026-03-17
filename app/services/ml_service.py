import random
from io import BytesIO
from datetime import datetime, timezone
from app.core.cloudinary import upload_image
from app.crud import model_readings_crud
from app.schemas import ModelReadingCreate
from app.core.database import AsyncSessionLocal
from app.services.websocket_service import websocket_service
from app.models.data_sources.model_readings import ModelReadings
from app.schemas import ModelWebSocketResponse
from app.core.state import fusion_state_manager
from app.schemas import BlockageStatus
from app.core.config import settings


class MLService:
    """
    Runs ML inference on JPEG frames received directly from the camera.
    Throttled per camera device to at most once per FRAME_CAPTURE_INTERVAL_SECONDS.
    """

    def __init__(self):
        # Per-camera last-processed timestamp to enforce the capture interval
        self._last_processed: dict[int, datetime] = {}

    async def process_frame_bytes(
        self,
        image_bytes: bytes,
        camera_device_id: int,
        location_id: int,
    ) -> dict:
        """
        Run inference on an in-memory JPEG image.
        Skips silently if called before the interval has elapsed for this camera.
        """
        now = datetime.now(timezone.utc)
        last = self._last_processed.get(camera_device_id)
        if last is not None:
            elapsed = (now - last).total_seconds()
            if elapsed < settings.FRAME_CAPTURE_INTERVAL_SECONDS - 5:
                return {}

        self._last_processed[camera_device_id] = now

        # Simulate model prediction
        prediction = random.choices(
            ["clear", "partial", "blocked"], weights=[0.7, 0.2, 0.1], k=1
        )[0]
        percentage = round(random.uniform(0.75, 0.99), 2)
        debris_count = random.randint(0, 20)

        public_id = f"rpi_{camera_device_id}_{int(now.timestamp())}"
        upload_result = await upload_image(BytesIO(image_bytes), filename=public_id)

        image_url = f"rpi_frame_{public_id}.jpg"
        if upload_result:
            image_url = upload_result["secure_url"]

        async with AsyncSessionLocal() as db:
            obj_in = ModelReadingCreate(
                camera_device_id=camera_device_id,
                image_path=image_url,
                timestamp=now,
                blockage_percentage=percentage * 100,
                blockage_status=prediction,
                total_debris_count=debris_count,
            )
            db_obj: ModelReadings = await model_readings_crud.create_and_return(
                db=db, obj_in=obj_in
            )

        blockage_reading = ModelWebSocketResponse(
            status="success",
            message="Retrieved successfully",
            blockage_status=prediction,
        )

        await websocket_service.broadcast_update(
            update_type="blockage_detection_update",
            data=blockage_reading.model_dump(mode="json"),
            location_id=location_id,
        )

        await fusion_state_manager.recalculate_visual_status_score(
            blockage_status=BlockageStatus(status=prediction, timestamp=db_obj.timestamp),
            location_id=location_id,
        )

        return blockage_reading.model_dump(mode="json")


ml_service = MLService()
