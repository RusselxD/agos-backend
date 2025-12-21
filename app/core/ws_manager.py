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
                await ws.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.append(ws)

        for ws in disconnected:
            await self.disconnect(ws)

ws_manager = ConnectionManager()