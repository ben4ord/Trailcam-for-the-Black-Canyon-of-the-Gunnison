"""Prediction helpers wrapping Ultralytics YOLO outputs for the GUI layer."""

from ultralytics import YOLO
from pathlib import Path
import numpy as np
import math
import cv2

class ImageLabeler:
    def __init__(self):
        # Resolve full model path
        full_model_path = Path.cwd() /"Models/best_3-24-2026.pt"
        # Model is loaded once so repeated image predictions are fast.
        self.model = YOLO(full_model_path)

    def predict(self, image_path: str):
        """Run inference and return first result object for a single image path."""
        results = self.model(image_path, verbose=False)
        return results[0]

   
    def label_image(self, image_path: str) -> np.ndarray:
        """Return image array with YOLO-drawn boxes/labels."""
        return self.predict(image_path).plot()
    
    def get_detections(self, image_path: str) -> list[dict]:
        """Convert raw YOLO boxes into plain dictionaries for UI consumption."""
        img = cv2.imread(image_path)
        if img is None:
            print(f"Skipping invalid image in predict: {image_path}")
            return None  # CRITICAL
        result = self.predict(image_path)
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:
            return []

        class_ids = boxes.cls.tolist()
        confidences = boxes.conf.tolist()
        xyxy = boxes.xyxy.tolist()
        xywhn = boxes.xywhn.tolist()

        detections = []

        for class_id, conf, box_xyxy, box_xywhn in zip(
            class_ids, confidences, xyxy, xywhn
        ):
            # Keep both pixel and normalized box formats for downstream tools.
            detections.append({
                "class_id": int(class_id),
                "class_name": result.names[int(class_id)],
                "confidence": float(conf),
                "bbox_xyxy": box_xyxy,
                "bbox_xywhn": box_xywhn,
            })

        return detections
    

    def get_conf_scores_single(self, image_path):
        if self.check_image_corruption(image_path):
            results = self.model(image_path,verbose=False)

            r = results[0]

            if r.boxes is None or len(r.boxes) == 0:
                return {"class_ids": [], "confidences": []}
            

            return {
                "class_ids": r.boxes.cls.tolist(),
                "confidences": r.boxes.conf.tolist(),
                "bbox_xyxy": r.boxes.xyxy.tolist(),
                "bbox_xywhn": r.boxes.xywhn.tolist(),
                "image_path": image_path
            }
        else:
            return None

    
    
    @staticmethod
    def to_yolo_label_lines(detections) -> list[str]:
        """Serialize detection dictionaries to YOLO txt label line format."""
        if not detections:
            return []

        lines = []

        for det in detections:
            class_id = int(det["class_id"])
            x_center, y_center, width, height = det["bbox_xywhn"]

            lines.append(
                f"{class_id} "
                f"{x_center:.6f} "
                f"{y_center:.6f} "
                f"{width:.6f} "
                f"{height:.6f}"
            )

        return lines
    
    def check_image_corruption(self, image_path):
        valid_image = cv2.imread(image_path)
        if valid_image is None:
            return False
        else:
            return True

