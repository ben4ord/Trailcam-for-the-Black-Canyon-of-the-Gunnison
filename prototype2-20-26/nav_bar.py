from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSizePolicy
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

        self.setFixedHeight(35)

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
                global_pos = event.globalPosition().toPoint()

                if self.parent_window.isMaximized() or self.parent_window.isFullScreen():

                    normal_rect = self.parent_window.normalGeometry()

                    target_width = normal_rect.width() if normal_rect.width() > 0 else self.parent_window.width()

                    self.parent_window.showNormal()

                    press_ratio_x = self._press_pos.x() / max(1, self.width())

                    anchor_x = int(press_ratio_x * target_width)
                    anchor_x = max(0, min(anchor_x, max(0, target_width - 1)))

                    anchor_y = max(
                        0,
                        min(
                            self._press_pos.y(),
                            max(0, self.height() - 1)
                        )
                    )

                    self.parent_window.move(
                        global_pos.x() - anchor_x,
                        global_pos.y() - anchor_y
                    )

                    self._drag_position = global_pos - self.parent_window.frameGeometry().topLeft()

                    self.max_btn.setIcon(qta.icon('fa6s.window-maximize'))
                    self.max_btn.setToolTip("Maximize")

                    return True

                self.parent_window.move(global_pos - self._drag_position)
                return True

            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_active = False
                return True

        return super().eventFilter(obj, event)
    
    def set_button_visibility(self, home=True, update_labels=True, new_folder=True):
        self.home_btn.setVisible(home)
        self.update_labels_btn.setVisible(update_labels)
        self.new_folder_btn.setVisible(new_folder)