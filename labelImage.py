from ultralytics import YOLO
import cv2
import os

class ImageLabeler:
    def __init__(self, model_path="yolov8n.pt", output_dir="labeledImgs"):
        self.model = YOLO(model_path)
        self.output_dir = output_dir

        os.makedirs(self.output_dir, exist_ok=True)

    def label_image(self, image_path: str) -> str:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        results = self.model(image)

        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls = int(box.cls[0])

                label = f"{self.model.names[cls]} {conf:.2f}"

                cv2.rectangle(image, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(
                    image,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 0, 0),
                    2
                )

        output_path = os.path.join(self.output_dir, "currentLabel.png")
        cv2.imwrite(output_path, image)

        return output_path
