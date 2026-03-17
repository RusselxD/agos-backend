import base64
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from app.schemas import CameraStatus
from app.services.camera_status_service import camera_status_service
from app.services.ml_service import ml_service
from app.core.config import settings
from app.core.rate_limiter import limiter
from app.core.ws_manager import ws_manager
from app.api.v1.dependencies import require_iot_api_key
from app.core.database import get_db
from app.crud import camera_device_crud
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/status", response_model=CameraStatus)
async def get_camera_status(location_id: int = Query(...)):
    """Return whether the camera for a location is actively sending frames."""
    return camera_status_service.get_status(location_id)


@router.post("/upload-image")
@limiter.limit("35/minute")
async def upload_camera_image(
    request: Request,
    location_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_iot_api_key),
):
    """Receive an image from the camera, broadcast it to WebSocket clients, and run ML inference."""
    camera_device_id = await camera_device_crud.get_id_by_location(
        db=db, location_id=location_id
    )
    if camera_device_id is None:
        raise HTTPException(
            status_code=403,
            detail="Device is not authorized for this location_id",
        )

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read(settings.MAX_IMAGE_UPLOAD_BYTES + 1)
    if len(image_bytes) > settings.MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds maximum allowed size")

    camera_status_service.record_frame(location_id)

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    await ws_manager.broadcast_to_location(
        {
            "type": "camera_update",
            "data": {
                "image": encoded,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
        location_id=location_id,
    )

    await ml_service.process_frame_bytes(
        image_bytes=image_bytes,
        camera_device_id=camera_device_id,
        location_id=location_id,
    )

    return {"status": "ok"}
