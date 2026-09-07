from typing import Literal

from pydantic import BaseModel, Field


class RouteCoordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class EvacuationRouteRequest(BaseModel):
    center_id: int = Field(gt=0)
    origin: RouteCoordinate


class EvacuationRouteResponse(BaseModel):
    geometry: list[RouteCoordinate] = Field(min_length=2)
    distance_meters: float = Field(ge=0)
    duration_seconds: float = Field(ge=0)
    provider: Literal["openrouteservice"] = "openrouteservice"
