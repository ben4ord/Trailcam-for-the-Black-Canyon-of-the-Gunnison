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
    epochs: int = 200
    # Image size used for both train and val transforms.
    imgsz: int = 512
    # Batch size per optimizer step.
    batch: int = 32
    # Device selection: int GPU index, "cpu", "mps", or None for auto.
    device: int | str | None = 0
    # Early-stop patience in epochs without improvement.
    patience: int = 15
    # Data loader worker processes; 0 keeps loading in main process.
    workers: int = 0
    # Output root for run artifacts.
    project: str = "Models"
    # Preferred run folder base name (auto-incremented if it exists).
    name: str = "experiment1"
    # Resume field to continue training from a previous run
    resume: bool | None = None
