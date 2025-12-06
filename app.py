import asyncio
import json
import pathlib
from http import HTTPStatus
from typing import Dict, Set

import websockets

ROOT = pathlib.Path(__file__).parent
STATIC_DIR = ROOT / "static"

Connected = Set[websockets.WebSocketServerProtocol]


def load_static_file(path: pathlib.Path) -> bytes:
    if not path.exists() or not path.is_file():
        return b""
    return path.read_bytes()


def content_type_for(path: pathlib.Path) -> str:
    if path.suffix == ".html":
        return "text/html; charset=utf-8"
    if path.suffix == ".css":
        return "text/css; charset=utf-8"
    if path.suffix == ".js":
        return "application/javascript; charset=utf-8"
    if path.suffix in {".svg", ".png", ".jpg", ".jpeg", ".gif"}:
        return f"image/{path.suffix.lstrip('.')}"
    return "application/octet-stream"


class SkySprintServer:
    def __init__(self) -> None:
        self.connections: Connected = set()
        self.scores: Dict[str, int] = {}
        self.next_id = 1
        self.lock = asyncio.Lock()

    async def register(self, websocket: websockets.WebSocketServerProtocol) -> str:
        async with self.lock:
            player_id = f"Pilot-{self.next_id:03d}"
            self.next_id += 1
            self.connections.add(websocket)
            self.scores.setdefault(player_id, 0)
        await websocket.send(
            json.dumps(
                {
                    "type": "welcome",
                    "playerId": player_id,
                    "scores": self.scores,
                }
            )
        )
        await self.broadcast_state()
        return player_id

    async def unregister(self, websocket: websockets.WebSocketServerProtocol) -> None:
        async with self.lock:
            self.connections.discard(websocket)
        await self.broadcast_state()

    async def broadcast_state(self) -> None:
        if not self.connections:
            return
        message = json.dumps({"type": "scores", "scores": self.scores})
        await asyncio.gather(*(ws.send(message) for ws in self.connections))

    async def handle_action(self, player_id: str) -> None:
        async with self.lock:
            self.scores[player_id] = self.scores.get(player_id, 0) + 1
        await self.broadcast_state()

    async def handler(self, websocket: websockets.WebSocketServerProtocol):
        player_id = await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "boost":
                    await self.handle_action(player_id)
        finally:
            await self.unregister(websocket)


def build_static_response(path: str):
    if path == "/":
        file_path = STATIC_DIR / "index.html"
    elif path.startswith("/static/"):
        file_path = STATIC_DIR / path.removeprefix("/static/")
    else:
        return None

    body = load_static_file(file_path)
    if not body:
        return None

    headers = [
        ("Content-Type", content_type_for(file_path)),
        ("Content-Length", str(len(body))),
    ]
    return HTTPStatus.OK, headers, body


async def process_request(path, request_headers):
    response = build_static_response(path)
    if response is None:
        return None
    status, headers, body = response
    return status, headers, body


async def main():
    server = SkySprintServer()
    async with websockets.serve(
        server.handler, "0.0.0.0", 8000, process_request=process_request
    ):
        print("SkySprint server running on http://localhost:8000")
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
