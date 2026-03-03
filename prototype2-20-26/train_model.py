import sys

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QTextEdit, QMessageBox
)

from PySide6.QtCore import QThread
from PySide6.QtCore import Qt

from training_worker import TrainingWorker
from nav_bar import NavBar


class TrainModel(QMainWindow):
    def __init__(self, drive):
        super().__init__()

        self.drive = drive
        self.thread = None
        self.worker = None

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

        # Log console
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        # Buttons
        self.train_btn = QPushButton("Train New Model")
        self.train_btn.clicked.connect(self.train_new_model)

        self.stop_btn = QPushButton("Abort Training")
        self.stop_btn.clicked.connect(self.abort_training)

        layout.addWidget(self.train_btn)
        layout.addWidget(self.stop_btn)

    # -----------------------------

    def train_new_model(self):

        cmd = [
            sys.executable,
            "-m",
            "ultralytics",
            "train",
            "model=yolov8s.pt",
            f"data={self.drive}/data.yaml",
            "epochs=200",
            "imgsz=512",
            "batch=32",
            "device=0",
            "patience=15",
            "project=Models",
            "name=experiment1"
        ]

        self.thread = QThread()
        self.worker = TrainingWorker(cmd)

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.log_signal.connect(self.append_log)
        self.worker.finished.connect(self.training_finished)

        self.thread.start()

        self.train_btn.setEnabled(False)

    # -----------------------------

    def abort_training(self):
        if self.worker:
            self.worker.stop()

    # -----------------------------

    def append_log(self, text):
        self.log_view.append(text)

    # -----------------------------

    def training_finished(self):
        self.train_btn.setEnabled(True)

        QMessageBox.information(
            self,
            "Training Complete",
            "Model training finished."
        )

        if self.thread:
            self.thread.quit()
            self.thread.wait()

    def menu_window(self):
        from menu import MenuWindow
        self.menuWindow = MenuWindow(self.drive)
        self.menuWindow.show()
        self.close()