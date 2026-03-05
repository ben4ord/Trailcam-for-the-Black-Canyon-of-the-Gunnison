from dataclasses import dataclass


@dataclass(slots=True)
class TrainingConfig:
    model: str = "yolov8s.pt"
    epochs: int = 200
    imgsz: int = 512
    batch: int = 32
    device: int | str | None = 0
    patience: int = 15
    workers: int = 0
    project: str = "Models"
    name: str = "experiment1"
