from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import SensorWebSocketResponse, WaterLevelStatus, SensorReadingForExport, SensorReadingForExportResponse
from app.schemas.sensor_reading import SensorReadingTrendResponse
from app.services.cache_service import cache_service
from app.models import SensorReading
from datetime import datetime, timezone, timedelta
from app.crud import sensor_reading_crud
from app.crud import sensor_device_crud
from app.core.state import fusion_state_manager
from app.core.config import settings
from app.schemas import SensorReadingResponse, SensorReadingCreate, SensorReadingPaginatedResponse, SensorDataRecordedResponse
from app.schemas import SensorReadingSummary, WaterLevelSummary, AlertSummary

DURATION_DELTAS = {
    '1_hour': timedelta(hours=1),
    '6_hours': timedelta(hours=6),
    '12_hours': timedelta(hours=12),
    '1_day': timedelta(days=1),
    '1_week': timedelta(weeks=1),
    '1_month': timedelta(days=30),
}

class SensorReadingService:

    async def get_items_paginated(self, 
                                db: AsyncSession, 
                                sensor_device_id: int,
                                page: int = 1, 
                                page_size: int = 10,
                                ) -> SensorReadingPaginatedResponse:

        db_items = await sensor_reading_crud.get_items_paginated(db=db, page=page, page_size=page_size, sensor_device_id=sensor_device_id)

        items = []
        # Process each item to determine status and change rate
        for item in db_items[:page_size]:
            status, change_rate = self._get_status_and_change_rate(item.water_level_cm, item.prev_water_level)

            items.append(SensorReadingResponse(
                id=item.id,
                timestamp=item.timestamp,
                water_level_cm=item.water_level_cm,
                status=status,
                change_rate=change_rate
            ))

        has_more = len(db_items) > page_size
        return SensorReadingPaginatedResponse(items=items[:page_size], has_more=has_more)


    async def get_readings_trend(self, db: AsyncSession, duration: str, sensor_device_id: int) -> SensorReadingTrendResponse:
    
        delta = DURATION_DELTAS.get(duration)
        if delta is None:
            raise ValueError(f"Invalid duration: {duration}")

        range_start = datetime.now(timezone.utc) - delta

        db_items = await sensor_reading_crud.get_readings_since(
            db=db, 
            since_datetime=range_start, 
            sensor_device_id=sensor_device_id
        )

        aggregation_intervals = {
            '1_hour': timedelta(minutes=1),
            '6_hours': timedelta(minutes=5),
            '12_hours': timedelta(minutes=10),
            '1_day': timedelta(minutes=30),
            '1_week': timedelta(hours=2),
            '1_month': timedelta(days=1),
        }
        
        interval = aggregation_intervals.get(duration, timedelta(minutes=1))
        
        return self._process_trend_data(db_items, interval, range_start)


    def _process_trend_data(self, items: list, interval: timedelta, start_time: datetime) -> SensorReadingTrendResponse:
        grouped_data = {}
        interval_seconds = interval.total_seconds()
        
        for item in items:
            timestamp = item.timestamp
            level = item.water_level_cm

            # Normalize timestamp to bucket interval
            ts_seconds = timestamp.timestamp()
            bucket_ts = ts_seconds - (ts_seconds % interval_seconds)
            
            if bucket_ts not in grouped_data:
                grouped_data[bucket_ts] = []
            grouped_data[bucket_ts].append(level)

        # Generate complete timeline
        # Align start_time to the grid
        start_ts = start_time.timestamp()
        current_bucket_ts = start_ts - (start_ts % interval_seconds)
        
        end_ts = datetime.now(timezone.utc).timestamp()
        
        labels = []
        levels = []

        # Iterate until we pass the current time
        while current_bucket_ts <= end_ts:
            if current_bucket_ts in grouped_data:
                avg_level = sum(grouped_data[current_bucket_ts]) / len(grouped_data[current_bucket_ts])
                levels.append(round(avg_level, 2))
            else:
                levels.append(0.0)
            
            dt = datetime.fromtimestamp(current_bucket_ts, tz=timezone.utc)
            labels.append(self._format_trend_label(dt, interval))
            
            current_bucket_ts += interval_seconds

        return SensorReadingTrendResponse(labels=labels, levels=levels)


    def _format_trend_label(self, dt: datetime, interval: timedelta) -> str:
        # Adjust to local time
        local_dt = dt.astimezone(timezone(timedelta(hours=settings.UTC_OFFSET_HOURS)))
        
        if interval >= timedelta(days=1):
            return local_dt.strftime("%d %b") 
        elif interval >= timedelta(hours=2):
            return local_dt.strftime("%d %b %H:%M")
        else:
            return local_dt.strftime("%H:%M")
    

    async def get_avialable_reading_days(self, db: AsyncSession, sensor_device_id: int) -> list[str]:
        return await sensor_reading_crud.get_available_reading_days(db=db, sensor_device_id=sensor_device_id)


    async def get_readings_for_export(self, 
                                    db: AsyncSession, 
                                    start_datetime: datetime, 
                                    end_datetime: datetime, 
                                    sensor_device_id: int
                                    ) -> SensorReadingForExportResponse:
        
        sensor_device_name = await sensor_device_crud.get_sensor_device_name(db=db, sensor_device_id=sensor_device_id)

        records = await sensor_reading_crud.get_readings_for_export(
            db=db, 
            start_datetime=start_datetime, 
            end_datetime=end_datetime,
            sensor_device_id=sensor_device_id
        )
        
        readings = []
        for record in records:

            status, change_rate = self._get_status_and_change_rate(record.water_level_cm, record.prev_water_level)

            readings.append(SensorReadingForExport(
                timestamp=self._format_datetime_for_excel(record.timestamp),
                water_level_cm=record.water_level_cm,
                status=status,
                change_rate=change_rate,
                signal_strength=record.signal_strength,
                signal_quality=self.get_signal_quality(record.signal_strength)
            ))
        
        return SensorReadingForExportResponse(
            readings=readings,
            sensor_device_name=sensor_device_name
        )


    async def record_reading(self, db: AsyncSession, obj_in: SensorReadingCreate) -> SensorDataRecordedResponse:
        from app.services.websocket_service import websocket_service
        
        # Verify sensor device exists
        if not await sensor_device_crud.get(db=db, id=obj_in.sensor_device_id):
            return SensorDataRecordedResponse(timestamp=datetime.now(timezone.utc), status="Error: Sensor device not found")

        # Get cached sensor installation height and calculate water level
        sensor_height = (await cache_service.get_sensor_config(db=db)).installation_height
        water_level_cm = sensor_height - obj_in.raw_distance_cm

        # Convert Pydantic model to dict
        data = obj_in.model_dump()

        # Create SensorReading DB object
        db_obj = SensorReading(**data)
        db_obj.water_level_cm = water_level_cm

        # Save to database
        db_reading: SensorReading = await sensor_reading_crud.create_record(db=db, db_obj=db_obj)

        # Run the calculations and prepare summary
        calculated_reading_summary = await self.calculate_record_summary(db=db, reading=db_reading)
        # Broadcast to connected WebSocket clients
        sensor_reading_summary_response = SensorWebSocketResponse(
            status = "success", 
            message = "Retrieved successfully",
            sensor_reading = calculated_reading_summary
        )

        await websocket_service.broadcast_update(
            update_type="sensor_update",
            data=sensor_reading_summary_response.model_dump(mode='json'),
            location_id=await cache_service.get_location_id_per_sensor_device(db=db, sensor_device_id=db_reading.sensor_device_id)
        )

        # Update fusion analysis state
        await fusion_state_manager.recalculate_water_level_score(
            water_level_status=WaterLevelStatus(
                water_level_cm=db_reading.water_level_cm,
                timestamp = db_reading.timestamp,
                critical_percentage = calculated_reading_summary.alert.percentage_of_critical,
                trend = calculated_reading_summary.water_level.trend,
                change_rate = calculated_reading_summary.water_level.change_rate
            ),
            location_id=await cache_service.get_location_id_per_sensor_device(db=db, sensor_device_id=db_reading.sensor_device_id)
        )

        # Return acknowledgment to sensor device
        return SensorDataRecordedResponse(timestamp=db_reading.created_at, status="Success: Reading recorded")


    async def calculate_record_summary(self, db: AsyncSession, reading: SensorReading) -> SensorReadingSummary:

        prev_reading = await sensor_reading_crud.get_previous_reading(db=db, before_timestamp=reading.timestamp)
        current_cm = reading.water_level_cm

        water_level_summary = self._calculate_water_level_summary(current_cm=current_cm, prev_reading=prev_reading)
        alert_summary = await self._calculate_alert_summary(current_cm=current_cm, db=db)
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
        sensor_config = await cache_service.get_sensor_config(db=db)
        
        current_cm = float(current_cm)
        warn = float(sensor_config.warning_threshold)
        crit = float(sensor_config.critical_threshold)

        level = "normal"
        if current_cm >= sensor_config.critical_threshold:
            level = "critical"
        elif current_cm >= sensor_config.warning_threshold:
            level = "warning"

        return AlertSummary(
            level=level,
            distance_to_warning_cm = round(warn - current_cm, 1),
            distance_from_warning_cm =  round(max(0, warn - current_cm), 1),
            distance_to_critical_cm = round(crit - current_cm, 1),
            distance_from_critical_cm = round(max(0, current_cm - crit), 1),
            percentage_of_critical=round((current_cm / crit) * 100, 1)
        )


    def get_signal_quality(self, signal_strength: int) -> str:
        if signal_strength >= -50:
            quality = 'excellent'
        elif signal_strength >= -60:
            quality = 'good'
        elif signal_strength >= -70:
            quality = 'fair'
        else:
            quality = 'poor'

        return quality
    

    def _get_status_and_change_rate(self, current_cm: float, prev_cm: float | None) -> tuple[str, float]:
        if prev_cm is None:
            return "stable", 0.0

        change_rate = round(current_cm - prev_cm, 2)

        if change_rate > 1:
            status = 'rising'
        elif change_rate < -1:
            status = 'falling'
        else:
            status = 'stable'

        return status, change_rate


    def _format_datetime_for_excel(self, dt: datetime) -> str:
        # Convert UTC to UTC+8 for display
        local_dt = dt.astimezone(timezone(timedelta(hours=settings.UTC_OFFSET_HOURS)))
        return local_dt.strftime("%Y-%m-%d %H:%M")


sensor_reading_service = SensorReadingService()