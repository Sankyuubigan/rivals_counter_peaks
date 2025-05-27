# File: core/window_drag_handler.py
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget, QPushButton, QSlider 
import logging

class WindowDragHandler:
    def __init__(self, window: QWidget, top_frame_provider: callable):
        self.window = window
        self.top_frame_provider = top_frame_provider 
        self._mouse_pressed = False
        self._old_pos: QPoint | None = None

    def mousePressEvent(self, event: QMouseEvent) -> bool:
        is_min_mode = hasattr(self.window, 'mode') and self.window.mode == "min"
        top_frame = self.top_frame_provider()
        logging.debug(f"[DragHandler.press] Event pos (rel to window): {event.pos()}, Global: {event.globalPosition().toPoint()}, MinMode: {is_min_mode}")
        if top_frame:
            logging.debug(f"[DragHandler.press] TopFrame geom (rel to parent): {top_frame.geometry()}, Mapped global click to top_frame local: {top_frame.mapFromGlobal(event.globalPosition().toPoint())}")

        if is_min_mode and top_frame and top_frame.geometry().contains(top_frame.mapFromGlobal(event.globalPosition().toPoint())):
            logging.debug("[DragHandler.press] Click is within top_frame geometry in min_mode.")
            if event.button() == Qt.MouseButton.LeftButton:
                top_frame_local_pos = top_frame.mapFromGlobal(event.globalPosition().toPoint())
                child_widget_at_click = top_frame.childAt(top_frame_local_pos)
                logging.debug(f"[DragHandler.press] Click at top_frame local coords: {top_frame_local_pos}. Child at click: {type(child_widget_at_click).__name__ if child_widget_at_click else 'None'}")

                if child_widget_at_click and child_widget_at_click.parentWidget() == top_frame:
                    if child_widget_at_click.isEnabled() and child_widget_at_click.isVisible():
                        if isinstance(child_widget_at_click, (QPushButton, QSlider)):
                           logging.debug(f"[DragHandler.press] Click on interactive child '{child_widget_at_click.objectName() if hasattr(child_widget_at_click, 'objectName') else type(child_widget_at_click).__name__}'. Not starting drag.")
                           self._mouse_pressed = False 
                           return False 

                self._mouse_pressed = True
                self._old_pos = event.globalPosition().toPoint()
                logging.debug(f"[DragHandler.press] Drag started. Old pos: {self._old_pos}")
                event.accept()
                return True
        self._mouse_pressed = False
        logging.debug("[DragHandler.press] Conditions not met for drag start or event not accepted by drag logic.")
        return False

    def mouseMoveEvent(self, event: QMouseEvent) -> bool:
        is_min_mode = hasattr(self.window, 'mode') and self.window.mode == "min"
        if is_min_mode and self._mouse_pressed and self._old_pos is not None:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.window.move(self.window.pos() + delta)
            self._old_pos = event.globalPosition().toPoint()
            event.accept()
            return True
        return False

    def mouseReleaseEvent(self, event: QMouseEvent) -> bool:
        is_min_mode = hasattr(self.window, 'mode') and self.window.mode == "min"
        if is_min_mode and self._mouse_pressed and event.button() == Qt.MouseButton.LeftButton:
            self._mouse_pressed = False
            self._old_pos = None
            logging.debug("[DragHandler.release] Dragging stopped.")
            event.accept()
            return True
        logging.debug("[DragHandler.release] Conditions not met for drag release handling or event not accepted by drag logic.")
        return False
