import datetime
import time
import uuid
from typing import Any, Callable, Dict, List

import orjson
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from senweaver.logger import logger

app = FastAPI()


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_ids: Dict[str, str] = {}
        self.subscribers: Dict[str, List[Callable]] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        self.active_connections[client_id] = websocket
        self.connection_ids[client_id] = f"{client_id}-{uuid.uuid4()}"

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
        self.connection_ids.pop(client_id, None)

    async def close_connection(self, client_id: str, code: int, reason: str):
        if websocket := self.active_connections[client_id]:
            try:
                await websocket.close(code=code, reason=reason)
                self.disconnect(client_id)
            except RuntimeError as exc:
                # This is to catch the following error:
                #  Unexpected ASGI message 'websocket.close', after sending 'websocket.close'
                if "after sending" in str(exc):
                    logger.error(f"Error closing connection: {exc}")

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

    async def broadcast_json(self, message: Any):
        json_msg = orjson.dumps(message).decode("utf-8")
        for connection in self.active_connections.values():
            await connection.send_text(json_msg)

    async def send_message(self, client_id: str, message: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def send_json(self, client_id: str, message: Any):
        websocket = self.active_connections[client_id]
        await websocket.send_json(message)

    def subscribe(self, topic: str, callback: Callable):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)

    async def publish(self, topic: str, data: dict):
        if topic in self.subscribers:
            for callback in self.subscribers[topic]:
                await callback(data)

    async def process_message(
        self, websocket: WebSocket, client_id: str, payload: Dict
    ):
        action = payload.get("action")
        if not action or action not in ["userinfo", "push_message", "chat_message"]:
            raise RuntimeError(f"action error {client_id}")
        data = payload.get("data", {})
        if action == "chat_message":
            data["id"] = websocket.user.id
            data["time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            data["username"] = websocket.user.username
            await self.send_data(client_id, "chat_message", data)
            text = data.get("text")
            if text.startswith("@"):
                target = text.split(" ")[0].split("@")
                if len(target) > 1:
                    target = target[1]
                    try:
                        push_message = {
                            "id": websocket.user.id,
                            "username": "其他人",
                            "text": f"用户 {websocket.user.username} 发来一条消息",
                            "title": f"用户 {websocket.user.username} 发来一条消息",
                            "message": text,
                            "level": "info",
                            "notice_type": {"label": "聊天室", "value": 0},
                            "message_type": "chat_message",
                            "time": datetime.datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S.%f"
                            ),
                        }
                        # Send message to WebSocket
                        await self.send_data(client_id, "chat_message", push_message)
                        await self.send_data(client_id, "push_message", data)

                    except Exception as e:
                        logger.error(e)
        elif action == "userinfo":
            await self.send_data(
                client_id,
                action,
                {
                    "userinfo": {
                        "username": websocket.user.username,
                        "nickname": websocket.user.nickname,
                        "gender": websocket.user.gender,
                        "id": websocket.user.id,
                    },
                    "id": websocket.user.id,
                },
            )
        elif action == "push_message":
            # 系统推送消息到客户端，推送消息格式如下：{"time": 1709714533.5625794, "action": "push_message", "data": {"message": 11}}
            await self.send_data(client_id, "push_message", data)

    async def send_data(self, client_id: str, action, content, close=False):
        data = {"time": time.time(), "action": action, "data": content}
        return await self.send_json(client_id, data)

    async def handle_websocket(self, client_id: str, websocket: WebSocket):
        await self.connect(client_id, websocket)
        try:
            while True:
                json_payload = await websocket.receive_json()
                if isinstance(json_payload, str):
                    payload = orjson.loads(json_payload)
                elif isinstance(json_payload, dict):
                    payload = json_payload

                await self.process_message(websocket, client_id, payload)
        except Exception as exc:
            # Handle any exceptions that might occur
            logger.exception(f"Error handling websocket: {exc}")
            if websocket.client_state == WebSocketState.CONNECTED:
                await self.close_connection(
                    client_id=client_id,
                    code=status.WS_1011_INTERNAL_ERROR,
                    reason=str(exc),
                )
            elif websocket.client_state == WebSocketState.DISCONNECTED:
                self.disconnect(client_id)

        finally:
            try:
                # first check if the connection is still open
                if websocket.client_state == WebSocketState.CONNECTED:
                    await self.close_connection(
                        client_id=client_id,
                        code=status.WS_1000_NORMAL_CLOSURE,
                        reason="Client disconnected",
                    )
            except Exception as exc:
                logger.error(f"Error closing connection: {exc}")
            self.disconnect(client_id)


manager = WebSocketManager()
