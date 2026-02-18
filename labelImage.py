from ultralytics import YOLO
import cv2
import os
import sys


class ImageLabeler:
    def __init__(self, model_path="yolov8n.pt", output_dir="labeledImgs"):
        
        # Detect if running inside PyInstaller bundle
        if hasattr(sys, "_MEIPASS"):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")

        # Resolve full model path
        full_model_path = os.path.join(base_path, model_path)

        self.model = YOLO(full_model_path)
        self.output_dir = output_dir

        os.makedirs(self.output_dir, exist_ok=True)

    def label_image(self, image_path: str) -> str:

        results = self.model(image_path, verbose=False)

        # output_path = os.path.join(self.output_dir, "currentLabel.png")
        # cv2.imwrite(output_path, results[0].plot())

        return results[0].plot()
