from ultralytics import YOLO
import os
import sys
import numpy as np
from pathlib import Path
class ImageLabeler:
    def __init__(self):
        # Resolve full model path
        full_model_path = Path.cwd() /"Models/best_3-3-2026.pt"
        self.model = YOLO(full_model_path)

    def predict(self, image_path: str):
        results = self.model(image_path, verbose=False)
        return results[0]

   
    def label_image(self, image_path: str) -> np.ndarray:
        return self.predict(image_path).plot()
    
    def get_detections(self, image_path: str) -> list[dict]:
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
            detections.append({
                "class_id": int(class_id),
                "class_name": result.names[int(class_id)],
                "confidence": float(conf),
                "bbox_xyxy": box_xyxy,
                "bbox_xywhn": box_xywhn,
            })

        return detections
    
    
    @staticmethod
    def to_yolo_label_lines(detections) -> list[str]:
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