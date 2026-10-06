"""Shared confidence rules for live inference and historical reconstruction."""

from collections.abc import Sequence

from app.core.config import settings
from app.schemas.fusion_analysis import ObstructionConfidence


def calculate_obstruction_confidence(
    statuses: Sequence[str], raw_percentage: float
) -> ObstructionConfidence:
    k = max(1, settings.OBSTRUCTION_WINDOW_K)
    window = list(statuses)[-k:]
    flagged = sum(status != "clear" for status in window)
    weighted = sum(
        1.0 if status == "blocked"
        else settings.OBSTRUCTION_PARTIAL_WEIGHT if status == "partial" else 0.0
        for status in window
    )
    fraction = weighted / k
    full = len(window) >= k
    if full and fraction >= settings.OBSTRUCTION_TIER_CONFIRMED:
        tier = "confirmed"
    elif full and fraction >= settings.OBSTRUCTION_TIER_LIKELY:
        tier = "likely"
    elif flagged:
        tier = "possible"
    else:
        tier = "clear"
    return ObstructionConfidence(
        tier=tier,
        score=round(min(1.0, fraction * (raw_percentage / 100.0)), 4),
        window_size=k,
        flagged_in_window=flagged,
    )


def obstruction_status_from_tier(tier: str) -> str:
    if tier in ("likely", "confirmed"):
        return "blocked"
    return "partial" if tier == "possible" else "clear"
