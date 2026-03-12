import json
import base64
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends
from app.core.ws_manager import ws_manager
from app.services.websocket_service import websocket_service
from app.services.ml_service import ml_service
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):

    location_id = websocket.query_params.get("location_id")

    await websocket.accept()

    if not location_id:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Missing location_id"
        )
        return

    # Convert location_id to int
    try:
        location_id = int(location_id)
    except ValueError:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid location_id"
        )
        return

    # Add the WebSocket connection to the manager
    await ws_manager.connect(websocket=websocket, location_id=location_id)

    # Send initial data to the connected client
    await websocket_service.send_initial_data(
        websocket=websocket, db=db, location_id=location_id
    )

    try:
        while True:
            await websocket.receive_text()  # Keep the connection alive
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket=websocket, location_id=location_id)


@router.websocket("/ws/rpi")
async def rpi_websocket_endpoint(websocket: WebSocket):
    camera_device_id = websocket.query_params.get("camera_device_id")
    location_id = websocket.query_params.get("location_id")

    await websocket.accept()

    if not camera_device_id or not location_id:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing camera_device_id or location_id",
        )
        return

    try:
        camera_device_id = int(camera_device_id)
        location_id = int(location_id)
    except ValueError:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid camera_device_id or location_id",
        )
        return

    await websocket.send_json(
        {
            "type": "connected",
            "camera_device_id": camera_device_id,
            "location_id": location_id,
        }
    )
    print(f"📷 RPi connected — cam={camera_device_id}, loc={location_id}")

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            if message["type"] != "websocket.receive":
                continue

            if message.get("bytes"):
                image_bytes: bytes = message["bytes"]

                # Broadcast the raw frame immediately to all frontend clients
                # so they see a live image feed (rapidly updating picture).
                # This happens before ML inference so the UI stays responsive.
                try:
                    await ws_manager.broadcast_to_location(
                        {
                            "type": "camera_update",
                            "data": {
                                "image": base64.b64encode(image_bytes).decode("utf-8"),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        },
                        location_id=location_id,
                    )
                except Exception as e:
                    logger.error(
                        "broadcast_to_location failed for location_id=%s: %s",
                        location_id,
                        e,
                        exc_info=True,
                    )

                # Run ML inference and send result back to the RPi
                try:
                    result = await ml_service.process_frame_bytes(
                        image_bytes=image_bytes,
                        camera_device_id=camera_device_id,
                        location_id=location_id,
                    )
                    await websocket.send_json(
                        {"type": "frame_processed", "data": result}
                    )
                except Exception:
                    logger.exception(
                        "ML inference failed for camera_device_id=%s, location_id=%s",
                        camera_device_id,
                        location_id,
                    )
                    await websocket.send_json(
                        {"type": "error", "message": "Internal server error"}
                    )

            # ── Text frame: control messages (ping, etc.) ────────────────────
            elif message.get("text"):
                try:
                    data = json.loads(message["text"])
                    if data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except (json.JSONDecodeError, Exception):
                    pass

    except WebSocketDisconnect:
        print(f"📷 RPi disconnected — cam={camera_device_id}, loc={location_id}")
