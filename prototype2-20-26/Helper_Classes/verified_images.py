import pandas as pd
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel, QProgressBar
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QObject,Signal
import sys 

class ImageCounterWorker(QObject):
    progress = Signal(int)
    finished = Signal(int, str)
    error = Signal(str)

    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path

    def run(self):
        try:
            root_dir = self.base_path / "verified_images"

            if not root_dir.exists():
                self.error.emit("Verified images folder not found.")
                return

            images_list = []
            valid_ext = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
            count = 0

            for path in root_dir.rglob("*"):
                if path.suffix.lower() in valid_ext:
                    images_list.append({"image_path": str(path)})
                    count += 1

                    if count % 100 == 0:
                        self.progress.emit(count)

            if count == 0:
                self.error.emit("No images found.")
                return

            csv_path = self.base_path / "test.csv"
            pd.DataFrame(images_list).to_csv(csv_path, index=False)

            self.finished.emit(count, str(csv_path))

        except Exception as e:
            self.error.emit(str(e))

class CountingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Updating Verified Images")
        self.setModal(True)

        layout = QVBoxLayout(self)

        self.label = QLabel("Counting images...")
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)

        self.resize(400, 120)

    def update_count(self, count):
        self.label.setText(f"Images found so far: {count}")