import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import random
import asyncio  # Add this import
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.schemas.sensor_reading import SensorReadingCreate
from app.crud.sensor_reading import sensor_reading as sensor_reading_crud

async def seed():
    async with AsyncSessionLocal() as db:  # Use async context manager
        now = datetime.now()
        sensor_readings = []

        # Starting distance (anywhere between 50 and 200)
        distance = random.uniform(50, 200)

        for i in range(50):
            # Decide randomly whether to rise, fall, or stay stable
            trend = random.choice(["rise", "fall", "stable"])
            
            if trend == "rise":
                # Increase distance a small random amount
                distance_change = random.uniform(0, 5)  # adjust max change as needed
                distance = min(distance + distance_change, 200)  # max 200
            elif trend == "fall":
                # Decrease distance a small random amount
                distance_change = random.uniform(0, 5)
                distance = max(distance - distance_change, 0)  # min 0
            else:  # stable
                # Small random jitter to keep it realistic
                distance_change = random.uniform(-1, 1)
                distance = max(0, min(distance + distance_change, 200))

            # Signal strength simulation remains the same
            signal_strength = random.randint(-75, -45)

            if signal_strength > -50:
                quality = "excellent"
            elif signal_strength > -60:
                quality = "good"
            elif signal_strength > -70:
                quality = "fair"
            else:
                quality = "poor"

            sensor_readings.append(
                SensorReadingCreate(
                    sensor_id=1,
                    timestamp=(now - timedelta(minutes=5 * (49 - i))).isoformat(),
                    raw_distance_cm=round(distance, 1),
                    signal_strength=signal_strength,
                    signal_quality=quality,
                )
            )

        await sensor_reading_crud.create_multi(db, objs_in=sensor_readings)
        print("Seeded 50 sensor readings at 5-minute intervals.")
        
    # db automatically closes when exiting the context manager

if __name__ == "__main__":
    asyncio.run(seed())  # Changed this line