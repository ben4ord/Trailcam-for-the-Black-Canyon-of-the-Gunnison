"""Training UI window that controls and monitors the background trainer.

This window never runs YOLO training directly. It talks to `TrainingSession`,
which launches `training_subprocess.py` and exposes a polling snapshot API.
"""

import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QGuiApplication

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QTextEdit, QMessageBox, QProgressBar, QLabel, QHBoxLayout, QComboBox
)

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QCloseEvent

from nav_bar import NavBar
import torch
import qtawesome as qta
from training_config import TrainingConfig
from training_session import get_training_session
from ui_dialogs import confirm_action


class TrainModel(QMainWindow):
    def __init__(self,drive):
        super().__init__()
        self.drive = drive
        # Shared singleton keeps run state consistent across reopened windows.
        self.session = get_training_session()
        self._abort_force_ms = 180000 # 3 minutes
        self._last_completion_counter = -1
        self._last_debug_text = ""
        self._last_log_text = ""
        self._prev_running = None

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
        self.debug_label.setWordWrap(True)
        self.debug_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        layout.addWidget(self.debug_label)

        self.debug_view = QTextEdit()
        self.debug_view.setReadOnly(True)
        self.debug_view.setMaximumHeight(120)
        layout.addWidget(self.debug_view)

        self.copy_debug_btn = QPushButton("Copy Debug Logs")
        self.copy_debug_btn.clicked.connect(self.copy_debug_logs)
        layout.addWidget(self.copy_debug_btn)

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
        self.model_combo.currentIndexChanged.connect(self._on_model_selected)
        model_row.addWidget(self.model_combo)

        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(qta.icon("fa5s.sync-alt"))
        self.refresh_btn.setFixedSize(30, 30)
        self.refresh_btn.setToolTip("Refresh model list")
        self.refresh_btn.clicked.connect(self._populate_model_dropdown)
        model_row.addWidget(self.refresh_btn)

        layout.addLayout(model_row)

        self._populate_model_dropdown()

        # Stop Button
        self.stop_btn = QPushButton("Abort Training")
        self.stop_btn.clicked.connect(self.abort_training)
        self.stop_btn.setEnabled(False)

        layout.addWidget(self.train_btn)
        layout.addWidget(self.stop_btn)

        self.refresh_timer = QTimer(self)
        # UI polls snapshot every 500 ms to mirror subprocess state in near real time.
        self.refresh_timer.setInterval(500)
        self.refresh_timer.timeout.connect(self.refresh_session_ui)
        self.refresh_timer.start()
        self.refresh_session_ui()

    def _set_busy_progress(self):
        """Switch to indeterminate mode for setup/teardown stages."""
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("Working...")

    def _set_determinate_progress(self):
        """Restore normal fixed-range mode for percent-based progress."""
        if self.progress_bar.minimum() == 0 and self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 10000)

    def _populate_model_dropdown(self):
        """Populate available checkpoint files from local `Models/` folder."""
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItem("Train from scratch", userData=None)

        models_dir = os.path.join(os.path.dirname(__file__), "Models")
        print(f"Looking for models in: {models_dir}")
        print(f"Directory exists: {os.path.isdir(models_dir)}")
        if os.path.isdir(models_dir):
            print(f"Contents: {os.listdir(models_dir)}")
            for f in sorted(os.listdir(models_dir)):
                if f.endswith(".pt"):
                    print(f"Found model file: {f}")
                    print(f"Models dir path: {models_dir}")
                    full_path = os.path.join(models_dir, f)
                    # Keep file name in userData; training config resolves path later.
                    self.model_combo.addItem(f, userData=f) #replace user data with full path if needed

        self.model_combo.blockSignals(False)
        self._on_model_selected(self.model_combo.currentIndex())

    def _on_model_selected(self, index):
        """Update primary action text to reflect selected base model."""
        selected_txt = self.model_combo.currentText()
        print(f"Selected model: {self.model_combo.currentData()}")
        
        if index == 0:
            self.train_btn.setText("Train New Model")
        else:
            self.train_btn.setText(f"Train Using '{selected_txt}'")

    def _get_device(self):
        """Legacy helper kept for reference if manual device controls are re-added."""
        if torch.cuda.is_available():
            return "0"          # Windows/Linux with NVIDIA GPU
        elif torch.backends.mps.is_available():
            return "mps"        # Apple Silicon Mac
        else:
            return "cpu"        # Fallback

    def train_new_model(self):
        """Confirm and launch a new training run via TrainingSession."""
        if not confirm_action(
            self,
            "Start Training",
            "Are you sure you want to start training a new model?",
        ):
            return

        ok, message = self.session.start(self.drive, TrainingConfig())
        if not ok:
            QMessageBox.information(self, "Training Busy", message)
            return

        self._set_busy_progress()
        self.progress_label.setText("Launching training...")
        self.debug_label.setText("Debug: waiting for first completed epoch...")
        self.refresh_session_ui()

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
        QTimer.singleShot(self._abort_force_ms, self._force_kill_if_still_running)

    def _force_kill_if_still_running(self):
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

    def refresh_session_ui(self):
        """Pull latest session snapshot and refresh progress/log controls."""
        snapshot = self.session.snapshot()
        was_running = self._prev_running
        self._prev_running = snapshot["running"]

        debug_text = "\n".join(snapshot["debug_lines"])
        if debug_text != self._last_debug_text:
            self.debug_view.setPlainText(debug_text)
            self._last_debug_text = debug_text

        self._last_log_text = "\n".join(snapshot["log_lines"])

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
            self._set_busy_progress()
        else:
            self._set_determinate_progress()
            self.progress_bar.setValue(max(0, min(10000, progress)))
            self.progress_bar.setFormat(f"{progress / 100:.1f}%")

        self.progress_label.setText(status)
        self.debug_label.setText(
            snapshot["debug_lines"][-1] if snapshot["debug_lines"] else "Debug: idle"
        )

        self.train_btn.setEnabled(not snapshot["running"])
        self.stop_btn.setEnabled(snapshot["running"])

        current_counter = int(snapshot["completion_counter"])
        if current_counter != self._last_completion_counter:
            # Counter increments once at each terminal state transition.
            self._last_completion_counter = current_counter
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
                self._set_determinate_progress()
                self.progress_bar.setValue(10000)
                self.progress_bar.setFormat("100.0%")
                QMessageBox.information(
                    self,
                    "Training Complete",
                    "Model training finished.",
                )

    def copy_debug_logs(self):
        """Copy debug log view to clipboard for quick sharing."""
        QGuiApplication.clipboard().setText(self.debug_view.toPlainText())
        self.debug_label.setText("Debug: logs copied to clipboard.")

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
