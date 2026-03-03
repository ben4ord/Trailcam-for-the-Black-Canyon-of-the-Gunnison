from ultralytics import YOLO
import os
import sys
import numpy as np


class ImageLabeler:
    def __init__(self):
        # Detect if running inside PyInstaller bundle
        def resource_path(relative_path: str):
            if hasattr(sys, "_MEIPASS"):
                return os.path.join(sys._MEIPASS, relative_path) #type: ignore
            return os.path.join(os.path.abspath("."), relative_path)

        # Resolve full model path
        full_model_path = resource_path("Models/best.pt")
        self.model = YOLO(full_model_path)

    def predict(self, image_path: str):
        results = self.model(image_path, verbose=False)
        return results[0]

    def label_image(self, image_path: str) -> np.ndarray:
        return self.predict(image_path).plot()

    @staticmethod
    def to_yolo_label_lines(result) -> list[str]:
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []

        classes = boxes.cls.tolist()
        normalized_xywh = boxes.xywhn.tolist()

        lines = []
        for class_id, (x_center, y_center, width, height) in zip(classes, normalized_xywh):
            lines.append(
                f"{int(class_id)} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
            )

        return lines
