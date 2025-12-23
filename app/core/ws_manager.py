from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        self.active.append(ws)
        print(f"Client connected. Total connections: {len(self.active)}")
    
    async def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
            print(f"Client disconnected. Total connections: {len(self.active)}")

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