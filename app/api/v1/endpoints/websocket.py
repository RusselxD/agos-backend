from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends
from app.core.ws_manager import ws_manager
from app.services.websocket_service import websocket_service
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):

    token = websocket.query_params.get("token")
    
    # Accept the WebSocket connection
    await websocket.accept()
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return

    # Add the WebSocket connection to the manager
    await ws_manager.connect(websocket)
    
    # Send initial data to the connected client
    await websocket_service.send_initial_data(websocket, db)

    try:
        while True:
            await websocket.receive_text() # Keep the connection alive
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)