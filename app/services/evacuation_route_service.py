import logging

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.models import EvacuationCenter
from app.schemas.evacuation_route import (
    EvacuationRouteResponse,
    RouteCoordinate,
)


logger = logging.getLogger(__name__)

ORS_DIRECTIONS_URL = (
    "https://api.openrouteservice.org/v2/directions/foot-walking/geojson"
)
ORS_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class EvacuationRouteService:
    async def get_walking_route(
        self,
        origin: RouteCoordinate,
        destination: EvacuationCenter,
    ) -> EvacuationRouteResponse:
        if not settings.ORS_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Walking directions are not configured.",
            )

        try:
            async with httpx.AsyncClient(timeout=ORS_TIMEOUT) as client:
                response = await client.post(
                    ORS_DIRECTIONS_URL,
                    headers={
                        "Authorization": settings.ORS_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={
                        "coordinates": [
                            [origin.longitude, origin.latitude],
                            [destination.longitude, destination.latitude],
                        ],
                        "instructions": False,
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException as error:
            logger.warning("openrouteservice timed out: %s", error)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Walking directions timed out. Please try again.",
            ) from error
        except httpx.HTTPStatusError as error:
            logger.warning(
                "openrouteservice returned HTTP %s",
                error.response.status_code,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Walking directions are temporarily unavailable.",
            ) from error
        except httpx.HTTPError as error:
            logger.warning("openrouteservice request failed: %s", error)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Walking directions are temporarily unavailable.",
            ) from error

        try:
            payload = response.json()
            feature = payload["features"][0]
            coordinates = feature["geometry"]["coordinates"]
            summary = feature["properties"]["summary"]
            geometry = [
                RouteCoordinate(latitude=latitude, longitude=longitude)
                for longitude, latitude in coordinates
            ]
            return EvacuationRouteResponse(
                geometry=geometry,
                distance_meters=summary["distance"],
                duration_seconds=summary["duration"],
            )
        except (KeyError, IndexError, TypeError, ValueError) as error:
            logger.warning("openrouteservice returned an invalid route payload")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Walking directions returned an invalid response.",
            ) from error


evacuation_route_service = EvacuationRouteService()
