from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from nav_bar import NavBar
from training_config import TrainingConfig
from training_session import get_training_session
from ui_dialogs import confirm_action


class TrainModel(QMainWindow):
    def __init__(self, drive):
        super().__init__()

        self.drive = drive
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

        self.train_btn = QPushButton("Train New Model")
        self.train_btn.clicked.connect(self.train_new_model)

        self.stop_btn = QPushButton("Abort Training")
        self.stop_btn.clicked.connect(self.abort_training)
        self.stop_btn.setEnabled(False)

        layout.addWidget(self.train_btn)
        layout.addWidget(self.stop_btn)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(500)
        self.refresh_timer.timeout.connect(self.refresh_session_ui)
        self.refresh_timer.start()
        self.refresh_session_ui()

    def _set_busy_progress(self):
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("Working...")

    def _set_determinate_progress(self):
        if self.progress_bar.minimum() == 0 and self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 10000)

    def train_new_model(self):
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
        QGuiApplication.clipboard().setText(self.debug_view.toPlainText())
        self.debug_label.setText("Debug: logs copied to clipboard.")

    def menu_window(self):
        from home_menu import MenuWindow

        self.menuWindow = MenuWindow(self.drive)
        self.menuWindow.show()
        self.close()

    def closeEvent(self, event: QCloseEvent):
        self.refresh_timer.stop()
        event.accept()
