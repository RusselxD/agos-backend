import sys
import asyncio
import random
from pathlib import Path
from datetime import date, datetime, timezone, timedelta

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.data_sources.daily_summary import DailySummary
from app.models.data_sources.location import Location

# ============================================
# CONFIGURATION - Adjust these values
# ============================================
DAYS_TO_SEED = 100  # Number of days to seed (going backwards from today)

# Dummy data ranges
WATER_LEVEL_RANGE = (5.0, 200.0)  # cm
DEBRIS_COUNT_RANGE = (0, 25)
PRECIPITATION_RANGE = (0.0, 15.0)  # mm
RISK_SCORE_RANGE = (10, 100)
BLOCKAGE_STATUSES = ["clear", "partial", "blocked"]
WEATHER_CODES = [0, 1, 2, 3, 45, 48, 51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]  # WMO codes


def generate_random_time(target_date: date) -> datetime:
    """Generate a random timestamp within the given date."""
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime.combine(target_date, datetime.min.time()).replace(
        hour=hour, minute=minute, second=second, tzinfo=timezone.utc
    )


def generate_dummy_summary(target_date: date) -> dict:
    """Generate dummy data for a single day's summary."""
    
    # Water level - ensure min < max
    water_min = round(random.uniform(*WATER_LEVEL_RANGE), 2)
    water_max = round(random.uniform(water_min, WATER_LEVEL_RANGE[1]), 2)
    
    # Debris count - ensure min <= max
    debris_min = random.randint(*DEBRIS_COUNT_RANGE)
    debris_max = random.randint(debris_min, DEBRIS_COUNT_RANGE[1])
    
    # Precipitation - ensure min < max
    precip_min = round(random.uniform(*PRECIPITATION_RANGE), 2)
    precip_max = round(random.uniform(precip_min, PRECIPITATION_RANGE[1]), 2)
    
    # Risk score - ensure min < max
    risk_min = random.randint(*RISK_SCORE_RANGE)
    risk_max = random.randint(risk_min, RISK_SCORE_RANGE[1])
    
    # Blockage statuses - least severe <= most severe
    blockage_indices = sorted(random.sample(range(len(BLOCKAGE_STATUSES)), 2))
    least_blockage = BLOCKAGE_STATUSES[blockage_indices[0]]
    most_blockage = BLOCKAGE_STATUSES[blockage_indices[1]]
    
    return {
        # Risk scores
        "min_risk_score": risk_min,
        "max_risk_score": risk_max,
        "min_risk_timestamp": generate_random_time(target_date),
        "max_risk_timestamp": generate_random_time(target_date),
        
        # Debris/Blockage
        "min_debris_count": debris_min,
        "max_debris_count": debris_max,
        "min_debris_timestamp": generate_random_time(target_date),
        "max_debris_timestamp": generate_random_time(target_date),
        "least_severe_blockage": least_blockage,
        "most_severe_blockage": most_blockage,
        
        # Water level
        "min_water_level_cm": water_min,
        "max_water_level_cm": water_max,
        "min_water_timestamp": generate_random_time(target_date),
        "max_water_timestamp": generate_random_time(target_date),
        
        # Weather
        "min_precipitation_mm": precip_min,
        "max_precipitation_mm": precip_max,
        "min_precip_timestamp": generate_random_time(target_date),
        "max_precip_timestamp": generate_random_time(target_date),
        "most_severe_weather_code": random.choice(WEATHER_CODES),
    }


async def seed_daily_summaries():
    """Seed daily summaries for all locations for the past N days."""
    async with AsyncSessionLocal() as db:
        try:
            # Get all location IDs
            result = await db.execute(select(Location.id))
            location_ids = [row[0] for row in result.fetchall()]
            
            if not location_ids:
                print("❌ No locations found. Please seed locations first.")
                return
            
            print(f"📍 Found {len(location_ids)} location(s)")
            print(f"📅 Seeding {DAYS_TO_SEED} days of summaries per location...\n")
            
            today = date.today()
            total_created = 0
            total_skipped = 0
            
            for loc_id in location_ids:
                print(f"  Location {loc_id}:")
                
                for days_ago in range(1, DAYS_TO_SEED + 1):
                    target_date = today - timedelta(days=days_ago)
                    
                    # Check if summary already exists
                    existing = await db.execute(
                        select(DailySummary).where(
                            DailySummary.location_id == loc_id,
                            DailySummary.summary_date == target_date
                        )
                    )
                    if existing.scalar_one_or_none():
                        total_skipped += 1
                        continue
                    
                    # Generate and insert dummy data
                    summary_data = generate_dummy_summary(target_date)
                    summary = DailySummary(
                        location_id=loc_id,
                        summary_date=target_date,
                        **summary_data
                    )
                    db.add(summary)
                    total_created += 1
                
                await db.commit()
                print(f"    ✅ Processed {DAYS_TO_SEED} days")
            
            print(f"\n🎉 Daily summaries seeding completed!")
            print(f"   Created: {total_created}")
            print(f"   Skipped (already exist): {total_skipped}")
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error seeding daily summaries: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_daily_summaries())
