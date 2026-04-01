# File: core/overwolf_server.py
import asyncio
import websockets
import json
import logging
from PySide6.QtCore import QThread, Signal, QObject

class OverwolfServerWorker(QObject):
    """Рабочий класс для обработки WebSocket соединения в отдельном потоке."""
    data_received = Signal(dict)

    def __init__(self, port=8765):
        super().__init__()
        self.port = port
        self.loop = None

    async def handler(self, websocket):
        logging.info(f"[OverwolfServer] Overwolf клиент подключился: {websocket.remote_address}")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logging.debug(f"[OverwolfServer] Получены данные: {data}")
                    self.data_received.emit(data)
                except json.JSONDecodeError:
                    logging.error(f"[OverwolfServer] Получен некорректный JSON: {message}")
        except websockets.exceptions.ConnectionClosed:
            logging.info("[OverwolfServer] Overwolf клиент отключился")

    async def start_server(self):
        self.loop = asyncio.get_running_loop()
        try:
            async with websockets.serve(self.handler, "localhost", self.port):
                logging.info(f"[OverwolfServer] WebSocket сервер запущен на ws://localhost:{self.port}")
                await asyncio.Future()  # Работаем бесконечно
        except Exception as e:
            logging.error(f"[OverwolfServer] Ошибка запуска сервера: {e}")

class OverwolfServer(QThread):
    """Поток, в котором крутится asyncio event loop для WebSocket сервера."""
    def __init__(self, port=8765, parent=None):
        super().__init__(parent)
        self.worker = OverwolfServerWorker(port)
        # Пробрасываем сигнал наверх
        self.data_received = self.worker.data_received

    def run(self):
        # Запускаем асинхронный цикл в отдельном потоке Qt
        asyncio.run(self.worker.start_server())