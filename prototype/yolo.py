import cv2
from ultralytics import YOLO

# Load a pretrained YOLOv8n model
model = YOLO('yolov8n.pt')

def detect_objects(image_path, conf=0.6):
    #run yolo detection on image, return image with bounding boxes drawn (which is a numpy array)
    results = model.predict(source=str(image_path), conf=conf, verbose=False)
    detected_img = results[0].plot()
    return detected_img
