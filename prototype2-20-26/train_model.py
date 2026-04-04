"""Training UI window that controls and monitors the background trainer.

This window never runs YOLO training directly. It talks to `TrainingSession`,
which launches `training_subprocess.py` and exposes a polling snapshot API.
"""

import os
import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QGuiApplication

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QTextEdit, QMessageBox, QProgressBar, QLabel, QHBoxLayout, QComboBox
)

from nav_bar import NavBar
import torch
import qtawesome as qta
from training_config import TrainingConfig
from training_session import get_training_session
from ui_dialogs import confirm_action
import datetime


class TrainModel(QMainWindow):
    def __init__(self,drive):
        super().__init__()
        self.drive = drive
        # Shared variable keeps run state consistent across reopened windows.
        self.session = get_training_session()
        self.abort_force_ms = 180000 # 3 minutes
        self.last_completion_counter = -1
        self.last_debug_text = ""
        self.last_log_text = ""
        self.prev_running = None

        self.resize(800, 500)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setContentsMargins(0, 0, 0, 0)

        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central)

        self.nav_bar = NavBar(self)
        self.nav_bar.set_button_visibility(
            home=True,
            update_labels=False,
            new_folder=False,
        )
        self.nav_bar.homeClicked.connect(self.menu_window)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.nav_bar)

        self.progress_label = QLabel("Ready to train")
        layout.addWidget(self.progress_label)

        self.debug_label = QLabel("Debug: idle")
        self.debug_label.setWordWrap(True) # Makes sure the debug text wraps to the next line
        self.debug_label.setTextInteractionFlags( # Set flags so users can select and copy text within the debug label
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        layout.addWidget(self.debug_label)

        # Debug view (that box where the debug prints go)
        self.debug_view = QTextEdit()
        self.debug_view.setReadOnly(True)
        self.debug_view.setMaximumHeight(120)
        layout.addWidget(self.debug_view)

        # Copy debug logs button (easy of use)
        self.copy_debug_btn = QPushButton("Copy Debug Logs")
        self.copy_debug_btn.clicked.connect(self.copy_debug_logs)
        layout.addWidget(self.copy_debug_btn)

        # Progress bar for epoch tracking
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 10000)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0.0%")
        layout.addWidget(self.progress_bar)

        # Keep a compact log box for failures only.
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        self.log_view.hide()
        layout.addWidget(self.log_view)

        # Train Button
        self.train_btn = QPushButton("Train New Model")
        self.train_btn.clicked.connect(self.train_new_model)

        # Model Selector
        model_row = QHBoxLayout()

        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(self.on_model_selected)
        model_row.addWidget(self.model_combo)

        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(qta.icon("fa5s.sync-alt"))
        self.refresh_btn.setFixedSize(30, 30)
        self.refresh_btn.setToolTip("Refresh model list")
        self.refresh_btn.clicked.connect(self.populate_model_dropdown)
        model_row.addWidget(self.refresh_btn)

        layout.addLayout(model_row)

        self.populate_model_dropdown()

        # Resume Button
        self.resume_btn = QPushButton("Resume Last Training")
        self.resume_btn.clicked.connect(self.resume_training)

        # Stop Button
        self.stop_btn = QPushButton("Abort Training")
        self.stop_btn.clicked.connect(self.abort_training)
        self.stop_btn.setEnabled(False)

        layout.addWidget(self.train_btn)
        layout.addWidget(self.resume_btn)
        layout.addWidget(self.stop_btn)

        self.refresh_timer = QTimer(self)
        # UI polls snapshot every 500 ms to mirror subprocess state in near real time.
        self.refresh_timer.setInterval(500)
        self.refresh_timer.timeout.connect(self.refresh_session_ui)
        self.refresh_timer.start()
        self.refresh_session_ui()

    # Sets text in view when background processes are working
    def set_busy_progress(self):
        """Switch to indeterminate mode for setup/teardown stages."""
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("Working...")

    # Sets the range for the progress bar display
    def set_determinate_progress(self):
        """Restore normal fixed-range mode for percent-based progress."""
        if self.progress_bar.minimum() == 0 and self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 10000)

    # Grab the model names from the Models folder and populate the dropdown based on it
    def populate_model_dropdown(self):
        """Populate available checkpoint files from local `Models/` folder."""
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItem("Train from scratch", userData=None)

        models_dir = os.path.join(os.path.dirname(__file__), "Models")
        if os.path.isdir(models_dir):
            for (root, dirs, files) in os.walk(models_dir):
                for f in files:
                    if f.endswith(".pt"):
                        full_path = os.path.join(root,f)
                        relative_path = os.path.relpath(full_path, start=models_dir)
                        if f != "last.pt": #ignore last.pt file
                            self.model_combo.addItem(relative_path, userData=relative_path)
        self.model_combo.blockSignals(False)
        self.on_model_selected(self.model_combo.currentIndex())

    # This will allow the user to select an existing model for resuming training or starting new from a saved point
    def on_model_selected(self, index):
        """Update primary action text to reflect selected base model."""
        selected_txt = self.model_combo.currentText()

        selected_model = self.model_combo.currentData() if self.model_combo.currentData() else "yolov8s.pt"
        last_model = self.get_corresponding_last_pt(selected_model)
        
        if index == 0:
            self.train_btn.setText("Train New Model")
        else:
            self.train_btn.setText(f"Train Using '{selected_txt}'")
            self.resume_btn.setText(f"Resume Using '{last_model}'")

    # Get the user device (this is for GPU usage when training, should work on Mac as well)
    def get_device(self):
        """Device control"""
        if torch.cuda.is_available():
            return "0"          # Windows/Linux with NVIDIA GPU
        elif torch.backends.mps.is_available():
            return "mps"        # Apple Silicon Mac
        else:
            return "cpu"        # Fallback

    def get_corresponding_last_pt(self, model_path: str) -> str:
        """Get the corresponding last.pt from the same directory as the selected model."""
        if not model_path:
            return "yolov8s.pt"
        
        # Get the directory containing the model
        model_dir = os.path.dirname(model_path)
        
        # Construct path to last.pt in the same directory
        last_pt_path = os.path.join(model_dir, "last.pt")
        
        # Verify it exists relative to Models folder
        models_dir = os.path.join(os.path.dirname(__file__), "Models")
        full_last_pt_path = os.path.join(models_dir, last_pt_path)
        
        if os.path.isfile(full_last_pt_path):
            return last_pt_path
        
        # If last.pt doesn't exist, return the original model path
        return model_path
    
    def resume_training(self):
        """Resume the last training run based on selection"""
        selected_model = self.model_combo.currentData() if self.model_combo.currentData() else "yolov8s.pt"
        last_model = self.get_corresponding_last_pt(selected_model)

        
        if not confirm_action(
            self,
            "Resume Training",
            f"Are you sure you want to resume training {last_model}?",
        ):
            return
        
        config = TrainingConfig(model=last_model, device=self.get_device())
        config.resume = True
        run_name = os.path.dirname(os.path.dirname(last_model)) or datetime.datetime.now().strftime('%m-%d-%Y_%H:%M:%S')
        config.name = os.path.basename(run_name)
        ok, message = self.session.start(self.drive, config)
        if not ok:
            QMessageBox.information(self, "Training Busy", message)
            return

        self.set_busy_progress()
        self.progress_label.setText("Launching training...")
        self.debug_label.setText("Debug: waiting for first completed epoch...")
        self.refresh_session_ui()


    # This is to start training on a completely new model (no previous weights)
    # This calls the session.start which launches a function in traning_session.py
    def train_new_model(self):
        """Confirm and launch a new training run via TrainingSession."""
        if not confirm_action(
            self,
            "Start Training",
            "Are you sure you want to start training a new model?",
        ):
            return

        config = TrainingConfig(model=self.model_combo.currentData() if self.model_combo.currentData() else "yolov8s.pt", device=self.get_device())
        config.name= datetime.datetime.now().strftime('%m-%d-%Y_%H:%M:%S')
        ok, message = self.session.start(self.drive, config)
        if not ok:
            QMessageBox.information(self, "Training Busy", message)
            return

        self.set_busy_progress()
        self.progress_label.setText("Launching training...")
        self.debug_label.setText("Debug: waiting for first completed epoch...")
        self.refresh_session_ui()

    # Abort the training if requested by the user
    # This calls the session.request_stop() function which tries to stop the training session
    # using a function in training_session.py
    def abort_training(self):
        """Request graceful stop and schedule hard-stop timeout fallback."""
        snapshot = self.session.snapshot()
        if not snapshot["running"]:
            return

        if not confirm_action(
            self,
            "Abort Training",
            "Are you sure you want to abort the current training run?\n"
            "A graceful stop is attempted first to preserve best weights.",
        ):
            return

        self.session.request_stop()
        self.stop_btn.setEnabled(False)
        self.progress_label.setText("Stopping training (this may take a while)...")
        self.debug_label.setText("Debug: stop requested from UI.")
        QTimer.singleShot(self.abort_force_ms, self.force_kill_if_still_running)

    # This function is to force kill the process after a certain amount of time
    # Sometimes the process will not terminate gracefully and we need to be able to force quit training
    # This calls the session.force_kill() to request a force quit
    def force_kill_if_still_running(self):
        """Force kill training process if it ignores graceful stop request."""
        snapshot = self.session.snapshot()
        if not snapshot["running"]:
            return

        killed = self.session.force_kill()
        if killed:
            QMessageBox.warning(
                self,
                "Training Force-Stopped",
                "Graceful stop timed out. The training subprocess was terminated.\n"
                "Best weights were recovered if available.",
            )

    # This function is designed for loading the current logs and progress information for training
    # It is designed so the user can completely close the GUI and continue training in the background
    # Thus, if they re-open the GUI we need to reload the training page with the up-to-date information from training
    def refresh_session_ui(self):
        """Pull latest session snapshot and refresh progress/log controls."""
        # This snapshot is used a lot and contains all of the training sessions information
        snapshot = self.session.snapshot()
        was_running = self.prev_running
        self.prev_running = snapshot["running"]

        # Grab the debug text from the training snapshot
        debug_text = "\n".join(snapshot["debug_lines"])
        if debug_text != self.last_debug_text:
            self.debug_view.setPlainText(debug_text)
            self.last_debug_text = debug_text

        self.last_log_text = "\n".join(snapshot["log_lines"])

        status = snapshot["status"]
        progress = int(snapshot["progress"])
        # Status prefixes that indicate non-determinate phases.
        is_setup_status = (
            status.startswith("Preparing")
            or status.startswith("Starting epoch")
            or status.startswith("Stopping")
            or status.startswith("Checking")
            or status.startswith("Loading")
            or status.startswith("Building")
            or status.startswith("Validating")
            or status.startswith("Training loop started")
            or status.startswith("Releasing")
            or status.startswith("Launching")
        )

        # Show spinner while worker is active but no meaningful percent exists yet.
        if snapshot["running"] and progress <= 0 and is_setup_status:
            self.set_busy_progress()
        else:
            self.set_determinate_progress()
            self.progress_bar.setValue(max(0, min(10000, progress)))
            self.progress_bar.setFormat(f"{progress / 100:.1f}%")

        self.progress_label.setText(status)
        self.debug_label.setText(
            snapshot["debug_lines"][-1] if snapshot["debug_lines"] else "Debug: idle"
        )

        self.train_btn.setEnabled(not snapshot["running"])
        self.stop_btn.setEnabled(snapshot["running"])

        current_counter = int(snapshot["completion_counter"])
        if current_counter != self.last_completion_counter:
            # Counter increments once at each terminal state transition.
            self.last_completion_counter = current_counter
            if current_counter <= 0:
                return
            if was_running is not True:
                return

            if snapshot["had_error"]:
                QMessageBox.warning(
                    self,
                    "Training Failed",
                    "Training failed. Check the log panel for details.",
                )
            elif snapshot["was_aborted"]:
                QMessageBox.information(
                    self,
                    "Training Aborted",
                    "Training was stopped.",
                )
            else:
                self.set_determinate_progress()
                self.progress_bar.setValue(10000)
                self.progress_bar.setFormat("100.0%")
                QMessageBox.information(
                    self,
                    "Training Complete",
                    "Model training finished.",
                )

    # Copies debug logs to the clipboard (ease of use)
    def copy_debug_logs(self):
        """Copy debug log view to clipboard for quick sharing."""
        QGuiApplication.clipboard().setText(self.debug_view.toPlainText())
        self.debug_label.setText("Debug: logs copied to clipboard.")

    # Menu window from the nav_bar
    def menu_window(self):
        """Navigate back to home menu."""
        from home_menu import MenuWindow

        self.menuWindow = MenuWindow(self.drive)
        self.menuWindow.show()
        self.close()

    def closeEvent(self, event: QCloseEvent):
        """Stop polling timer on window close."""
        self.refresh_timer.stop()
        event.accept()
