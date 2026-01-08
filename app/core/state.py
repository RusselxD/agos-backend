from app.schemas import FusionData, BlockageStatus, WaterLevelStatus, WeatherStatus, FusionAnalysisData, AlertThresholdsResponse
from app.schemas.reading_summary_response import FusionWebSocketResponse
from app.services.cache_service import cache_service

class FusionAnalysisState:
    def __init__(self):
        self.fusion_analysis: FusionAnalysisData | None = None
        
        self.fusion_data: FusionData = FusionData(
            alert_name="Normal",
            combined_risk_score=0,
            triggered_conditions=[]
        )
        self.blockage_status: BlockageStatus | None = None
        self.water_level_status: WaterLevelStatus | None = None
        self.weather_status: WeatherStatus | None = None

    async def broadcast_fusion_analysis(self):
        from app.services import websocket_service

        fusion_websocket_response = FusionWebSocketResponse(
            status="success",
            message="Retrieved successfully",
            fusion_analysis=self.fusion_analysis
        )

        await websocket_service.broadcast_update(
            "fusion_analysis_update", 
            fusion_websocket_response.model_dump(mode='json')
        )

    async def load_initial_state(self, db):
        """
        Loads the latest data from the database upon server startup.
        Verifies if the data is recent enough to be considered valid for fusion analysis.
        """
        from app.crud.sensor_reading import sensor_reading as sensor_reading_crud
        from app.crud.model_readings import model_readings as model_readings_crud
        from app.crud.weather import weather as weather_crud
        from app.services.sensor_reading_service import sensor_reading_service
        from app.services.weather_service import weather_service
        from app.core.config import settings
        from datetime import datetime, timezone, timedelta

        # --- 1. Load Sensor Reading (Water Level) ---
        latest_sensor = await sensor_reading_crud.get_latest_reading(db=db)
        if latest_sensor:
            # Check if data is within the acceptable warning period (not too stale)
            is_valid = latest_sensor.timestamp >= datetime.now(timezone.utc) - timedelta(minutes=settings.SENSOR_WARNING_PERIOD_MINUTES)
            
            if is_valid:
                # Calculate summary to get trend and critical percentage
                summary = await sensor_reading_service.calculate_record_summary(db=db, reading=latest_sensor)
                
                self.water_level_status = WaterLevelStatus(
                    timestamp=latest_sensor.timestamp,
                    water_level_cm=summary.water_level.current_cm,
                    change_rate=summary.water_level.change_rate,
                    critical_percentage=summary.alert.percentage_of_critical,
                    trend=summary.water_level.trend
                )

        # --- 2. Load Model Reading (Blockage) ---
        latest_model = await model_readings_crud.get_latest_reading(db=db)
        if latest_model:
            # Check if data is within the acceptable warning period
            model_timestamp = latest_model["timestamp"]
            is_valid = model_timestamp >= datetime.now(timezone.utc) - timedelta(minutes=settings.SENSOR_WARNING_PERIOD_MINUTES)
            
            if is_valid:
                self.blockage_status = BlockageStatus(
                    timestamp=model_timestamp,
                    status=latest_model["status"]
                )

        # --- 3. Load Weather Condition ---
        latest_weather = await weather_crud.get_latest_weather(db)
        if latest_weather:
            # Check if data is within the acceptable warning period
            weather_timestamp = latest_weather["created_at"]
            is_valid = weather_timestamp >= datetime.now(timezone.utc) - timedelta(minutes=settings.WEATHER_CONDITION_WARNING_PERIOD_MINUTES)
            
            if is_valid:
                # Get weather description
                weather_summary = weather_service.get_weather_summary(
                    created_at=weather_timestamp,
                    weather_code=latest_weather["weather_code"],
                    precipitation_mm=latest_weather["precipitation_mm"]
                )
                
                self.weather_status = WeatherStatus(
                    timestamp=weather_timestamp,
                    precipitation_mm=latest_weather["precipitation_mm"],
                    weather_condition=weather_summary.condition
                )
        
        # --- 4. Recalculate Fusion Data with loaded values ---
        await self._recalculate_fusion_data()

    async def calculate_visual_status_score(self, blockage_status: BlockageStatus = None):
        if blockage_status:
            self.blockage_status = blockage_status
        await self._recalculate_fusion_data()

    async def calculate_water_level_score(self, water_level_status: WaterLevelStatus = None):
        if water_level_status:
            self.water_level_status = water_level_status
        await self._recalculate_fusion_data()

    async def calculate_weather_score(self, weather_status: WeatherStatus = None):
        if weather_status:
            self.weather_status = weather_status
        await self._recalculate_fusion_data()

    async def _recalculate_fusion_data(self):
        from app.core.database import AsyncSessionLocal
        
        score = 0
        conditions = []
        
        # --- Blockage Score (0-35) ---
        if self.blockage_status:
            if self.blockage_status.status == "blocked":
                score += 35
                conditions.append("Waterway is BLOCKED - Immediate action required.")
            elif self.blockage_status.status == "partial":
                score += 20
                conditions.append("Partial blockage detected in waterway.")

        # --- Water Level Score (0-45) ---
        if self.water_level_status:
            if self.water_level_status.critical_percentage < 50:
                score += 10
            elif 50 <= self.water_level_status.critical_percentage < 75:
                score += 20
            elif 75 <= self.water_level_status.critical_percentage < 90:
                score += 30
            elif 90 <= self.water_level_status.critical_percentage < 100:
                score += 45
                conditions.append("Water level nearing critical threshold.")
            elif self.water_level_status.critical_percentage == 100:
                score += 45
                conditions.append("Water level at CRITICAL threshold!")
            else:
                score += 45
                conditions.append("Water level above CRITICAL threshold!")

            if self.water_level_status.trend == "rising":
                score += 5

            if self.water_level_status.change_rate >= 2:
                conditions.append("Water level rising quickly.")
            elif self.water_level_status.change_rate >= 1.5:
                conditions.append("Water level rising.")

        # --- Weather Score (0-20) ---
        if self.weather_status:
            if 1 <= self.weather_status.precipitation_mm < 2.55:
                score += 8
            elif 2.55 <= self.weather_status.precipitation_mm < 7.5:
                score += 15
            elif self.weather_status.precipitation_mm >= 7.5:
                score += 20
                conditions.append("Heavy rainfall detected.")

        # --- Critical Combination Check ---
        if (self.blockage_status and self.blockage_status.status == "blocked" and
            self.water_level_status and self.water_level_status.critical_percentage >= 90 and
            self.weather_status and self.weather_status.precipitation_mm >= 7.5):
            conditions.append("MULTIPLE CRITICAL FACTORS")

        # Retreive cached alert thresholds
        async with AsyncSessionLocal() as db:
            alert_thresholds: AlertThresholdsResponse = await cache_service.get_alert_thresholds(db)

        # Determine Alert Name based on score
        alert_name = "Normal"
        if alert_thresholds.tier_2_min <= score <= alert_thresholds.tier_2_max:
            alert_name = "Warning"
        elif alert_thresholds.tier_3_min <= score:
            alert_name = "Critical"

        if alert_name == "Normal":
            if not conditions:
                conditions = [
                    "All systems operating within normal parameters",
                    "Drainage system clear and functioning",
                    "Water levels within safe range"
                ]
            else:
                # Some conditions present but overall normal
                conditions = ["Conditions normal - Continue routine monitoring"] + conditions
            
        self.fusion_data = FusionData(
            alert_name=alert_name,
            combined_risk_score=score,
            triggered_conditions=conditions
        )
        
        # Update fusion analysis only if all components are present
        if self.blockage_status and self.water_level_status and self.weather_status:
            self.fusion_analysis = FusionAnalysisData(
                fusion_data=self.fusion_data,
                blockage_status=self.blockage_status,
                water_level_status=self.water_level_status,
                weather_status=self.weather_status
            )
        
        await self.broadcast_fusion_analysis()

fusion_analysis_state = FusionAnalysisState()