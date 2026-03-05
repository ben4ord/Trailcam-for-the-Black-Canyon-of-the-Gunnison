from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QTextEdit, QMessageBox, QProgressBar, QLabel
)

from PySide6.QtCore import QThread, QTimer
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QCloseEvent

from training_worker import TrainingWorker
from training_config import TrainingConfig
from nav_bar import NavBar
from ui_dialogs import confirm_action


class TrainModel(QMainWindow):
    def __init__(self, drive):
        super().__init__()

        self.drive = drive
        self.thread = None #type: ignore
        self.worker = None
        self._shutting_down = False
        self._abort_force_ms = 30000
        self._forced_abort = False
        self._current_run_dir = None

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
            new_folder=False
        )
        self.nav_bar.homeClicked.connect(self.menu_window)

        # Layout
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.nav_bar)

        # Training progress (non-technical display)
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

        # Buttons
        self.train_btn = QPushButton("Train New Model")
        self.train_btn.clicked.connect(self.train_new_model)

        self.stop_btn = QPushButton("Abort Training")
        self.stop_btn.clicked.connect(self.abort_training)
        self.stop_btn.setEnabled(False)

        layout.addWidget(self.train_btn)
        layout.addWidget(self.stop_btn)

    # -----------------------------

    def _set_busy_progress(self):
        # Qt indeterminate mode (animated barber pole)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("Working...")

    def _set_determinate_progress(self):
        if self.progress_bar.minimum() == 0 and self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 10000)

    def train_new_model(self):
        if self.thread and self.thread.isRunning(): #type: ignore
            return

        if not confirm_action(
            self,
            "Start Training",
            "Are you sure you want to start training a new model?",
        ):
            return

        config = TrainingConfig()

        self.thread = QThread() #type: ignore
        self.worker = TrainingWorker(config, self.drive)

        self.worker.moveToThread(self.thread) #type: ignore

        self.thread.started.connect(self.worker.run) #type: ignore

        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.debug_signal.connect(self.update_debug)
        self.worker.run_dir_signal.connect(self._on_run_dir)
        self.worker.finished.connect(self.training_finished)

        self.thread.start() #type: ignore

        self._set_busy_progress()
        self.progress_label.setText("Launching training...")
        self.debug_label.setText("Debug: waiting for first completed epoch...")
        self.debug_view.clear()
        self.log_view.clear()
        self.log_view.hide()
        self.append_log(f"Launching training from folder: {self.drive}")
        self.train_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    # -----------------------------

    def abort_training(self):
        if self.worker:
            if not confirm_action(
                self,
                "Abort Training",
                "Are you sure you want to abort the current training run?\nThis may take a while...",
            ):
                return
            self.worker.stop()
            self.stop_btn.setEnabled(False)
            self.progress_label.setText("Stopping training (this may take a while)...")
            self.debug_label.setText("Debug: stop requested from UI.")
            QTimer.singleShot(self._abort_force_ms, self._force_stop_if_still_running)

    def _on_run_dir(self, run_dir: str):
        self._current_run_dir = Path(run_dir)

    def _copy_partial_best_if_available(self) -> bool:
        if self._current_run_dir is None:
            return False
        try:
            source_model = self._current_run_dir / "weights" / "best.pt"
            if not source_model.exists():
                return False
            destination = Path(__file__).resolve().parent / "Models" / "best.pt"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source_model.read_bytes())
            return True
        except Exception:
            return False

    def _force_stop_if_still_running(self):
        if not self.thread or not self.thread.isRunning(): #type: ignore
            return

        self._forced_abort = True
        copied = self._copy_partial_best_if_available()
        if copied:
            self.append_log("Recovered latest best.pt before force-stop.")
        else:
            self.append_log("Force-stop: no best.pt was available to recover yet.")

        injected = False
        if self.worker:
            injected = self.worker.request_keyboard_interrupt()
        if injected:
            self.debug_label.setText("Debug: timeout reached; sent KeyboardInterrupt to training thread.")
            self.thread.wait(10000) #type: ignore
            if not self.thread.isRunning(): #type: ignore
                self.training_finished()
                return

        self.debug_label.setText(
            "Debug: training did not stop after timeout. Unsafe thread termination is disabled."
        )
        self.append_log(
            "Stop timeout reached. Training did not stop yet; continuing to wait for graceful shutdown."
        )
        self.log_view.show()
        self.stop_btn.setEnabled(True)
        QMessageBox.warning(
            self,
            "Stop Delayed",
            "Training is still shutting down. To avoid crashing the app, forced thread termination is disabled.\n\n"
            "You can wait a bit longer and press Abort again."
        )

    def _shutdown_training(self):
        if not self.thread or not self.thread.isRunning(): #type: ignore
            return

        self._shutting_down = True
        if self.worker:
            self.worker.stop()

        self.thread.quit()                                             #type: ignore
        if not self.thread.wait(5000): #type: ignore
            # Hard-stop as fallback on app/window close.
            self.thread.terminate()                                    #type: ignore
            self.thread.wait(2000)                                     #type: ignore

    # -----------------------------

    def append_log(self, text):
        self.log_view.append(text)
        if self.worker and self.worker.had_error:
            self.log_view.show()

    def update_progress(self, progress, status):
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
        )

        if progress <= 0 and is_setup_status:
            self._set_busy_progress()
            self.progress_label.setText(status)
            return

        self._set_determinate_progress()
        self.progress_bar.setValue(progress)
        self.progress_bar.setFormat(f"{progress / 100:.1f}%")
        self.progress_label.setText(status)

    def update_debug(self, text):
        self.debug_label.setText(text)
        self.debug_view.append(text)

    def copy_debug_logs(self):
        QGuiApplication.clipboard().setText(self.debug_view.toPlainText())
        self.debug_label.setText("Debug: logs copied to clipboard.")

    # -----------------------------

    def training_finished(self):
        if self.thread and self.thread.isRunning(): #type: ignore
            return

        self.train_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if self._shutting_down:
            if self.thread:
                self.thread.quit()                          #type: ignore
                self.thread.wait()                          #type: ignore
            self.worker = None
            self.thread = None                              #type: ignore
            return

        if self.worker and self.worker.had_error:
            self._set_determinate_progress()
            self.log_view.show()
            QMessageBox.warning(
                self,
                "Training Failed",
                "Training failed. Check the log panel for details."
            )
        elif self.worker and self.worker.was_aborted:
            self._set_determinate_progress()
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("0.0%")
            self.progress_label.setText("Training aborted")
            if self._forced_abort:
                QMessageBox.warning(
                    self,
                    "Training Force-Stopped",
                    "Training did not stop gracefully in time and was force-stopped. Best weights were recovered if available."
                )
            else:
                QMessageBox.information(
                    self,
                    "Training Aborted",
                    "Training was stopped."
                )
        else:
            self._set_determinate_progress()
            self.progress_bar.setValue(10000)
            self.progress_bar.setFormat("100.0%")
            self.progress_label.setText("Training complete")
            QMessageBox.information(
                self,
                "Training Complete",
                "Model training finished."
            )

        if self.thread:
            self.thread.quit()                                 #type: ignore
            self.thread.wait()                                 #type: ignore
        self.worker = None
        self.thread = None                                     #type: ignore
        self._current_run_dir = None
        self._forced_abort = False

    def menu_window(self):
        self._shutdown_training()
        from home_menu import MenuWindow
        self.menuWindow = MenuWindow(self.drive)
        self.menuWindow.show()
        self.close()

    def closeEvent(self, event: QCloseEvent):
        self._shutdown_training()
        event.accept()
