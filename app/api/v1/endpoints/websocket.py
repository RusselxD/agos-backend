from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends
from app.core.ws_manager import ws_manager
from app.services.websocket_service import websocket_service
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):

    location_id = websocket.query_params.get("location_id")
    
    # Accept the WebSocket connection
    await websocket.accept()
    
    if not location_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing location_id")
        return
    
    # Convert location_id to int
    try:
        location_id = int(location_id)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid location_id")
        return

    # Add the WebSocket connection to the manager
    await ws_manager.connect(websocket=websocket, location_id=location_id)
    
    # Send initial data to the connected client
    await websocket_service.send_initial_data(websocket=websocket, db=db, location_id=location_id)

    try:
        while True:
            await websocket.receive_text() # Keep the connection alive
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket=websocket, location_id=location_id)