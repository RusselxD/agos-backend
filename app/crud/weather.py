from app.models import Weather
from app.schemas import WeatherCreate
from app.crud.base import CRUDBase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class CRUDWeather(CRUDBase[WeatherCreate, None, None]):
    
    async def get_latest_weather(self, db: AsyncSession, sensor_id: int = 1) -> Weather | None:
        result = await db.execute(
            select(self.model.precipitation_mm, self.model.weather_code, self.model.created_at)
            .filter(self.model.sensor_id == sensor_id)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        return result.mappings().first()

weather = CRUDWeather(Weather)