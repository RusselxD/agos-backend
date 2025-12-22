import httpx
from fastapi import HTTPException
from app.schemas import WeatherConditionResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.sensor_devices import sensor_device as sensor_device_crud

class WeatherConditionService:

    async def get_weather_condition(self, db: AsyncSession, sensor_id: int = 1):

        lat, lon = await sensor_device_crud.get_coordinates(db, sensor_id)

        if not lat or not lon:
            raise HTTPException(status_code=404, detail="Sensor device coordinates not found")

        api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=precipitation,weather_code"
    
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(api_url)
                response.raise_for_status()  # Raises exception for 4xx/5xx status codes
                data = response.json()
                return WeatherConditionResponse(
                    weather_code = data["current"]["weather_code"],
                    precipitation = data["current"]["precipitation"],
                )
            except httpx.HTTPError as e:
                raise HTTPException(status_code=500, detail=f"Error fetching weather data: {str(e)}")

weather_condition_service = WeatherConditionService()