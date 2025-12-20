import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.schemas.sensor_reading import SensorReadingCreate
from app.crud.sensor_reading import sensor_reading as sensor_reading_crud

def seed():
    db: Session = SessionLocal()

    now = datetime.now()
    
    # Realistic water tank scenario: gradual filling with some variations
    # Distance values are closer together (within ~20cm range)
    # Simulating a tank that's around 60-70% full with gradual changes
    sensor_readings = [
        SensorReadingCreate(
            sensor_id=1,
            timestamp=(now - timedelta(minutes=60)).isoformat(),
            raw_distance_cm=75.0,
            signal_strength=-45,
            signal_quality='excellent'
        ),
        SensorReadingCreate(
            sensor_id=1,
            timestamp=(now - timedelta(minutes=55)).isoformat(),
            raw_distance_cm=74.2,
            signal_strength=-48,
            signal_quality='excellent'
        ),
        SensorReadingCreate(
            sensor_id=1,
            timestamp=(now - timedelta(minutes=50)).isoformat(),
            raw_distance_cm=73.5,
            signal_strength=-52,
            signal_quality='good'
        ),
        SensorReadingCreate(
            sensor_id=1,
            timestamp=(now - timedelta(minutes=45)).isoformat(),
            raw_distance_cm=72.8,
            signal_strength=-55,
            signal_quality='good'
        ),
        SensorReadingCreate(
            sensor_id=1,
            timestamp=(now - timedelta(minutes=40)).isoformat(),
            raw_distance_cm=71.5,
            signal_strength=-58,
            signal_quality='good'
        ),
        SensorReadingCreate(
            sensor_id=1,
            timestamp=(now - timedelta(minutes=35)).isoformat(),
            raw_distance_cm=70.3,
            signal_strength=-54,
            signal_quality='good'
        ),
        SensorReadingCreate(
            sensor_id=1,
            timestamp=(now - timedelta(minutes=30)).isoformat(),
            raw_distance_cm=69.8,
            signal_strength=-62,
            signal_quality='fair'
        ),
        SensorReadingCreate(
            sensor_id=1,
            timestamp=(now - timedelta(minutes=25)).isoformat(),
            raw_distance_cm=69.5,
            signal_strength=-65,
            signal_quality='fair'
        ),
        SensorReadingCreate(
            sensor_id=1,
            timestamp=(now - timedelta(minutes=20)).isoformat(),
            raw_distance_cm=68.2,
            signal_strength=-68,
            signal_quality='fair'
        ),
        SensorReadingCreate(
            sensor_id=1,
            timestamp=(now - timedelta(minutes=15)).isoformat(),
            raw_distance_cm=67.0,
            signal_strength=-72,
            signal_quality='poor'
        ),
        SensorReadingCreate(
            sensor_id=1,
            timestamp=(now - timedelta(minutes=10)).isoformat(),
            raw_distance_cm=66.1,
            signal_strength=-59,
            signal_quality='good'
        ),
        SensorReadingCreate(
            sensor_id=1,
            timestamp=(now - timedelta(minutes=5)).isoformat(),
            raw_distance_cm=65.5,
            signal_strength=-51,
            signal_quality='good'
        ),
        SensorReadingCreate(
            sensor_id=1,
            timestamp=now.isoformat(),
            raw_distance_cm=65.0,
            signal_strength=-47,
            signal_quality='excellent'
        ),
    ]
    
    sensor_reading_crud.create_multi(db, objs_in=sensor_readings)
    print("Seeded sensor readings with realistic water level changes and signal quality.")

    db.close()

if __name__ == "__main__":
    seed()