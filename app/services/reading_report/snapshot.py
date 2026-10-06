"""Stable report metadata and metrics, all derived from the saved summaries."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

from app.schemas.daily_summary import DailySummaryResponse


def summary_stats(rows: list[dict]) -> dict:
    risk = [r for r in rows if r["max_risk_score"] is not None]
    water = [r for r in rows if r["max_water_level_cm"] is not None]
    precip = [r["max_precipitation_mm"] for r in rows if r["max_precipitation_mm"] is not None]
    obstruction = [r for r in rows if r["most_severe_blockage"] is not None]
    highest = max(risk, key=lambda r: r["max_risk_score"]) if risk else None
    peak = max(water, key=lambda r: r["max_water_level_cm"]) if water else None
    return {
        "highestRisk": {"value": highest["max_risk_score"], "date": highest["summary_date"]} if highest else None,
        "peakWaterLevel": {"value": peak["max_water_level_cm"], "date": peak["summary_date"]} if peak else None,
        "avgDailyPeakPrecipitation": sum(precip) / len(precip) if precip else None,
        "precipDays": len(precip),
        "blockageDays": len(obstruction),
        "blockedDays": sum(r["most_severe_blockage"].lower() == "blocked" for r in obstruction),
    }


def make_snapshot(location, request, summaries: list[DailySummaryResponse], utc_offset: float, *, captured_at: datetime | None = None) -> dict:
    rows = sorted((r.model_dump(mode="json") for r in summaries), key=lambda r: r["summary_date"])
    present = {r["summary_date"] for r in rows}
    days = (request.end_date - request.start_date).days + 1
    missing = [(request.start_date + timedelta(days=i)).isoformat() for i in range(days)
               if (request.start_date + timedelta(days=i)).isoformat() not in present]
    timezone_name = "Asia/Manila" if utc_offset == 8 else f"UTC{utc_offset:+g}"
    captured_at = captured_at or datetime.now(timezone.utc)
    local_today = captured_at.astimezone(timezone(timedelta(hours=utc_offset))).date()
    partial_dates = [local_today.isoformat()] if request.start_date <= local_today <= request.end_date else []
    snapshot = {
        "location_id": request.location_id, "start_date": request.start_date.isoformat(), "end_date": request.end_date.isoformat(),
        "location_name": location.name, "timezone": timezone_name, "utc_offset_hours": utc_offset,
        "summaries": rows, "missing_dates": missing, "partial_dates": partial_dates, "stats": summary_stats(rows),
        "metric_definitions": "Risk and water: highest daily maxima. Precipitation: mean of daily maxima in mm. Obstruction: days with potential surface obstruction based on the worst smoothed status. Missing values excluded.",
    }
    snapshot["data_hash"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return snapshot
