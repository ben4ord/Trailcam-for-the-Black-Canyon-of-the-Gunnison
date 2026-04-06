from dataclasses import dataclass


# Eventually this will be modified to have the model passed in be dynamic based on the user selected model dropdown

@dataclass(slots=True)
class TrainingConfig:
    """Serializable training hyperparameters passed to training_subprocess.

    Values are intentionally simple types so they can be JSON-encoded by
    `training_session` and reconstructed in `training_subprocess`.
    """
    # Base checkpoint or model architecture file passed to `YOLO(...)`.
    model: str = "yolov8s.pt"
    # Total epochs to train.
    epochs: int = 300
    # Image size used for both train and val transforms.
    imgsz: int = 512
    # Batch size per optimizer step.
    batch: int = 4
    # Device selection: int GPU index, "cpu", "mps", or None for auto.
    device: int | str | None = 0
    # Early-stop patience in epochs without improvement.
    patience: int = 15
    # Mosaic Value modified the data augmentation levels
    mosaic: float = 0.2
    # Data loader worker processes; 0 keeps loading in main process.
    workers: int = 0
    # Output root for run artifacts.
    project: str = "Models"
    # Preferred run folder base name (auto-incremented if it exists).
    name: str = "experiment1"
    # Resume field to continue training from a previous run
    resume: bool | None = None

    @classmethod
    def small(cls) -> "TrainingConfig":
        return cls(
            model="yolov8s.pt",
            epochs=300,
            imgsz=512,
            batch=4,
            device=0,
            patience=15,
            mosaic=0.2,
            workers=0,
            project="Models",
            name="experiment1",
        )

    @classmethod
    def medium(cls) -> "TrainingConfig":
        return cls(
            model="yolov8s.pt",
            epochs=300,
            imgsz=640,
            batch=12,
            device=0,
            patience=15,
            mosaic=0.2,
            workers=0,
            project="Models",
            name="experiment1",
        )

    @classmethod
    def large(cls) -> "TrainingConfig":
        return cls(
            model="yolov8s.pt",
            epochs=300,
            imgsz=724,
            batch=24,
            device=0,
            patience=15,
            mosaic=0.2,
            workers=0,
            project="Models",
            name="experiment1",
        )
