from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        self.active.append(websocket)
        print(f"Client connected. Total connections: {len(self.active)}")
    
    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)
            print(f"Client disconnected. Total connections: {len(self.active)}")

    """
        Broadcast Message Format:
        {
            type: str
            data: {
                status: str,
                message: str,
                data: (Actual data object depending on the type)
            }
        }

        Sensor Reading Broadcast Type: "sensor_update"
        Model Reading Broadcast Type: "blockage_detection_update"
        Weather Condition Broadcast Type: "weather_update"

        Fusion Analysis Broadcast Type: "fusion_analysis_update"
    """
    async def broadcast(self, message: dict):
        disconnected = []
        for ws in self.active[:]:  # Create a copy to iterate safely
            try:
                # Check application state if possible (FastAPI/Starlette specific)
                if ws.client_state.name != "CONNECTED":
                    disconnected.append(ws)
                    continue
                    
                await ws.send_json(message)
            except RuntimeError:
                # This catches 'Unexpected ASGI message' (Client already closed)
                disconnected.append(ws)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.append(ws)

        for ws in disconnected:
            if ws in self.active:
                self.active.remove(ws)

ws_manager = ConnectionManager()