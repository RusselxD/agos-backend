from app.schemas import ModelWebSocketResponse, WeatherWebSocketResponse, SensorWebSocketResponse, FusionWebSocketResponse
from app.schemas import WeatherConditionResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.sensor_reading_service import sensor_reading_service
from app.services.weather_service import weather_service
from fastapi import WebSocket
from app.models.sensor_readings import SensorReading
from app.crud.sensor_reading import sensor_reading as sensor_reading_crud
from app.crud.model_readings import model_readings as model_readings_crud
from app.crud.weather import weather as weather_crud
from datetime import timedelta, datetime, timezone
from app.core.config import settings
from app.core.ws_manager import ws_manager
from app.core.state import fusion_analysis_state

class WebSocketService:

    async def send_initial_data(self, websocket: WebSocket, db: AsyncSession):
        initial_sensor_reading_data = await self._get_initial_sensor_reading_data(db=db)
        await websocket.send_json({
            "type": "sensor_update",
            "data": initial_sensor_reading_data.model_dump(mode='json')
        })

        initial_model_reading_data = await self._get_initial_model_reading_data(db=db)
        await websocket.send_json({
            "type": "blockage_detection_update",
            "data": initial_model_reading_data.model_dump(mode='json')
        })

        initial_weather_condition_data = await self._get_initial_weather_data(db=db)
        await websocket.send_json({
            "type": "weather_update",
            "data": initial_weather_condition_data.model_dump(mode='json')
        })

        initial_fusion_analysis_data = await self._get_initial_fusion_analysis_data()
        await websocket.send_json({
            "type": "fusion_analysis_update",
            "data": initial_fusion_analysis_data.model_dump(mode='json')
        })

    async def _get_initial_sensor_reading_data(self, db: AsyncSession, sensor_id: int = 1) -> SensorWebSocketResponse:
        latest_sensor_reading: SensorReading = await sensor_reading_crud.get_latest_reading(db=db, sensor_id=sensor_id)

        # If no reading found or beyond the warning period, send error message
        if not latest_sensor_reading or (latest_sensor_reading.timestamp < datetime.now(timezone.utc) - timedelta(minutes=settings.SENSOR_WARNING_PERIOD_MINUTES)):
            return SensorWebSocketResponse(
                status="error", 
                message="No recent sensor data available.",
                sensor_reading=None
            )

        sensor_reading = await sensor_reading_service.calculate_record_summary(db=db, reading=latest_sensor_reading)

        # Check if the latest reading is stale (beyond the grace period but within warning period)
        if latest_sensor_reading.timestamp < datetime.now(timezone.utc) - timedelta(minutes=settings.SENSOR_GRACE_PERIOD_MINUTES):
            return SensorWebSocketResponse(
                status="warning", 
                message="Latest sensor data is stale.",
                sensor_reading=sensor_reading
            )

        # Normal case: recent data available
        return SensorWebSocketResponse(
            status="success", 
            message="Retrieved successfully",
            sensor_reading=sensor_reading
        )

    async def _get_initial_model_reading_data(self, db: AsyncSession) -> ModelWebSocketResponse:
        latest_model_reading = await model_readings_crud.get_latest_reading(db=db)

        # If no reading found or beyond the warning period, send error message
        if not latest_model_reading or (latest_model_reading["timestamp"] < datetime.now(timezone.utc) - timedelta(minutes=settings.SENSOR_WARNING_PERIOD_MINUTES)):
            return ModelWebSocketResponse(
                status="error", 
                message="No recent blockage detection data available.",
                blockage_status=None
            )

        # Check if the latest reading is stale (beyond the grace period but within warning period)
        if latest_model_reading["timestamp"] < datetime.now(timezone.utc) - timedelta(minutes=settings.DETECTION_GRACE_PERIOD_MINUTES):
            return ModelWebSocketResponse(
                status="warning", 
                message="Latest blockage detection is stale.",
                blockage_status=latest_model_reading["status"]
            )

        return ModelWebSocketResponse(
            status="success", 
            message="Retrieved successfully",
            blockage_status=latest_model_reading["status"]
        )

    async def _get_initial_weather_data(self, db: AsyncSession, sensor_id: int = 1) -> WeatherWebSocketResponse:
        latest_weather_condition = await weather_crud.get_latest_weather(db=db, sensor_id=sensor_id)

        # If no reading found or beyond the warning period, send error message
        if not latest_weather_condition or (latest_weather_condition["created_at"] < datetime.now(timezone.utc) - timedelta(minutes=settings.WEATHER_CONDITION_WARNING_PERIOD_MINUTES)):
            return WeatherWebSocketResponse(
                status="error",
                message="No recent weather data available.",
                weather_condition=None
            )
        
        # Prepare weather condition summary
        weather_condition: WeatherConditionResponse = weather_service.get_weather_summary(
            created_at=latest_weather_condition["created_at"],
            weather_code=latest_weather_condition["weather_code"],
            precipitation_mm=latest_weather_condition["precipitation_mm"])
        
        # Check if the latest reading is stale (beyond the grace period but within warning period)
        if latest_weather_condition["created_at"] < datetime.now(timezone.utc) - timedelta(minutes=settings.WEATHER_CONDITION_GRACE_PERIOD_MINUTES):
            return WeatherWebSocketResponse(
                status="warning",
                message="Latest weather data is stale.",
                weather_condition=weather_condition
            )
        
        # Normal case: recent data available
        return WeatherWebSocketResponse(
            status="success",
            message="Retrieved successfully",
            weather_condition=weather_condition
        )

    async def _get_initial_fusion_analysis_data(self) -> FusionWebSocketResponse:
        fusion_analysis_data = fusion_analysis_state.fusion_analysis
        return FusionWebSocketResponse(
            status="success",
            message="Retrieved successfully",
            fusion_analysis=fusion_analysis_data
        )

    async def broadcast_update(self, update_type: str, data: dict):
        await ws_manager.broadcast({
            "type": update_type,
            "data": data
        })

websocket_service = WebSocketService()