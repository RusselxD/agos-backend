# app/api/v1/endpoints/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from app.core.ws_manager import ws_manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    
    # Accept the WebSocket connection
    await websocket.accept()
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return
    
    # Add the WebSocket connection to the manager
    await ws_manager.connect(websocket)
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)