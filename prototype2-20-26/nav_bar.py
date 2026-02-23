from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QEvent, QPoint, Signal
import qtawesome as qta


class NavBar(QWidget):
    homeClicked = Signal()
    updateLabelsClicked = Signal()
    newFolderClicked = Signal()

    def __init__(self, parent_window):
        super().__init__()

        self.parent_window = parent_window
        self._drag_active = False
        self._drag_position = QPoint()
        self._press_pos = QPoint()

        self.setObjectName("navBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.GlobalColor.transparent)
        self.setPalette(palette)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Navigation buttons
        # Icons can be found here: https://fontawesome.com/v6/search?ic=free-collection
        self.home_btn = QPushButton()
        self.home_btn.setIcon(qta.icon('fa6s.house'))
        self.home_btn.setToolTip("Home")
        self.home_btn.clicked.connect(self.homeClicked.emit)

        self.update_labels_btn = QPushButton()
        self.update_labels_btn.setIcon(qta.icon('fa6s.file-pen'))
        self.update_labels_btn.setToolTip("Update Class Labels")
        self.update_labels_btn.clicked.connect(self.updateLabelsClicked.emit)

        self.new_folder_btn = QPushButton()
        self.new_folder_btn.setIcon(qta.icon('fa6s.folder'))
        self.new_folder_btn.setToolTip("Select New Directory")
        self.new_folder_btn.clicked.connect(self.newFolderClicked.emit)

        layout.addWidget(self.home_btn)
        layout.addWidget(self.update_labels_btn)
        layout.addWidget(self.new_folder_btn)
        layout.addStretch()

        # Window controls
        self.min_btn = QPushButton()
        self.min_btn.setIcon(qta.icon('fa6s.minus'))
        self.min_btn.setToolTip("Minimize")
        self.min_btn.clicked.connect(self.parent_window.showMinimized)

        self.max_btn = QPushButton()
        self.max_btn.setIcon(qta.icon('fa6s.window-maximize'))
        self.max_btn.clicked.connect(self.toggle_max_restore)

        self.close_btn = QPushButton()
        self.close_btn.setIcon(qta.icon('fa6s.xmark'))
        self.close_btn.setToolTip("Close")
        self.close_btn.clicked.connect(self.parent_window.close)

        for btn in (self.min_btn, self.max_btn, self.close_btn):
            btn.setFixedWidth(36)
            layout.addWidget(btn)

        self.installEventFilter(self)

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


    def toggle_max_restore(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.max_btn.setIcon(qta.icon('fa6s.window-maximize'))
            self.max_btn.setToolTip("Restore")
        else:
            self.parent_window.showMaximized()
            self.max_btn.setIcon(qta.icon('fa6s.window-restore'))
            self.max_btn.setToolTip("Maximize")

    def eventFilter(self, obj, event):
        if obj is self:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                self.toggle_max_restore()
                return True

            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                clicked_child = self.childAt(event.position().toPoint())
                if isinstance(clicked_child, QPushButton):
                    return False

                self._drag_active = True
                self._press_pos = event.position().toPoint()
                self._drag_position = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
                return True

            if event.type() == QEvent.Type.MouseMove and self._drag_active:
                self.parent_window.move(event.globalPosition().toPoint() - self._drag_position)
                return True

            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_active = False
                return True

        return super().eventFilter(obj, event)