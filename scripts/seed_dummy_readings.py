import asyncio
import hashlib
import json
import random
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from sqlalchemy import and_, delete, select


sys.path.append(str(Path(__file__).parent.parent))

from app.core.cloudinary import init_cloudinary, upload_image
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.crud.daily_summary import daily_summary_crud
from app.models import CameraDevice, DailySummary, ModelReadings, SensorDevice, SensorReading, Weather
from app.services.daily_summary.service import daily_summary_service
from app.services.ml_service import ml_service


# ============================================
# CONFIGURATION
# ============================================
LOCATION_ID = 1
DAYS_TO_GENERATE = 20

SENSOR_INTERVAL_MINUTES = 1
MODEL_INTERVAL_MINUTES = 3
WEATHER_INTERVAL_HOURS = 1

IMAGE_DIR = Path("dummy_images")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
STORE_ABSOLUTE_IMAGE_PATHS = False
UPLOAD_IMAGES_TO_CLOUDINARY = True
USE_ML_MODEL_FOR_IMAGES = True
CLOUDINARY_UPLOAD_FOLDER = "agos/dummy_model_readings"
CLOUDINARY_URL_CACHE_FILE = IMAGE_DIR / ".cloudinary_urls.json"
MAX_IMAGES_TO_PROCESS = None

SKIP_EXISTING_AT_TIMESTAMP = True
RANDOM_SEED = 42
BATCH_SIZE = 1000
REFRESH_DAILY_SUMMARIES = True


@dataclass
class WeatherPoint:
    timestamp: datetime
    precipitation_mm: float
    weather_code: int
    temperature_2m: float
    relative_humidity_2m: float
    wind_speed_10m: float
    wind_direction_10m: float
    cloud_cover: float


@dataclass
class ModelPoint:
    timestamp: datetime
    image_path: str
    blockage_percentage: float
    blockage_status: str


@dataclass
class ModelImageAsset:
    image_path: str
    blockage_percentage: float
    blockage_status: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(second=0, microsecond=0)


def _utc_key(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0)


def _iter_times(start: datetime, end: datetime, step: timedelta):
    current = start
    while current <= end:
        yield current
        current += step


def _iter_dates(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _align_down(dt: datetime, step: timedelta) -> datetime:
    seconds = int(step.total_seconds())
    epoch = int(dt.timestamp())
    return datetime.fromtimestamp(epoch - (epoch % seconds), tz=timezone.utc)


def _list_images() -> list[Path]:
    image_dir = IMAGE_DIR.resolve() if STORE_ABSOLUTE_IMAGE_PATHS else IMAGE_DIR
    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {IMAGE_DIR}")

    images = [
        path
        for path in image_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not images:
        raise FileNotFoundError(f"No images found in {IMAGE_DIR}")
    images = sorted(images)
    if MAX_IMAGES_TO_PROCESS is not None:
        images = images[:MAX_IMAGES_TO_PROCESS]
    return images


def _image_public_id(path: Path) -> str:
    digest = hashlib.sha1(path.read_bytes()).hexdigest()[:12]
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", path.stem).strip("_") or "image"
    return f"{safe_stem}_{digest}"


def _load_url_cache() -> dict[str, dict]:
    if not CLOUDINARY_URL_CACHE_FILE.exists():
        return {}
    with CLOUDINARY_URL_CACHE_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return {str(key): value for key, value in data.items()}


def _save_url_cache(cache: dict[str, dict]) -> None:
    CLOUDINARY_URL_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CLOUDINARY_URL_CACHE_FILE.open("w", encoding="utf-8") as file:
        json.dump(cache, file, indent=2, sort_keys=True)


def _local_image_value(path: Path) -> str:
    if STORE_ABSOLUTE_IMAGE_PATHS:
        return str(path.resolve())
    return path.as_posix()


def _cache_key_for_image(path: Path) -> str:
    digest = hashlib.sha1(path.read_bytes()).hexdigest()
    return f"{path.as_posix()}:{digest}"


async def _prepare_model_image_assets(images: list[Path]) -> list[ModelImageAsset]:
    if not UPLOAD_IMAGES_TO_CLOUDINARY:
        return [
            ModelImageAsset(
                image_path=_local_image_value(path),
                blockage_percentage=0.0,
                blockage_status="clear",
            )
            for path in images
        ]

    init_cloudinary()
    cache = _load_url_cache()
    assets: list[ModelImageAsset] = []

    for index, path in enumerate(images, start=1):
        cache_key = _cache_key_for_image(path)
        cached_url = cache.get(cache_key)
        if isinstance(cached_url, dict) and cached_url.get("secure_url"):
            assets.append(
                ModelImageAsset(
                    image_path=cached_url["secure_url"],
                    blockage_percentage=float(cached_url.get("blockage_percentage", 0.0)),
                    blockage_status=str(cached_url.get("blockage_status", "clear")),
                )
            )
            continue

        image_bytes = path.read_bytes()
        blockage_percentage = 0.0
        blockage_status = "clear"
        upload_bytes = image_bytes

        if USE_ML_MODEL_FOR_IMAGES:
            blockage_percentage, blockage_status, upload_bytes = await ml_service._infer_and_annotate(image_bytes)

        print(
            f"Uploading dummy image {index}/{len(images)}: {path.name} "
            f"({blockage_status}, {blockage_percentage}%)"
        )
        result = await upload_image(
            file=BytesIO(upload_bytes),
            filename=_image_public_id(path),
            folder=CLOUDINARY_UPLOAD_FOLDER,
        )
        if not result or not result.get("secure_url"):
            raise RuntimeError(f"Cloudinary upload failed for {path}")

        cache[cache_key] = {
            "secure_url": result["secure_url"],
            "public_id": result.get("public_id"),
            "blockage_percentage": blockage_percentage,
            "blockage_status": blockage_status,
        }
        assets.append(
            ModelImageAsset(
                image_path=result["secure_url"],
                blockage_percentage=blockage_percentage,
                blockage_status=blockage_status,
            )
        )
        _save_url_cache(cache)

    return assets


def _weather_code_for_precip(precipitation_mm: float, cloud_cover: float) -> int:
    if precipitation_mm >= 7.5:
        return random.choice([65, 80, 81, 82, 95])
    if precipitation_mm >= 2.55:
        return random.choice([61, 63, 80])
    if precipitation_mm >= 1.0:
        return random.choice([51, 53, 61])
    if cloud_cover >= 75:
        return 3
    if cloud_cover >= 35:
        return random.choice([1, 2])
    return 0


def _generate_weather(start: datetime, end: datetime) -> list[WeatherPoint]:
    points: list[WeatherPoint] = []
    rain_event_hours = 0
    rain_intensity = 0.0

    for ts in _iter_times(start, end, timedelta(hours=WEATHER_INTERVAL_HOURS)):
        local_hour = ts.astimezone(settings.APP_TIMEZONE).hour

        if rain_event_hours <= 0 and random.random() < 0.16:
            rain_event_hours = random.randint(2, 7)
            rain_intensity = random.choice([1.5, 3.5, 6.0, 10.0])

        if rain_event_hours > 0:
            precipitation = max(0.0, random.gauss(rain_intensity, rain_intensity * 0.35))
            rain_event_hours -= WEATHER_INTERVAL_HOURS
            if rain_event_hours <= 0:
                rain_intensity = 0.0
        else:
            precipitation = random.choice([0.0, 0.0, 0.0, round(random.uniform(0.0, 0.8), 2)])

        precipitation = round(min(25.0, precipitation), 2)
        is_rainy = precipitation >= 1.0
        cloud_cover = round(
            min(100.0, max(5.0, random.gauss(85 if is_rainy else 45, 18))),
            1,
        )
        temperature_base = 27.5 if 6 <= local_hour <= 18 else 25.5
        temperature = round(
            max(23.0, min(34.0, random.gauss(temperature_base - precipitation * 0.18, 1.3))),
            1,
        )
        humidity = round(
            max(55.0, min(98.0, random.gauss(88 if is_rainy else 74, 7))),
            1,
        )
        wind_speed = round(max(1.0, min(45.0, random.gauss(12 + precipitation * 0.8, 5))), 1)

        points.append(
            WeatherPoint(
                timestamp=ts,
                precipitation_mm=precipitation,
                weather_code=_weather_code_for_precip(precipitation, cloud_cover),
                temperature_2m=temperature,
                relative_humidity_2m=humidity,
                wind_speed_10m=wind_speed,
                wind_direction_10m=round(random.uniform(0, 359), 1),
                cloud_cover=cloud_cover,
            )
        )

    return points


def _precip_at(weather_points: list[WeatherPoint], ts: datetime) -> float:
    if not weather_points:
        return 0.0
    index = min(
        len(weather_points) - 1,
        max(0, int((ts - weather_points[0].timestamp).total_seconds() // 3600)),
    )
    return weather_points[index].precipitation_mm


def _status_from_percentage(percentage: float) -> str:
    if percentage < 20:
        return "clear"
    if percentage < 60:
        return "partial"
    return "blocked"


def _generate_model_points(
    start: datetime,
    end: datetime,
    weather_points: list[WeatherPoint],
    image_assets: list[ModelImageAsset],
) -> list[ModelPoint]:
    points: list[ModelPoint] = []
    debris_level = random.uniform(0, 12)

    for ts in _iter_times(start, end, timedelta(minutes=MODEL_INTERVAL_MINUTES)):
        precipitation = _precip_at(weather_points, ts)
        rain_push = precipitation * random.uniform(0.08, 0.22)
        random_debris = random.uniform(4, 18) if random.random() < 0.006 else 0.0
        natural_decay = random.uniform(0.04, 0.18)

        debris_level = max(0.0, min(100.0, debris_level + rain_push + random_debris - natural_decay))
        if precipitation < 1 and random.random() < 0.015:
            debris_level = max(0.0, debris_level - random.uniform(2, 8))

        asset = random.choice(image_assets)
        if USE_ML_MODEL_FOR_IMAGES and UPLOAD_IMAGES_TO_CLOUDINARY:
            percentage = asset.blockage_percentage
            blockage_status = asset.blockage_status
        else:
            percentage = round(max(0.0, min(100.0, random.gauss(debris_level, 4.0))), 2)
            blockage_status = _status_from_percentage(percentage)

        points.append(
            ModelPoint(
                timestamp=ts,
                image_path=asset.image_path,
                blockage_percentage=percentage,
                blockage_status=blockage_status,
            )
        )

    return points


def _nearest_model(model_points: list[ModelPoint], ts: datetime) -> ModelPoint | None:
    if not model_points:
        return None
    elapsed = (ts - model_points[0].timestamp).total_seconds()
    index = round(elapsed / (MODEL_INTERVAL_MINUTES * 60))
    return model_points[min(len(model_points) - 1, max(0, index))]


def _generate_sensor_readings(
    start: datetime,
    end: datetime,
    sensor_device_id: int,
    installation_height: float,
    warning_threshold: float,
    critical_threshold: float,
    weather_points: list[WeatherPoint],
    model_points: list[ModelPoint],
) -> list[SensorReading]:
    rows: list[SensorReading] = []
    baseline = max(5.0, warning_threshold * 0.25)
    water_level = random.uniform(baseline * 0.8, baseline * 1.2)

    for ts in _iter_times(start, end, timedelta(minutes=SENSOR_INTERVAL_MINUTES)):
        precipitation = _precip_at(weather_points, ts)
        model_point = _nearest_model(model_points, ts)
        blockage_factor = (model_point.blockage_percentage / 100.0) if model_point else 0.0

        rain_gain = precipitation * random.uniform(0.35, 0.75)
        blocked_drain_penalty = blockage_factor * random.uniform(0.25, 0.8)
        drainage = random.uniform(0.7, 1.8) * (1.0 - min(0.75, blockage_factor))
        target = baseline + precipitation * 4.2 + blockage_factor * warning_threshold * 0.55

        water_level += (target - water_level) * 0.08 + rain_gain + blocked_drain_penalty - drainage
        water_level += random.gauss(0, 0.7)
        water_level = max(0.0, min(installation_height - 1, water_level))

        if water_level > critical_threshold and precipitation < 1.0:
            water_level -= random.uniform(0.5, 2.0)

        water_level = round(water_level, 2)
        raw_distance = round(max(0.0, installation_height - water_level), 2)

        rows.append(
            SensorReading(
                sensor_device_id=sensor_device_id,
                water_level_cm=Decimal(str(water_level)),
                raw_distance_cm=Decimal(str(raw_distance)),
                signal_strength=random.randint(-78, -42),
                timestamp=ts,
            )
        )

    return rows


async def _existing_timestamp_keys(db, model, timestamp_col, *filters) -> set[datetime]:
    if not SKIP_EXISTING_AT_TIMESTAMP:
        return set()

    result = await db.execute(select(timestamp_col).where(and_(*filters)))
    return {_utc_key(row[0]) for row in result.all()}


async def _insert_in_batches(db, rows: list) -> int:
    total = 0
    for index in range(0, len(rows), BATCH_SIZE):
        batch = rows[index:index + BATCH_SIZE]
        db.add_all(batch)
        await db.commit()
        total += len(batch)
    return total


async def _refresh_daily_summaries(db, start: datetime, end: datetime) -> int:
    if not REFRESH_DAILY_SUMMARIES:
        return 0

    start_date = start.astimezone(settings.APP_TIMEZONE).date()
    end_date = end.astimezone(settings.APP_TIMEZONE).date()

    await db.execute(
        delete(DailySummary).where(
            DailySummary.location_id == LOCATION_ID,
            DailySummary.summary_date >= start_date,
            DailySummary.summary_date <= end_date,
        )
    )
    await db.commit()

    created = 0
    for target_date in _iter_dates(start_date, end_date):
        summary_data = await daily_summary_service.generate_summary_for_location(
            db=db,
            location_id=LOCATION_ID,
            target_date=target_date,
        )
        await daily_summary_crud.create_daily_summary(
            db=db,
            location_id=LOCATION_ID,
            summary_date=target_date,
            summary_data=summary_data,
        )
        created += 1

    return created


async def seed_dummy_readings() -> None:
    random.seed(RANDOM_SEED)

    end = _utc_now()
    start = _align_down(end - timedelta(days=DAYS_TO_GENERATE), timedelta(hours=1))
    images = _list_images()
    image_assets = await _prepare_model_image_assets(images)

    async with AsyncSessionLocal() as db:
        sensor_result = await db.execute(
            select(SensorDevice).where(SensorDevice.location_id == LOCATION_ID)
        )
        sensor_device = sensor_result.scalar_one_or_none()
        if sensor_device is None:
            raise RuntimeError(f"No sensor device found for location_id={LOCATION_ID}")

        camera_result = await db.execute(
            select(CameraDevice).where(CameraDevice.location_id == LOCATION_ID)
        )
        camera_device = camera_result.scalar_one_or_none()
        if camera_device is None:
            raise RuntimeError(f"No camera device found for location_id={LOCATION_ID}")

        sensor_config = sensor_device.sensor_config
        weather_points = _generate_weather(start, end)
        model_points = _generate_model_points(start, end, weather_points, image_assets)
        sensor_rows = _generate_sensor_readings(
            start=start,
            end=end,
            sensor_device_id=sensor_device.id,
            installation_height=float(sensor_config.installation_height),
            warning_threshold=float(sensor_config.warning_threshold),
            critical_threshold=float(sensor_config.critical_threshold),
            weather_points=weather_points,
            model_points=model_points,
        )

        weather_existing = await _existing_timestamp_keys(
            db,
            Weather,
            Weather.created_at,
            Weather.location_id == LOCATION_ID,
            Weather.created_at >= start,
            Weather.created_at <= end,
        )
        model_existing = await _existing_timestamp_keys(
            db,
            ModelReadings,
            ModelReadings.timestamp,
            ModelReadings.camera_device_id == camera_device.id,
            ModelReadings.timestamp >= start,
            ModelReadings.timestamp <= end,
        )
        sensor_existing = await _existing_timestamp_keys(
            db,
            SensorReading,
            SensorReading.timestamp,
            SensorReading.sensor_device_id == sensor_device.id,
            SensorReading.timestamp >= start,
            SensorReading.timestamp <= end,
        )

        weather_rows = [
            Weather(
                location_id=LOCATION_ID,
                precipitation_mm=p.precipitation_mm,
                weather_code=p.weather_code,
                temperature_2m=p.temperature_2m,
                relative_humidity_2m=p.relative_humidity_2m,
                wind_speed_10m=p.wind_speed_10m,
                wind_direction_10m=p.wind_direction_10m,
                cloud_cover=p.cloud_cover,
                created_at=p.timestamp,
            )
            for p in weather_points
            if _utc_key(p.timestamp) not in weather_existing
        ]
        model_rows = [
            ModelReadings(
                camera_device_id=camera_device.id,
                image_path=p.image_path,
                timestamp=p.timestamp,
                blockage_percentage=p.blockage_percentage,
                blockage_status=p.blockage_status,
            )
            for p in model_points
            if _utc_key(p.timestamp) not in model_existing
        ]
        sensor_rows = [
            row for row in sensor_rows if _utc_key(row.timestamp) not in sensor_existing
        ]

        weather_count = await _insert_in_batches(db, weather_rows)
        model_count = await _insert_in_batches(db, model_rows)
        sensor_count = await _insert_in_batches(db, sensor_rows)
        summary_count = await _refresh_daily_summaries(db, start, end)

    print("Dummy readings seeded")
    print(f"  Range: {start.isoformat()} to {end.isoformat()}")
    print(f"  Location: {LOCATION_ID}")
    print(f"  Weather rows: {weather_count}")
    print(f"  Model rows: {model_count}")
    print(f"  Sensor rows: {sensor_count}")
    print(f"  Daily summaries refreshed: {summary_count}")


if __name__ == "__main__":
    asyncio.run(seed_dummy_readings())
