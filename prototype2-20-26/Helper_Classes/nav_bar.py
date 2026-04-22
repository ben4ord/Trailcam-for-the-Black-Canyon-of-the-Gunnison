from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QComboBox
from PySide6.QtCore import Qt, QEvent, QPoint, Signal, QTimer
import qtawesome as qta
import os
import sys
from pathlib import Path
# Determine base directory (.exe dist)
if getattr(sys, "frozen", False):
    base_path = Path(sys.executable).parent
else:
    base_path = Path(__file__).resolve().parent

MODELS_DIR = base_path / "Models"

def icon(name: str):
    """Return a qtawesome icon forced to white regardless of system theme."""
    return qta.icon(name, color='white')  # type: ignore[call-arg]
from Training_Classes.training_session import get_training_session
from Helper_Classes.model_selection_state import get_model_selection_state


class NavBar(QWidget):
    homeClicked = Signal()
    updateLabelsClicked = Signal()
    newFolderClicked = Signal()
    newBatchClicked = Signal()
    infoClicked = Signal()
    modelSelected = Signal(str)  # emits full path to the selected .pt file

    def __init__(self, parent_window):
        super().__init__()

        self.parent_window = parent_window
        self.training_session = get_training_session()
        self._model_state = get_model_selection_state()
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
        self.home_btn.setIcon(icon('fa6s.house'))
        self.home_btn.setToolTip("Home")
        self.home_btn.clicked.connect(self.homeClicked.emit)

        # Update labels button
        self.update_labels_btn = QPushButton()
        self.update_labels_btn.setIcon(icon('fa6s.file-pen'))
        self.update_labels_btn.setToolTip("Update Class Labels")
        self.update_labels_btn.clicked.connect(self.updateLabelsClicked.emit)

        # Select new folder button
        self.new_folder_btn = QPushButton()
        self.new_folder_btn.setIcon(icon('fa6s.folder'))
        self.new_folder_btn.setToolTip("Select New Directory")
        self.new_folder_btn.clicked.connect(self.newFolderClicked.emit)
        
        # Do new batch prediction 
        self.new_batch_btn = QPushButton()
        self.new_batch_btn.setIcon(icon('fa6s.object-group'))
        self.new_batch_btn.setToolTip("New Batch Prediction")
        self.new_batch_btn.clicked.connect(self.newBatchClicked.emit)

        # Info button 
        self.info_btn = QPushButton()
        self.info_btn.setIcon(icon('fa6s.circle-question'))
        self.info_btn.setToolTip("Help")
        self.info_btn.clicked.connect(self.infoClicked.emit)

        # Training status button
        self.training_status_btn = QPushButton("Training: Idle")
        self.training_status_btn.setToolTip("Current model training status. Click to open training window.")
        self.training_status_btn.clicked.connect(self.open_training_window)
        self.training_status_btn.setStyleSheet(
            "padding: 2px 8px; border-radius: 8px; background: #2d3a47; color: #b9c4d0;"
        )

        # Model Selection dropdown + refresh button
        self.model_selection_box = QComboBox()
        self.model_selection_box.setToolTip("Select prediction model")
        self.model_selection_box.currentIndexChanged.connect(self.on_model_selected)

        self.model_refresh_btn = QPushButton()
        self.model_refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="white"))
        self.model_refresh_btn.setFixedSize(26, 26)
        self.model_refresh_btn.setToolTip("Refresh model list")
        self.model_refresh_btn.clicked.connect(self.populate_model_dropdown)

        layout.addWidget(self.home_btn)
        layout.addWidget(self.update_labels_btn)
        layout.addWidget(self.new_folder_btn)
        layout.addWidget(self.new_batch_btn)
        layout.addWidget(self.info_btn)
        layout.addWidget(self.training_status_btn)
        layout.addWidget(self.model_selection_box)
        layout.addWidget(self.model_refresh_btn)

        layout.addStretch()

        # Window controls (Top right)
        self.min_btn = QPushButton()
        self.min_btn.setIcon(icon('fa6s.minus'))
        self.min_btn.setToolTip("Minimize")
        self.min_btn.clicked.connect(self.parent_window.showMinimized)

        self.max_btn = QPushButton()
        self.max_btn.setIcon(icon('fa6s.window-maximize'))
        self.max_btn.clicked.connect(self.toggle_max_restore)

        self.close_btn = QPushButton()
        self.close_btn.setIcon(icon('fa6s.xmark'))
        self.close_btn.setToolTip("Close")
        self.close_btn.clicked.connect(self.parent_window.close)

        for btn in (self.min_btn, self.max_btn, self.close_btn):
            btn.setFixedWidth(36)
            layout.addWidget(btn)

        self.installEventFilter(self)

        self.training_status_timer = QTimer(self)
        # Poll less frequently to avoid UI stutter on slower disks.
        self.training_status_timer.setInterval(10000)
        self.training_status_timer.timeout.connect(self.refresh_training_status)
        self.training_status_timer.start()
        self.refresh_training_status()

        self.populate_model_dropdown()

        self.update()


    # function to modify the size of the screen based on previous state
    # if window already max, then it shrinks. If window is shrunk then it maximizes it
    def toggle_max_restore(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.max_btn.setIcon(icon('fa6s.window-maximize'))
            self.max_btn.setToolTip("Restore")
        else:
            self.parent_window.showMaximized()
            self.max_btn.setIcon(icon('fa6s.window-restore'))
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

                    self.max_btn.setIcon(icon('fa6s.window-maximize'))
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
    def set_button_visibility(self, home=True, update_labels=True, new_folder=True, info_btn=True ,training_status=True, batch_status=False, model_selector=True):
        self.home_btn.setVisible(home)
        self.update_labels_btn.setVisible(update_labels)
        self.new_folder_btn.setVisible(new_folder)
        self.info_btn.setVisible(info_btn)
        self.training_status_btn.setVisible(training_status)
        self.new_batch_btn.setVisible(batch_status)
        self.model_selection_box.setVisible(model_selector)
        self.model_refresh_btn.setVisible(model_selector)

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

        from Training_Classes.train_model import TrainModel

        self.parent_window.trainWindow = TrainModel(drive)
        self.parent_window.trainWindow.show()
        self.parent_window.close()

    # Grab the model names from the Models folder and populate the dropdown based on it
    def populate_model_dropdown(self):
        """Populate available checkpoint files from the project-level `Models/` folder."""
        self.model_selection_box.blockSignals(True)
        self.model_selection_box.clear()

        if os.path.isdir(MODELS_DIR):
            for root, _dirs, files in os.walk(MODELS_DIR):
                for f in sorted(files):
                    if f.endswith(".pt") and f != "last.pt":
                        full_path = os.path.normpath(os.path.join(root, f))
                        display = os.path.relpath(full_path, start=MODELS_DIR)
                        self.model_selection_box.addItem(display, userData=full_path)

        self.model_selection_box.blockSignals(False)

        # Restore the last selection from the process-wide singleton
        saved_path = self._model_state.get()
        if saved_path:
            idx = self.model_selection_box.findData(saved_path)
            if idx >= 0:
                self.model_selection_box.setCurrentIndex(idx)
                return

        # Nothing saved yet — emit so consumers pick up the default
        if self.model_selection_box.count() > 0:
            self.on_model_selected(0)

    def on_model_selected(self, index):
        """Persist the selection and emit so consumers can reload their labeler."""
        full_path = self.model_selection_box.currentData()
        if full_path:
            self._model_state.set(full_path)
            self.modelSelected.emit(full_path)

    def selected_model_path(self) -> str:
        """Return the full path of the currently selected model, or empty string."""
        return self.model_selection_box.currentData() or ""