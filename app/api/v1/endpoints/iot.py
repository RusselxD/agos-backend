from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.dependencies import require_iot_api_key
from app.core.state import fusion_state_manager
from app.schemas.fusion_analysis import IoTRiskScoreResponse


router = APIRouter(
    prefix="/iot",
    tags=["iot"],
    dependencies=[Depends(require_iot_api_key)],
)


@router.get("/risk-score", response_model=IoTRiskScoreResponse)
async def get_current_risk_score(
    location_id: int = Query(..., ge=1),
) -> IoTRiskScoreResponse:
    try:
        fusion_analysis = fusion_state_manager.get_fusion_analysis_state(
            location_id=location_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if fusion_analysis is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fusion analysis data is not available yet.",
        )

    return IoTRiskScoreResponse(
        risk_score=fusion_analysis.fusion_data.combined_risk_score
    )
