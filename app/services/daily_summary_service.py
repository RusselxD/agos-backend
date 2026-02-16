from datetime import date, datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.schemas import DailySummaryResponse
from app.models.data_sources.sensor_reading import SensorReading
from app.models.data_sources.model_readings import ModelReadings
from app.models.data_sources.weather import Weather
from app.crud.daily_summary import daily_summary_crud
from app.services.cache_service import cache_service


BLOCKAGE_SEVERITY = {"clear": 0, "partial": 1, "blocked": 2}


class DailySummaryService:

    async def generate_summary_for_location(self, db: AsyncSession, location_id: int, target_date: date) -> dict:
        """Generate daily summary data for a single location."""
        
        # Define time range for the target date (00:00:00 to 23:59:59.999999 UTC)
        start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_day = start_of_day + timedelta(days=1)
        
        # Get device IDs and sensor config once
        device_ids = await cache_service.get_device_ids_per_location(db, location_id)
        sensor_config = await cache_service.get_sensor_config(db)
        critical_level = sensor_config.critical_water_level_cm if sensor_config else 100.0
        
        # Fetch all data ONCE
        sensor_readings = []
        model_readings = []
        weather_readings = []
        
        if device_ids and device_ids.sensor_device_id:
            result = await db.execute(
                select(SensorReading).where(
                    and_(
                        SensorReading.sensor_device_id == device_ids.sensor_device_id,
                        SensorReading.timestamp >= start_of_day,
                        SensorReading.timestamp < end_of_day
                    )
                ).order_by(SensorReading.timestamp)
            )
            sensor_readings = result.scalars().all()
        
        if device_ids and device_ids.camera_device_id:
            result = await db.execute(
                select(ModelReadings).where(
                    and_(
                        ModelReadings.camera_device_id == device_ids.camera_device_id,
                        ModelReadings.timestamp >= start_of_day,
                        ModelReadings.timestamp < end_of_day
                    )
                ).order_by(ModelReadings.timestamp)
            )
            model_readings = result.scalars().all()
        
        result = await db.execute(
            select(Weather).where(
                and_(
                    Weather.location_id == location_id,
                    Weather.created_at >= start_of_day,
                    Weather.created_at < end_of_day
                )
            ).order_by(Weather.created_at)
        )
        weather_readings = result.scalars().all()
        
        # Build summary from fetched data
        summary_data = {}
        
        if sensor_readings:
            summary_data.update(self._extract_water_level_summary(sensor_readings))
        
        if model_readings:
            summary_data.update(self._extract_model_readings_summary(model_readings))
        
        if weather_readings:
            summary_data.update(self._extract_weather_summary(weather_readings))
        
        # Calculate risk scores from already-fetched data
        risk_summary = self._calculate_risk_scores(
            sensor_readings, model_readings, weather_readings, critical_level
        )
        summary_data.update(risk_summary)
        
        return summary_data


    def _extract_water_level_summary(self, readings: list) -> dict:
        """Extract min/max water levels from pre-fetched readings."""
        min_reading = min(readings, key=lambda r: r.water_level_cm)
        max_reading = max(readings, key=lambda r: r.water_level_cm)
        
        return {
            "min_water_level_cm": float(min_reading.water_level_cm),
            "min_water_timestamp": min_reading.timestamp,
            "max_water_level_cm": float(max_reading.water_level_cm),
            "max_water_timestamp": max_reading.timestamp,
        }


    def _extract_model_readings_summary(self, readings: list) -> dict:
        """Extract debris and blockage stats from pre-fetched readings."""
        min_debris = min(readings, key=lambda r: r.total_debris_count)
        max_debris = max(readings, key=lambda r: r.total_debris_count)
        least_severe = min(readings, key=lambda r: BLOCKAGE_SEVERITY.get(r.blockage_status, 0))
        most_severe = max(readings, key=lambda r: BLOCKAGE_SEVERITY.get(r.blockage_status, 0))
        
        return {
            "min_debris_count": min_debris.total_debris_count,
            "min_debris_timestamp": min_debris.timestamp,
            "max_debris_count": max_debris.total_debris_count,
            "max_debris_timestamp": max_debris.timestamp,
            "least_severe_blockage": least_severe.blockage_status,
            "most_severe_blockage": most_severe.blockage_status,
        }


    def _extract_weather_summary(self, readings: list) -> dict:
        """Extract precipitation stats from pre-fetched readings."""
        min_precip = min(readings, key=lambda r: r.precipitation_mm)
        max_precip = max(readings, key=lambda r: r.precipitation_mm)
        most_severe_code = max(r.weather_code for r in readings)
        
        return {
            "min_precipitation_mm": min_precip.precipitation_mm,
            "min_precip_timestamp": min_precip.created_at,
            "max_precipitation_mm": max_precip.precipitation_mm,
            "max_precip_timestamp": max_precip.created_at,
            "most_severe_weather_code": most_severe_code,
        }


    def _calculate_risk_scores(
        self,
        sensor_readings: list,
        model_readings: list,
        weather_readings: list,
        critical_level: float
    ) -> dict:
        """Calculate min/max risk scores from pre-fetched data."""
        if not sensor_readings and not model_readings and not weather_readings:
            return {}
        
        min_score = float('inf')
        max_score = float('-inf')
        min_timestamp = None
        max_timestamp = None
        
        # Use sensor readings as primary timeline
        if sensor_readings:
            for sensor in sensor_readings:
                score = self._calc_water_score(float(sensor.water_level_cm), critical_level)
                score += self._find_and_calc_blockage_score(model_readings, sensor.timestamp)
                score += self._find_and_calc_weather_score(weather_readings, sensor.timestamp)
                
                if score < min_score:
                    min_score, min_timestamp = score, sensor.timestamp
                if score > max_score:
                    max_score, max_timestamp = score, sensor.timestamp
        
        # Fallback to model readings timeline
        elif model_readings:
            for model in model_readings:
                score = self._calc_blockage_score(model.blockage_status)
                score += self._find_and_calc_weather_score(weather_readings, model.timestamp)
                
                if score < min_score:
                    min_score, min_timestamp = score, model.timestamp
                if score > max_score:
                    max_score, max_timestamp = score, model.timestamp
        
        # Fallback to weather-only
        elif weather_readings:
            for weather in weather_readings:
                score = self._calc_weather_score(weather.precipitation_mm)
                
                if score < min_score:
                    min_score, min_timestamp = score, weather.created_at
                if score > max_score:
                    max_score, max_timestamp = score, weather.created_at
        
        if min_score == float('inf'):
            return {}
        
        return {
            "min_risk_score": min_score,
            "max_risk_score": max_score,
            "min_risk_timestamp": min_timestamp,
            "max_risk_timestamp": max_timestamp,
        }


    def _calc_water_score(self, water_level_cm: float, critical_level: float) -> int:
        """Calculate water level contribution to risk score."""
        critical_pct = (water_level_cm / critical_level) * 100
        if critical_pct < 50:
            return 10
        elif critical_pct < 75:
            return 20
        elif critical_pct < 90:
            return 30
        return 45


    def _calc_blockage_score(self, status: str) -> int:
        """Calculate blockage contribution to risk score."""
        if status == "blocked":
            return 35
        elif status == "partial":
            return 20
        return 0


    def _calc_weather_score(self, precipitation_mm: float) -> int:
        """Calculate weather contribution to risk score."""
        if precipitation_mm >= 7.5:
            return 20
        elif precipitation_mm >= 2.55:
            return 15
        elif precipitation_mm >= 1:
            return 8
        return 0


    def _find_and_calc_blockage_score(self, model_readings: list, target_time: datetime, max_gap_minutes: int = 15) -> int:
        """Find closest model reading and calculate blockage score."""
        closest = self._find_closest(model_readings, target_time, 'timestamp', max_gap_minutes)
        return self._calc_blockage_score(closest.blockage_status) if closest else 0


    def _find_and_calc_weather_score(self, weather_readings: list, target_time: datetime, max_gap_minutes: int = 15) -> int:
        """Find closest weather reading and calculate weather score."""
        closest = self._find_closest(weather_readings, target_time, 'created_at', max_gap_minutes)
        return self._calc_weather_score(closest.precipitation_mm) if closest else 0


    def _find_closest(self, readings: list, target_time: datetime, time_attr: str, max_gap_minutes: int):
        """Find reading closest to target_time within max_gap_minutes."""
        if not readings:
            return None
        
        max_gap = timedelta(minutes=max_gap_minutes)
        closest = None
        min_diff = max_gap
        
        for r in readings:
            diff = abs(getattr(r, time_attr) - target_time)
            if diff < min_diff:
                min_diff = diff
                closest = r
        
        return closest


    async def generate_all_summaries(self, db: AsyncSession, target_date: date) -> int:
        """Generate summaries for all locations. Returns count of summaries created."""
        location_ids = await cache_service.get_all_location_ids(db)
        created_count = 0
        
        for loc_id in location_ids:
            # Check if summary already exists
            existing = await daily_summary_crud.get_by_location_and_date(db, loc_id, target_date)
            if existing:
                print(f"📋 Summary already exists for location {loc_id} on {target_date}, skipping.")
                continue
            
            summary_data = await self.generate_summary_for_location(db, loc_id, target_date)
            await daily_summary_crud.create_daily_summary(db, loc_id, target_date, summary_data)
            created_count += 1
            print(f"✅ Created daily summary for location {loc_id} on {target_date}")
        
        return created_count


    async def get_daily_summaries(self, db: AsyncSession, location_id: int, start_date: datetime, end_date: datetime) -> list[DailySummaryResponse]:
        """Get daily summaries for a location within a datetime range."""
        db_summaries = await daily_summary_crud.get_daily_summaries(db=db, location_id=location_id, start_date=start_date, end_date=end_date)
        return [DailySummaryResponse.model_validate(summary) for summary in db_summaries]


    async def get_available_summary_days(self, db: AsyncSession, location_id: int) -> list[datetime]:
        """Get list of dates for which summaries are available for a location."""
        return await daily_summary_crud.get_available_summary_days(db=db, location_id=location_id)


daily_summary_service = DailySummaryService()
