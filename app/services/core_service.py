from app.crud import location_crud
from app.crud import sensor_device_crud
from app.crud import camera_device_crud
from app.schemas import LocationDetails, DeviceDetails, PublicStatusResponse
from fastapi import HTTPException


class CoreService:
    async def get_default_location(self, db) -> LocationDetails:

        default_location = await location_crud.get_default_location(db=db)
        print(default_location)
        if not default_location:
            raise HTTPException(status_code=404, detail="Default location not found")

        return LocationDetails(
            location_id=default_location["id"], location_name=default_location["name"]
        )

    async def get_device_details(self, db, location_id: int) -> DeviceDetails:

        default_camera = await camera_device_crud.get_default_camera_by_location(
            db=db, location_id=location_id
        )
        default_sensor = await sensor_device_crud.get_default_sensor_by_location(
            db=db, location_id=location_id
        )

        if not default_camera or not default_sensor:
            raise HTTPException(
                status_code=404,
                detail="Default devices not found for the given location",
            )

        return DeviceDetails(
            sensor_device_id=default_sensor["id"],
            sensor_device_name=default_sensor["device_name"],
            camera_device_id=default_camera["id"],
            camera_device_name=default_camera["device_name"],
        )

    def get_public_status(self, location_id: int) -> PublicStatusResponse:
        """Return the latest in-memory fusion snapshot for public first paint.

        The WebSocket remains the live source. This small REST read closes the
        startup/offline-recovery gap without exposing the operator-only score in
        the citizen-facing level.
        """
        from app.core.state import fusion_state_manager

        try:
            fusion_analysis = fusion_state_manager.get_fusion_analysis_state(
                location_id=location_id
            )
        except ValueError:
            fusion_analysis = None

        if fusion_analysis is None:
            return PublicStatusResponse(
                location_id=location_id,
                level="unknown",
                updated_at=None,
                fusion_analysis=None,
            )

        alert_name = fusion_analysis.fusion_data.alert_name
        level_by_alert = {
            "Normal": "safe",
            "Warning": "alert",
            "Critical": "high_risk",
        }
        timestamps = [
            status.timestamp
            for status in (
                fusion_analysis.blockage_status,
                fusion_analysis.water_level_status,
                fusion_analysis.weather_status,
            )
            if status is not None
        ]

        return PublicStatusResponse(
            location_id=location_id,
            level=level_by_alert.get(alert_name, "unknown"),
            updated_at=max(timestamps) if timestamps else None,
            fusion_analysis=fusion_analysis,
        )


core_service = CoreService()
