from app.models import Weather
from app.schemas import WeatherCreate
from app.crud.base import CRUDBase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDWeather(CRUDBase[Weather, WeatherCreate, None]):
    
    async def get_latest_weather(self, db: AsyncSession, location_id) -> Weather | None:
        result = await db.execute(
            select(self.model.precipitation_mm, self.model.weather_code, self.model.created_at)
            .filter(self.model.location_id == location_id)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        return result.mappings().first()


    async def get_latest_weather_full(self, db: AsyncSession, location_id: int) -> Weather | None:
        result = await db.execute(
            select(self.model)
            .filter(self.model.location_id == location_id)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()


weather_crud = CRUDWeather(Weather)