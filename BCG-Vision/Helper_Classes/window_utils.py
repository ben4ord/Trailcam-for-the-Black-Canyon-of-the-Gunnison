import sys
from pathlib import Path
import ctypes

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFileDialog

# Windows hit-test codes for resize edges
_HT = {
    "l":  10,  # HTLEFT
    "r":  11,  # HTRIGHT
    "t":  12,  # HTTOP
    "tl": 13,  # HTTOPLEFT
    "tr": 14,  # HTTOPRIGHT
    "b":  15,  # HTBOTTOM
    "bl": 16,  # HTBOTTOMLEFT
    "br": 17,  # HTBOTTOMRIGHT
}


class ResizableMixin:
    """Adds drag-to-resize on all edges and corners for FramelessWindowHint windows.

    On Windows: uses nativeEvent (WM_NCHITTEST) so the OS handles the cursor
    and the actual resize drag natively — no child-widget event-blocking issues.
    On other platforms: falls back to mouse-event tracking with setMouseTracking.
    """

    _GRIP = 8  # px from edge that activates resize

    # ------------------------------------------------------------------
    # Windows native path
    # ------------------------------------------------------------------
    def nativeEvent(self, event_type, message):
        if sys.platform == "win32" and event_type == b"windows_generic_MSG":
            from ctypes import wintypes
            from PySide6.QtGui import QCursor
            msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
            if msg.message == 0x0083 and msg.wParam:  # WM_NCCALCSIZE
                # Tell Windows the client area fills the entire window rect,
                # suppressing the visible thick frame border.
                return True, 0
            if msg.message == 0x0084:  # WM_NCHITTEST
                pos = self.mapFromGlobal(QCursor.pos())
                edge = self._resize_edge_at(pos)
                if edge:
                    return True, _HT[edge]
        return super().nativeEvent(event_type, message)

    # ------------------------------------------------------------------
    # Windows: restore WS_THICKFRAME so the OS can execute the resize drag.
    # FramelessWindowHint strips this flag, which means WM_NCHITTEST hit codes
    # are delivered but Windows never enters its resize loop without it.
    # WM_NCCALCSIZE returning 0 keeps the client area filling the full window
    # so no visible frame border appears.
    # ------------------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            GWL_STYLE    = -16
            WS_THICKFRAME = 0x00040000
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_THICKFRAME)
        else:
            self.setMouseTracking(True)
            if self.centralWidget():
                self.centralWidget().setMouseTracking(True)

    def mousePressEvent(self, event):
        if sys.platform != "win32" and event.button() == Qt.MouseButton.LeftButton:
            edge = self._resize_edge_at(event.position().toPoint())
            if edge:
                self._rz_edge = edge
                self._rz_start = event.globalPosition().toPoint()
                self._rz_geo = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if sys.platform != "win32":
            if (
                hasattr(self, "_rz_edge")
                and self._rz_edge
                and event.buttons() & Qt.MouseButton.LeftButton
            ):
                self._apply_resize(event.globalPosition().toPoint())
                event.accept()
                return
            self.setCursor(self._cursor_for_edge(self._resize_edge_at(event.position().toPoint())))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if sys.platform != "win32":
            self._rz_edge = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _resize_edge_at(self, pos):
        g = self._GRIP
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        left = x < g
        right = x > w - g
        top = y < g
        bottom = y > h - g
        if top and left:   return "tl"
        if top and right:  return "tr"
        if bottom and left:  return "bl"
        if bottom and right: return "br"
        if left:   return "l"
        if right:  return "r"
        if top:    return "t"
        if bottom: return "b"
        return None

    def _cursor_for_edge(self, edge):
        return {
            "tl": Qt.CursorShape.SizeFDiagCursor,
            "br": Qt.CursorShape.SizeFDiagCursor,
            "tr": Qt.CursorShape.SizeBDiagCursor,
            "bl": Qt.CursorShape.SizeBDiagCursor,
            "l":  Qt.CursorShape.SizeHorCursor,
            "r":  Qt.CursorShape.SizeHorCursor,
            "t":  Qt.CursorShape.SizeVerCursor,
            "b":  Qt.CursorShape.SizeVerCursor,
        }.get(edge, Qt.CursorShape.ArrowCursor)

    def _apply_resize(self, global_pos):
        from PySide6.QtCore import QRect
        delta = global_pos - self._rz_start
        geo = QRect(self._rz_geo)
        edge = self._rz_edge
        if "r" in edge: geo.setRight(geo.right() + delta.x())
        if "b" in edge: geo.setBottom(geo.bottom() + delta.y())
        if "l" in edge: geo.setLeft(geo.left() + delta.x())
        if "t" in edge: geo.setTop(geo.top() + delta.y())
        min_w = max(self.minimumWidth(), 200)
        min_h = max(self.minimumHeight(), 100)
        if geo.width() >= min_w and geo.height() >= min_h:
            self.setGeometry(geo)


# Function to center the application based on the users screen shape
def center_on_primary_screen(window) -> None:
    screen = QGuiApplication.primaryScreen().availableGeometry()
    geometry = window.frameGeometry()
    window.move(
        screen.center().x() - geometry.width() // 2,
        screen.center().y() - geometry.height() // 2,
    )


# Function to change directories (this button exists in multiple places so we made it a general function)
def pick_directory(parent, title: str = "Select a Directory") -> str | None:
    selected = QFileDialog.getExistingDirectory(parent, title)
    if not selected:
        return None
    return str(Path(selected))
