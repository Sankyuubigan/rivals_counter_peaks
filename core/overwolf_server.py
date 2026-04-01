# File: core/overwolf_server.py
import asyncio
import websockets
import json
import logging
from PySide6.QtCore import QThread, Signal, QObject

class OverwolfServerWorker(QObject):
    data_received = Signal(dict)
    client_connected = Signal()
    client_disconnected = Signal()

    def __init__(self, port=8765):
        super().__init__()
        self.port = port
        self.loop = None

    async def handler(self, websocket):
        logging.info(f"[OverwolfServer] Overwolf клиент подключился: {websocket.remote_address}")
        self.client_connected.emit()
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    self.data_received.emit(data)
                except json.JSONDecodeError:
                    logging.error(f"[OverwolfServer] Получен некорректный JSON: {message}")
        except websockets.exceptions.ConnectionClosed:
            logging.info("[OverwolfServer] Overwolf клиент отключился")
        finally:
            self.client_disconnected.emit()

    async def start_server(self):
        self.loop = asyncio.get_running_loop()
        try:
            async with websockets.serve(self.handler, "localhost", self.port):
                logging.info(f"[OverwolfServer] WebSocket сервер запущен на ws://localhost:{self.port}")
                await asyncio.Future()
        except Exception as e:
            logging.error(f"[OverwolfServer] Ошибка запуска сервера: {e}")

class OverwolfServer(QThread):
    def __init__(self, port=8765, parent=None):
        super().__init__(parent)
        self.worker = OverwolfServerWorker(port)
        self.data_received = self.worker.data_received
        self.client_connected = self.worker.client_connected
        self.client_disconnected = self.worker.client_disconnected

    def run(self):
        asyncio.run(self.worker.start_server())