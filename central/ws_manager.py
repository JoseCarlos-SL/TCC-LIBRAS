# central/ws_manager.py
"""Gerenciador de conexões WebSocket para transmissão em tempo real."""

import json
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Mantém a lista de clientes WebSocket conectados e transmite mensagens."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Aceita e registra uma nova conexão WebSocket."""
        await websocket.accept()
        self._connections.append(websocket)
        logger.info("Cliente WS conectado. Total: %d", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove uma conexão encerrada da lista."""
        self._connections.remove(websocket)
        logger.info("Cliente WS desconectado. Total: %d", len(self._connections))

    async def broadcast(self, payload: dict) -> None:
        """Envia um payload JSON para todos os clientes conectados."""
        message = json.dumps(payload, default=str)
        mortos: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                mortos.append(ws)
        for ws in mortos:
            self._connections.remove(ws)


# Instância global compartilhada entre os routers
manager = ConnectionManager()
