from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QGridLayout
)

from PySide6.QtCore import Qt, QEvent, QPoint

import qtawesome as qta


class LabelUpdater(QMainWindow):
    def __init__(self, drive):
        super().__init__()
        
        self.drive = drive
        self._drag_active = False
        self._drag_position = QPoint()
        self._press_pos = QPoint()

        self.setGeometry(100, 100, 600, 400) # Made it slightly larger to fit an image
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)


        self.title_bar = QWidget()
        self.title_bar.setObjectName("titleBar")
        self.setStyleSheet("""
        #titleBar {
            background-color: #1f2a36;   /* bar color */
            border-bottom: 1px solid #3b4b5f;
        }
        #titleBar QLabel {
            color: #ffffff;
            font-weight: 600;
        }
        #titleBar QPushButton {
            background: transparent;
            color: #ffffff;
            border: none;
            padding: 4px 8px;
        }
        #titleBar QPushButton:hover {
            background-color: #2f3e4f;
        }
        """)

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(8, 4, 8, 4)
        title_layout.setSpacing(6)


        self.home_btn = QPushButton()
        self.home_btn.setIcon(qta.icon('fa6s.house'))
        self.home_btn.setToolTip('Home')
        self.home_btn.clicked.connect(self.menu_window)
        self.home_btn.setFlat(True)

        self.min_btn = QPushButton()
        self.min_btn.setIcon(qta.icon('fa6s.minus'))
        self.min_btn.setToolTip('Minimize')
        self.min_btn.clicked.connect(self.showMinimized)
        self.min_btn.setFixedWidth(36)

        self.max_btn = QPushButton()
        self.max_btn.setIcon(qta.icon('fa6s.window-maximize'))
        self.max_btn.setToolTip('Maximize')
        self.max_btn.clicked.connect(self.toggle_max_restore)
        self.max_btn.setFixedWidth(36)

        self.close_btn = QPushButton()
        self.close_btn.setIcon(qta.icon('fa6s.xmark'))
        self.close_btn.setToolTip('Close')
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setFixedWidth(36)


        title_layout.addWidget(self.home_btn)
        title_layout.addStretch()

        title_layout.addWidget(self.min_btn)
        title_layout.addWidget(self.max_btn)
        title_layout.addWidget(self.close_btn)
        self.title_bar.installEventFilter(self)

        layout.addWidget(self.title_bar, 0, 0, 1, 5)

    
    def toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setIcon(qta.icon('fa6s.window-maximize'))
            self.max_btn.setToolTip('Maximize')
        else:
            self.showMaximized()
            self.max_btn.setIcon(qta.icon('fa6s.window-restore'))
            self.max_btn.setToolTip('Restore')

    def eventFilter(self, obj, event):
        if obj is self.title_bar:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                self.toggle_max_restore()
                return True
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                clicked_child = self.title_bar.childAt(event.position().toPoint())
                if clicked_child in (
                    self.home_btn,
                    self.min_btn,
                    self.max_btn,
                    self.close_btn,
                ):
                    return False
                self._drag_active = True
                self._press_pos = event.position().toPoint()
                self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

                return True
            if event.type() == QEvent.Type.MouseMove and self._drag_active:
                global_pos = event.globalPosition().toPoint()
                if self.isMaximized() or self.isFullScreen():
                    # Use pre-maximize geometry to avoid transient width values after showNormal().
                    normal_rect = self.normalGeometry()
                    target_width = normal_rect.width() if normal_rect.width() > 0 else self.width()

                    self.showNormal()
                    # Keep cursor anchored to the same relative point on the title bar after restore.
                    press_ratio_x = self._press_pos.x() / max(1, self.title_bar.width())
                    anchor_x = int(press_ratio_x * target_width)
                    anchor_x = max(0, min(anchor_x, max(0, target_width - 1)))
                    anchor_y = max(0, min(self._press_pos.y(), max(0, self.title_bar.height() - 1)))
                    self.move(global_pos.x() - anchor_x, global_pos.y() - anchor_y)

                    self._drag_position = global_pos - self.frameGeometry().topLeft()
                    self.max_btn.setIcon(qta.icon('fa6s.window-maximize'))
                    self.max_btn.setToolTip('Maximize')
                    return True

                self.move(global_pos - self._drag_position)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_active = False
                return True
        return super().eventFilter(obj, event)
    
    def menu_window(self):
        from menu import MenuWindow
        self.menuWindow = MenuWindow(self.drive)
        self.menuWindow.show()
        self.close()