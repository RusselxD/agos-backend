from app.schemas.reading_summary_response.model_reading import ModelReadingSummary
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.sensor_reading_service import sensor_reading_service
from fastapi import WebSocket
from app.models.sensor_readings import SensorReading
from app.crud.sensor_reading import sensor_reading as sensor_reading_crud
from app.crud.model_readings import model_readings as model_readings_crud
from datetime import timedelta, datetime, timezone
from app.schemas.reading_summary_response.sensor_reading_summary import SensorReadingSummaryResponse
from app.core.config import settings

class WebSocketService:

    async def send_initial_data(self, websocket: WebSocket, db: AsyncSession):
        initial_sensor_reading_data = await self._get_initial_sensor_reading_data(db)
        await websocket.send_json({
            "type": "sensor_update",
            "data": initial_sensor_reading_data.model_dump(mode='json')
        })

        initial_model_reading_data = await self._get_initial_model_reading_data(db)
        await websocket.send_json({
            "type": "blockage_detection_update",
            "data": initial_model_reading_data.model_dump(mode='json')
        })

    async def _get_initial_sensor_reading_data(self, db: AsyncSession) -> SensorReadingSummaryResponse:
        latest_reading: SensorReading = await sensor_reading_crud.get_latest_reading(db)

        # If no reading found or beyond the warning period, send error message
        if not latest_reading or (latest_reading.timestamp < datetime.now(timezone.utc) - timedelta(minutes=settings.SENSOR_WARNING_PERIOD_MINUTES)):
            return SensorReadingSummaryResponse(
                status="error", 
                message="No recent sensor data available.",
                sensor_reading=None
            )

        # Check if the latest reading is stale (beyond the grace period but within warning period)
        if latest_reading.timestamp < datetime.now(timezone.utc) - timedelta(minutes=settings.SENSOR_GRACE_PERIOD_MINUTES):
            return SensorReadingSummaryResponse(
                status="warning", 
                message="Latest sensor data is stale.",
                sensor_reading = await sensor_reading_service.calculate_record_summary(db, latest_reading)
            )

        # Normal case: recent data available
        return SensorReadingSummaryResponse(
            status = "success", 
            message = "Retrieved successfully",
            sensor_reading = await sensor_reading_service.calculate_record_summary(db, latest_reading)
        )

    async def _get_initial_model_reading_data(self, db: AsyncSession) -> ModelReadingSummary:
        latest_reading = await model_readings_crud.get_latest_reading(db)

        # If no reading found or beyond the warning period, send error message
        if not latest_reading or (latest_reading["timestamp"] < datetime.now(timezone.utc) - timedelta(minutes=settings.SENSOR_WARNING_PERIOD_MINUTES)):
            return ModelReadingSummary(
                status="error", 
                message="No recent blockage detection data available.",
                blockage_status=None
            )

        # Check if the latest reading is stale (beyond the grace period but within warning period)
        if latest_reading["timestamp"] < datetime.now(timezone.utc) - timedelta(minutes=settings.DETECTION_GRACE_PERIOD_MINUTES):
            return ModelReadingSummary(
                status="warning", 
                message="Latest blockage detection is stale.",
                blockage_status=latest_reading["status"]
            )

        return ModelReadingSummary(
                status="success", 
                message="Retrieved successfully",
                blockage_status=latest_reading["status"]
            )

web_socket_service = WebSocketService()