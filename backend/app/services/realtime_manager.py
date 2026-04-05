import json

from fastapi import WebSocket

from app.services.analysis_pipeline import AnalysisPipeline


class RealtimeManager:
    def __init__(self) -> None:
        self.pipeline = AnalysisPipeline()
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def push_snapshot(self, timeframe: str = "15m") -> None:
        if not self.connections:
            return

        payload = (await self.pipeline.analyze(timeframe)).model_dump()
        message = json.dumps(payload, default=str)
        stale_connections: list[WebSocket] = []
        for connection in self.connections:
            try:
                await connection.send_text(message)
            except Exception:
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)
