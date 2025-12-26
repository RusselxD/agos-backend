from app.models import Weather
from app.schemas import WeatherCreate
from app.crud.base import CRUDBase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class CRUDWeather(CRUDBase[WeatherCreate, None, None]):
    
    async def get_latest_weather(self, db: AsyncSession, sensor_id: int = 1) -> Weather | None:
        result = await db.execute(
            select(Weather.precipitation_mm, Weather.weather_code, Weather.created_at)
            .filter(Weather.sensor_id == sensor_id)
            .order_by(Weather.created_at.desc())
            .limit(1)
        )
        return result.mappings().first()

weather = CRUDWeather(Weather)