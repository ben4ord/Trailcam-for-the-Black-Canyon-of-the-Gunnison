import os
import sys

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QMessageBox, QProgressBar, QLabel, QComboBox
)

from PySide6.QtCore import QThread
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QCloseEvent

from training_worker import TrainingWorker
from nav_bar import NavBar
import torch
from pathlib import Path
import qtawesome as qta


class TrainModel(QMainWindow):
    def __init__(self,drive):
        super().__init__()
        self.drive = drive
        self.thread = None
        self.worker = None
        self._shutting_down = False

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

    # -----------------------------

    def _set_busy_progress(self):
        # Qt indeterminate mode (animated barber pole)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("Working...")

    def _set_determinate_progress(self):
        if self.progress_bar.minimum() == 0 and self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 10000)

    def _populate_model_dropdown(self):
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
                    self.model_combo.addItem(f, userData=f) #replace user data with full path if needed

        self.model_combo.blockSignals(False)
        self._on_model_selected(self.model_combo.currentIndex())

    def _on_model_selected(self, index):
        selected_txt = self.model_combo.currentText()
        print(f"Selected model: {self.model_combo.currentData()}")
        
        if index == 0:
            self.train_btn.setText("Train New Model")
        else:
            self.train_btn.setText(f"Train Using '{selected_txt}'")

    def _get_device(self):
        if torch.cuda.is_available():
            return "0"          # Windows/Linux with NVIDIA GPU
        elif torch.backends.mps.is_available():
            return "mps"        # Apple Silicon Mac
        else:
            return "cpu"        # Fallback

    def train_new_model(self):
        if self.thread and self.thread.isRunning():
            return

        data_path = Path.cwd() / "data.yaml"
        project_path = Path.cwd() / "Models"
        model_path = Path.cwd() / self.model_combo.currentData() if self.model_combo.currentIndex() != 0 else "yolov8s.pt" #change fallback if needed

        cmd = [
            sys.executable,
            "-m",
            "ultralytics",
            "train",
            f"model={model_path}",
            f"data={data_path}",
            "epochs=200",
            "imgsz=512",
            "batch=32",
            f"device={self._get_device()}",
            "patience=15",
            f"project={project_path}",
            "name=experiment1"
        ]

        self.thread = QThread()
        self.worker = TrainingWorker(cmd, self.drive)

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.debug_signal.connect(self.update_debug)
        self.worker.finished.connect(self.training_finished)

        self.thread.start()

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
            self.worker.stop()
            self.stop_btn.setEnabled(False)
            self.progress_label.setText("Stopping training...")
            self.debug_label.setText("Debug: stop requested from UI.")

    def _shutdown_training(self):
        if not self.thread or not self.thread.isRunning():
            return

        self._shutting_down = True
        if self.worker:
            self.worker.stop()

        self.thread.quit()
        if not self.thread.wait(5000):
            # Hard-stop as fallback on app/window close.
            self.thread.terminate()
            self.thread.wait(2000)

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
        self.train_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if self._shutting_down:
            if self.thread:
                self.thread.quit()
                self.thread.wait()
            self.worker = None
            self.thread = None
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
            self.thread.quit()
            self.thread.wait()
        self.worker = None
        self.thread = None

    def menu_window(self):
        self._shutdown_training()
        from home_menu import MenuWindow
        self.menuWindow = MenuWindow(self.drive)
        self.menuWindow.show()
        self.close()

    def closeEvent(self, event: QCloseEvent):
        self._shutdown_training()
        event.accept()
