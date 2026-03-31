from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Signal

class ClickableLabel(QLabel):
    clicked = Signal(int, int)

    def mousePressEvent(self, event):
        pos = event.position()
        self.clicked.emit(int(pos.x()), int(pos.y()))
        super().mousePressEvent(event)
