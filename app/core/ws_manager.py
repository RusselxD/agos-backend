from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.connections: dict[int, list[WebSocket]] = {}
        # int is the location_id

    async def connect(self, websocket: WebSocket, location_id: int):
        if location_id not in self.connections:
            self.connections[location_id] = []

        self.connections[location_id].append(websocket)
        print(f"Client connected. Total connections: {len(self.connections[location_id])}")
    
    async def disconnect(self, websocket: WebSocket, location_id: int):
        if location_id in self.connections and websocket in self.connections[location_id]:
            self.connections[location_id].remove(websocket)
            print(f"Client disconnected. Total connections: {len(self.connections[location_id])}")

            # Cleanup if no connections left for this location
            if not self.connections[location_id]:
                del self.connections[location_id]

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
    async def broadcast_to_location(self, message: dict, location_id: int):

        if location_id not in self.connections:
            return  # No connections for this location

        disconnected = []
        for ws in self.connections[location_id][:]: # iterate over a copy of the list
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
            if ws in self.connections[location_id]:
                self.connections[location_id].remove(ws)


ws_manager = ConnectionManager()