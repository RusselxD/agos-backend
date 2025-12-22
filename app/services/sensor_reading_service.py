from sqlalchemy.ext.asyncio import AsyncSession
from app.services.cache_service import cache_service
from app.models.sensor_readings import SensorReading
from datetime import datetime, timezone
from app.core.ws_manager import ws_manager
from app.crud.sensor_reading import sensor_reading as sensor_reading_crud
from app.crud.sensor_devices import sensor_device as sensor_device_crud
from app.schemas.sensor_reading import AlertSummary, SensorReadingSummaryResponse, WaterLevelSummary, SensorReadingSummary, SensorReadingResponse, SensorReadingCreate, SensorReadingPaginatedResponse, SensorDataRecordedResponse

class SensorReadingService:

    async def get_items_paginated(self, db: AsyncSession, page: int = 1, page_size: int = 10) -> SensorReadingPaginatedResponse:

        db_items = await sensor_reading_crud.get_items_paginated(db, page=page, page_size=page_size)

        items = []
        # Process each item to determine status and change rate
        for item in db_items[:page_size]:
            if item.prev_water_level is None:
                change_rate = 0
                status = "stable"
            else:
                change_rate = round(item.water_level_cm - item.prev_water_level, 2)
            
                if change_rate > 1:
                    status = 'rising'
                elif change_rate < -1:
                    status = 'falling'
                else:
                    status = 'stable'

            items.append(SensorReadingResponse(
                id=item.id,
                timestamp=item.timestamp,
                water_level_cm=item.water_level_cm,
                status=status,
                change_rate=change_rate
            ))

        has_more = len(db_items) > page_size
        return SensorReadingPaginatedResponse(items=items[:page_size], has_more=has_more)

    async def record_reading(self, db: AsyncSession, obj_in: SensorReadingCreate) -> SensorDataRecordedResponse:
        
        # Verify sensor device exists
        if not await sensor_device_crud.get(db, id=obj_in.sensor_id):
            return SensorDataRecordedResponse(timestamp=datetime.now(timezone.utc), status="Error: Sensor device not found")

        # Get cached sensor installation height and calculate water level
        sensor_height = (await cache_service.get_sensor_config(db)).installation_height
        water_level_cm = sensor_height - obj_in.raw_distance_cm

        # Convert Pydantic model to dict
        data = obj_in.model_dump()

        # Create SensorReading DB object
        db_obj = SensorReading(**data)
        db_obj.water_level_cm = water_level_cm

        # Save to database
        db_reading = await sensor_reading_crud.create_record(
            db, db_obj=db_obj,
        )

        # Run the calculations and prepare summary
        # Broadcast to connected WebSocket clients
        calculated_reading_summary = await self.calculate_record_summary(db, db_reading)

        sensor_reading_summary_response = SensorReadingSummaryResponse(
            status = "success", 
            message = "Retrieved successfully",
            sensor_reading = calculated_reading_summary
        )

        await ws_manager.broadcast({
            "type": "sensor_update",
            "data": sensor_reading_summary_response.model_dump(mode='json')
        })

        return SensorDataRecordedResponse(timestamp=db_reading.created_at, status="Success: Reading recorded")

    async def calculate_record_summary(self, db: AsyncSession, reading: SensorReading) -> SensorReadingSummary:

        prev_reading = await sensor_reading_crud.get_previous_reading(db, reading.timestamp)
        current_cm = reading.water_level_cm

        water_level_summary = self._calculate_water_level_summary(current_cm, prev_reading)
        alert_summary = await self._calculate_alert_summary(current_cm, db)

        return SensorReadingSummary(
            timestamp = reading.timestamp,
            water_level = water_level_summary,
            alert = alert_summary
        )

    def _calculate_water_level_summary(self, current_cm: float, prev_reading: SensorReading | None) -> WaterLevelSummary:

        change_rate = 0.0
        if prev_reading:
            change_rate = round(current_cm - prev_reading.water_level_cm, 2)

        trend = "stable"
        if change_rate > 1:
            trend = "rising"
        elif change_rate < -1:
            trend = "falling"

        return WaterLevelSummary(
            current_cm = current_cm,
            change_rate = change_rate,
            trend = trend
        )

    async def _calculate_alert_summary(self, current_cm: float, db: AsyncSession) -> AlertSummary:
        sensor_config = await cache_service.get_sensor_config(db)\
        
        current_cm = float(current_cm)
        warn = float(sensor_config.warning_threshold)
        crit = float(sensor_config.critical_threshold)

        print(current_cm)
        print(warn)

        level = "normal"
        if current_cm >= sensor_config.critical_threshold:
            level = "critical"
        elif current_cm >= sensor_config.warning_threshold:
            level = "warning"

        return AlertSummary(
            level=level,
            distance_to_warning_cm = round(max(0, current_cm - warn), 1),
            distance_from_warning_cm =  round(max(0, warn - current_cm), 1),
            distance_to_critical_cm = round(crit - current_cm, 1),
            distance_from_critical_cm = round(max(0, current_cm - crit), 1),
            percentage_of_critical=round((current_cm / crit) * 100, 1)
        )

    """
    Record multiple sensor readings in bulk.
    FOR DEVELOPMENT USE ONLY. WILL BE REMOVED IN PRODUCTION.
    """
    async def record_bulk_readings(self, db: AsyncSession, objs_in: list[SensorReadingCreate]) -> SensorDataRecordedResponse:
        sensor_height = (await cache_service.get_sensor_config(db)).installation_height
        
        # Prepare DB objects
        db_objs = []
        for obj_in in objs_in:
            obj_in_data = obj_in.model_dump()
            db_obj = SensorReading(**obj_in_data)
            db_obj.water_level_cm = sensor_height - db_obj.raw_distance_cm
            db_objs.append(db_obj)
        
        # Save to database
        await sensor_reading_crud.create_bulk_record(db, db_objs=db_objs)

        return SensorDataRecordedResponse(timestamp=datetime.now(timezone.utc), status="Success: Bulk Reading recorded")

sensor_reading_service = SensorReadingService()