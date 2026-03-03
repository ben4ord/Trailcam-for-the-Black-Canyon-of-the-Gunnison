from PySide6.QtCore import QObject, Signal
from pathlib import Path
import shutil
from ultralytics import YOLO



class TrainingWorker(QObject):
    log_signal = Signal(str)
    finished = Signal()

    def __init__(self, training_cmd, drive):
        super().__init__()
        self.training_cmd = training_cmd
        self._running = True

        self.models_dir = Path("Models")
        self.models_dir.mkdir(exist_ok=True)
        self.drive = drive

    def stop(self):
        self._running = False

    def run(self):
        model = YOLO("yolov8s.pt")

        model.train(
            data=f"{self.drive}/data.yaml",
            epochs=200,
            imgsz=512,
            batch=32,
            device=0,
            patience=15,
            project="Models",
            name="experiment1"
        )

        self.finished.emit()

        source_model = Path("Models/experiment1/weights/best.pt")

        if source_model.exists():
            shutil.copy(source_model, self.models_dir / "best.pt")
            print("Model saved to Models/best.pt")

        self.finished.emit()