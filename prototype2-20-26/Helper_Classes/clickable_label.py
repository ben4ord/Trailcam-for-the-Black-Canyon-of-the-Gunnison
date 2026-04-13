from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Signal

class ClickableLabel(QLabel):
    clicked = Signal(int, int)
    resized = Signal()

    def mousePressEvent(self, event):
        pos = event.position()
        self.clicked.emit(int(pos.x()), int(pos.y()))
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()
