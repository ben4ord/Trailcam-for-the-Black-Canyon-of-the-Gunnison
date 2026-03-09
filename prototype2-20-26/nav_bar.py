from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QEvent, QPoint, Signal, QTimer
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QEvent, QPoint, Signal, QTimer

import qtawesome as qta
from training_session import get_training_session
from training_session import get_training_session


class NavBar(QWidget):
    homeClicked = Signal()
    updateLabelsClicked = Signal()
    newFolderClicked = Signal()

    def __init__(self, parent_window):
        super().__init__()

        self.parent_window = parent_window
        self.training_session = get_training_session()
        self.drag_active = False
        self.drag_position = QPoint()
        self.press_pos = QPoint()

        self.setObjectName("navBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.setFixedHeight(35)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Navigation buttons (Top left)
        # Icons can be found here: https://fontawesome.com/v6/search?ic=free-collection
        # Home button
        self.home_btn = QPushButton()
        self.home_btn.setIcon(qta.icon('fa6s.house'))
        self.home_btn.setToolTip("Home")
        self.home_btn.clicked.connect(self.homeClicked.emit)

        # Update labels button
        self.update_labels_btn = QPushButton()
        self.update_labels_btn.setIcon(qta.icon('fa6s.file-pen'))
        self.update_labels_btn.setToolTip("Update Class Labels")
        self.update_labels_btn.clicked.connect(self.updateLabelsClicked.emit)

        # Select new folder button
        self.new_folder_btn = QPushButton()
        self.new_folder_btn.setIcon(qta.icon('fa6s.folder'))
        self.new_folder_btn.setToolTip("Select New Directory")
        self.new_folder_btn.clicked.connect(self.newFolderClicked.emit)

        # Training status button
        self.training_status_btn = QPushButton("Training: Idle")
        self.training_status_btn.setToolTip("Current model training status. Click to open training window.")
        self.training_status_btn.clicked.connect(self.open_training_window)
        self.training_status_btn.setStyleSheet(
            "padding: 2px 8px; border-radius: 8px; background: #2d3a47; color: #b9c4d0;"
        )

        layout.addWidget(self.home_btn)
        layout.addWidget(self.update_labels_btn)
        layout.addWidget(self.new_folder_btn)
        layout.addWidget(self.training_status_btn)

        layout.addWidget(self.training_status_btn)

        layout.addStretch()

        # Window controls (Top right)
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

        self.training_status_timer = QTimer(self)
        self.training_status_timer.setInterval(1000)
        self.training_status_timer.timeout.connect(self.refresh_training_status)
        self.training_status_timer.start()
        self.refresh_training_status()

        self.update()


    # function to modify the size of the screen based on previous state
    # if window already max, then it shrinks. If window is shrunk then it maximizes it
    def toggle_max_restore(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.max_btn.setIcon(qta.icon('fa6s.window-maximize'))
            self.max_btn.setToolTip("Restore")
        else:
            self.parent_window.showMaximized()
            self.max_btn.setIcon(qta.icon('fa6s.window-restore'))
            self.max_btn.setToolTip("Maximize")

    # Check what the mouse click actually is (double click, click & drag, etc.)
    def eventFilter(self, obj, event):
        if obj is self:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                self.toggle_max_restore()
                return True

            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                clicked_child = self.childAt(event.position().toPoint())
                if isinstance(clicked_child, QPushButton):
                    return False

                self.drag_active = True
                self.press_pos = event.position().toPoint()
                self.drag_position = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
                return True

            # If dragging the nav bar, we need to shrink it accordingly and also move the
            # window according to the mouse position
            if event.type() == QEvent.Type.MouseMove and self.drag_active:
                global_pos = event.globalPosition().toPoint()

                if self.parent_window.isMaximized() or self.parent_window.isFullScreen():

                    normal_rect = self.parent_window.normalGeometry()

                    target_width = normal_rect.width() if normal_rect.width() > 0 else self.parent_window.width()

                    self.parent_window.showNormal()

                    press_ratio_x = self.press_pos.x() / max(1, self.width())

                    anchor_x = int(press_ratio_x * target_width)
                    anchor_x = max(0, min(anchor_x, max(0, target_width - 1)))

                    anchor_y = max(
                        0,
                        min(
                            self.press_pos.y(),
                            max(0, self.height() - 1)
                        )
                    )

                    self.parent_window.move(
                        global_pos.x() - anchor_x,
                        global_pos.y() - anchor_y
                    )

                    self.drag_position = global_pos - self.parent_window.frameGeometry().topLeft()

                    self.max_btn.setIcon(qta.icon('fa6s.window-maximize'))
                    self.max_btn.setToolTip("Maximize")

                    return True

                self.parent_window.move(global_pos - self.drag_position)
                return True

            # stop tracking the window movement based on the mouse if we are no longer holding down the click
            if event.type() == QEvent.Type.MouseButtonRelease:
                self.drag_active = False
                return True

        return super().eventFilter(obj, event)
    
    # certain windows don't need all the nav bar buttons visible
    # this function allows them to decide which ones they want to see (all are true by default)
    def set_button_visibility(self, home=True, update_labels=True, new_folder=True, training_status=True):
        self.home_btn.setVisible(home)
        self.update_labels_btn.setVisible(update_labels)
        self.new_folder_btn.setVisible(new_folder)
        self.training_status_btn.setVisible(training_status)

    # we need to modify the training status based on the session tracking for training
    # this function will refresh the training status based on the snapshot generated (this is explained more in the training_session file)
    def refresh_training_status(self):
        snapshot = self.training_session.snapshot()
        has_drive = bool(self.resolve_drive())
        self.training_status_btn.setEnabled(has_drive)
        if has_drive:
            self.training_status_btn.setToolTip(
                "Current model training status. Click to open training window."
            )
        else:
            self.training_status_btn.setToolTip("Training status. Select/open a dataset first.")

        if snapshot["running"]:
            self.training_status_btn.setText("Training: Running")
            self.training_status_btn.setStyleSheet(
                "padding: 2px 8px; border-radius: 8px; background: #1f4f2e; color: #d3f5dc;"
            )
            return

        # check the status from the snapshot generated so we know what to set the status on the navbar as
        status = str(snapshot["status"] or "")
        if status == "Training complete":
            self.training_status_btn.setText("Training: Complete")
            self.training_status_btn.setStyleSheet(
                "padding: 2px 8px; border-radius: 8px; background: #1f4f2e; color: #d3f5dc;"
            )
        elif status == "Training failed":
            self.training_status_btn.setText("Training: Failed")
            self.training_status_btn.setStyleSheet(
                "padding: 2px 8px; border-radius: 8px; background: #5a2525; color: #ffd6d6;"
            )
        elif status == "Training aborted":
            self.training_status_btn.setText("Training: Aborted")
            self.training_status_btn.setStyleSheet(
                "padding: 2px 8px; border-radius: 8px; background: #5a4a21; color: #ffe9b6;"
            )
        else:
            self.training_status_btn.setText("Training: Idle")
            self.training_status_btn.setStyleSheet(
                "padding: 2px 8px; border-radius: 8px; background: #2d3a47; color: #b9c4d0;"
            )

    def resolve_drive(self):
        drive = getattr(self.parent_window, "drive", None)
        if drive:
            return drive

        line_edit = getattr(self.parent_window, "dir_name_edit", None)
        if line_edit is not None:
            try:
                text = line_edit.text().strip()
                if text:
                    return text
            except Exception:
                pass

        return None

    # if the user clicks on the training status button in nav bar we want to direct them to that window
    # this isn't required, just a nice to have so its quicker to get to the training window
    def open_training_window(self):
        drive = self.resolve_drive()
        if not drive:
            return

        if self.parent_window.__class__.__name__ == "TrainModel":
            return

        from train_model import TrainModel

        self.parent_window.trainWindow = TrainModel(drive)
        self.parent_window.trainWindow.show()
        self.parent_window.close()
