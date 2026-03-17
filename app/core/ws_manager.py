from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.connections: dict[int, list[WebSocket]] = {}
        # int is the location_id

    async def connect(self, websocket: WebSocket, location_id: int):
        if location_id not in self.connections:
            self.connections[location_id] = []

        self.connections[location_id].append(websocket)
        print(
            "[WS_FRONTEND_CONNECTED] "
            f"location_id={location_id} "
            f"client={getattr(websocket, 'client', None)} "
            f"total_connections={len(self.connections[location_id])}"
        )

    async def disconnect(self, websocket: WebSocket, location_id: int):
        if (
            location_id in self.connections
            and websocket in self.connections[location_id]
        ):
            self.connections[location_id].remove(websocket)
            print(
                "[WS_FRONTEND_DISCONNECTED] "
                f"location_id={location_id} "
                f"client={getattr(websocket, 'client', None)} "
                f"total_connections={len(self.connections[location_id])}"
            )

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

    async def broadcast_to_location(self, message: dict, location_id: int) -> int:

        if location_id not in self.connections:
            if message.get("type") == "camera_update":
                print(
                    "[WS_FRAME_BROADCAST] "
                    f"location_id={location_id} delivered_clients=0 reason=no_frontend_ws_clients"
                )
            return 0  # No connections for this location

        disconnected = []
        sent_count = 0
        for ws in self.connections[location_id][:]:  # iterate over a copy of the list
            try:
                # Check application state if possible (FastAPI/Starlette specific)
                if ws.client_state.name != "CONNECTED":
                    disconnected.append(ws)
                    continue

                await ws.send_json(message)
                sent_count += 1

                if message.get("type") == "camera_update":
                    image_b64 = message.get("data", {}).get("image")
                    print(
                        "[WS_FRAME_SENT] "
                        f"location_id={location_id} "
                        f"client={getattr(ws, 'client', None)} "
                        f"image_b64_chars={len(image_b64) if isinstance(image_b64, str) else 0}"
                    )
            except RuntimeError:
                # This catches 'Unexpected ASGI message' (Client already closed)
                disconnected.append(ws)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.append(ws)

        for ws in disconnected:
            location_connections = self.connections.get(location_id)
            if not location_connections:
                break

            if ws in location_connections:
                location_connections.remove(ws)

        if location_id in self.connections and not self.connections[location_id]:
            del self.connections[location_id]

        if message.get("type") == "camera_update":
            print(
                "[WS_FRAME_BROADCAST] "
                f"location_id={location_id} delivered_clients={sent_count}"
            )

        return sent_count


ws_manager = ConnectionManager()
