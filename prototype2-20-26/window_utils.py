from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFileDialog


def center_on_primary_screen(window) -> None:
    screen = QGuiApplication.primaryScreen().availableGeometry()
    geometry = window.frameGeometry()
    window.move(
        screen.center().x() - geometry.width() // 2,
        screen.center().y() - geometry.height() // 2,
    )


def pick_directory(parent, title: str = "Select a Directory") -> str | None:
    selected = QFileDialog.getExistingDirectory(parent, title)
    if not selected:
        return None
    return str(Path(selected))
