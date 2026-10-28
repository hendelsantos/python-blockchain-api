"""Canal WebSocket usado pelo dashboard e observadores da rede."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class RealtimeManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, event: dict[str, object]) -> None:
        stale: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(event)
            except RuntimeError:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


@router.websocket("/ws/blocks")
async def blockchain_events(websocket: WebSocket) -> None:
    manager: RealtimeManager = websocket.app.state.realtime
    blockchain = websocket.app.state.blockchain
    await manager.connect(websocket)
    await websocket.send_json(
        {
            "type": "chain_snapshot",
            "length": len(blockchain.chain),
            "valid": blockchain.is_valid(),
        }
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
