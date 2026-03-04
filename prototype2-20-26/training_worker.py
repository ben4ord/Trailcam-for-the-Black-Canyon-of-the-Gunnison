from PySide6.QtCore import QObject, Signal
from pathlib import Path
import shutil
from ultralytics import YOLO
import traceback
import os
from contextlib import redirect_stdout, redirect_stderr



class TrainingWorker(QObject):
    log_signal = Signal(str)
    finished = Signal()

    def __init__(self, training_cmd, drive):
        super().__init__()
        self.training_cmd = training_cmd
        self._running = True
        self.had_error = False

        self.models_dir = Path("Models")
        self.models_dir.mkdir(exist_ok=True)
        self.drive = drive

    def stop(self):
        self._running = False

    # Stream the signal to the gui
    class _SignalStream:
        def __init__(self, emit_fn):
            self.emit_fn = emit_fn
            self._buffer = ""

        def write(self, data):
            if not data:
                return

            self._buffer += str(data)
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                line = line.rstrip()
                if line:
                    self.emit_fn(line)

        def flush(self):
            if self._buffer.strip():
                self.emit_fn(self._buffer.strip())
            self._buffer = ""

    def _resolve_device(self):
        forced_device = os.getenv("TRAILCAM_TRAIN_DEVICE", "").strip()
        if forced_device:
            self.log_signal.emit(f"Device override from env: TRAILCAM_TRAIN_DEVICE={forced_device}")
            return forced_device

        try:
            import torch

            if torch.cuda.is_available():
                return 0
            self.log_signal.emit("CUDA not available in torch. Falling back to CPU.")
        except Exception:
            self.log_signal.emit("Torch import failed while selecting device. Falling back to CPU.")

        return "cpu"

    def _log_runtime_info(self):
        try:
            import ultralytics
            self.log_signal.emit(f"Ultralytics version: {ultralytics.__version__}")
        except Exception as exc:
            self.log_signal.emit(f"Could not read Ultralytics version: {exc}")

        try:
            import torch
            self.log_signal.emit(f"Torch version: {torch.__version__}")
            self.log_signal.emit(f"CUDA available: {torch.cuda.is_available()}")
            self.log_signal.emit(f"Torch CUDA build: {torch.version.cuda}")

            if torch.cuda.is_available() and torch.cuda.device_count() > 0:
                self.log_signal.emit(f"CUDA device: {torch.cuda.get_device_name(0)}")
        except Exception as exc:
            self.log_signal.emit(f"Torch runtime check failed: {exc}")

    def run(self):
        self.had_error = False

        try:
            stream = self._SignalStream(self.log_signal.emit)

            with redirect_stdout(stream), redirect_stderr(stream):
                self._log_runtime_info()

                data_path = Path(self.drive) / "data.yaml"
                if not data_path.exists():
                    fallback = Path(__file__).resolve().parent / "data.yaml"
                    if fallback.exists():
                        data_path = fallback
                        self.log_signal.emit(
                            f"data.yaml not found in selected folder. Using: {data_path}"
                        )
                    else:
                        raise FileNotFoundError(
                            f"Could not find data.yaml in {Path(self.drive)} "
                            f"or {Path(__file__).resolve().parent}"
                        )

                self.log_signal.emit("Loading YOLO base model: yolov8s.pt")
                model = YOLO("yolov8s.pt")

                device = self._resolve_device()
                self.log_signal.emit(f"Training device: {device}")
                self.log_signal.emit(f"Starting training with config: {data_path}")
                results = model.train(
                    data=str(data_path),
                    epochs=200,
                    imgsz=512,
                    batch=32,
                    device=device,
                    patience=15,
                    project="Models",
                    name="experiment1"
                )

                stream.flush()

            save_dir = Path(results.save_dir)
            source_model = save_dir / "weights" / "best.pt"

            if source_model.exists():
                shutil.copy(source_model, self.models_dir / "best.pt")
                self.log_signal.emit(f"Model saved to: {self.models_dir / 'best.pt'}")
            else:
                self.log_signal.emit(f"Training ended, but best.pt was not found in: {save_dir}")

        except Exception as exc:
            self.had_error = True
            self.log_signal.emit(f"Training failed: {exc}")
            self.log_signal.emit(traceback.format_exc())
        finally:
            self.finished.emit()
