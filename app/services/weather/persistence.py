from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Weather
from app.schemas import WeatherCreate
from app.crud import weather_crud


async def save_weather(db: AsyncSession, weather_data: WeatherCreate) -> None:
    """Save weather data to the database (no return)."""
    await weather_crud.create_only(db=db, obj_in=weather_data)


async def save_weather_and_return(db: AsyncSession, weather_data: WeatherCreate) -> Weather:
    """Save weather data to the database and return the created record."""
    return await weather_crud.create_and_return(db=db, obj_in=weather_data)
