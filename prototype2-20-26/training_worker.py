from PySide6.QtCore import QObject, Signal
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from ultralytics import YOLO
import shutil
import traceback
import time
import gc
import os
import re

class TrainingWorker(QObject):
    log_signal = Signal(str)
    progress_signal = Signal(int, str)
    debug_signal = Signal(str)
    finished = Signal()

    class _SignalStream:
        def __init__(self, emit_fn):
            self.emit_fn = emit_fn
            self._buffer = ""

        def write(self, data):
            if not data:
                return
            self._buffer += str(data).replace("\r", "\n")
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                line = line.rstrip()
                if line:
                    self.emit_fn(line)

        def flush(self):
            if self._buffer.strip():
                self.emit_fn(self._buffer.strip())
            self._buffer = ""

    def __init__(self, training_cmd, drive):
        super().__init__()
        self.training_cmd = list(training_cmd or [])
        self.drive = drive

        self._running = True
        self.had_error = False
        self.was_aborted = False

        self.base_dir = Path(__file__).resolve().parent
        self.models_dir = self.base_dir / "Models"
        self.models_dir.mkdir(exist_ok=True)

        self._configured_epochs = self._parse_int_arg("epochs=", 200)
        self._imgsz = self._parse_int_arg("imgsz=", 512)
        self._batch = self._parse_int_arg("batch=", 32)
        self._patience = self._parse_int_arg("patience=", 15)
        self._workers = self._parse_int_arg("workers=", 0)
        self._project = self._parse_str_arg("project=", "Models")
        self._name = self._parse_str_arg("name=", "experiment1")
        self._device = self._parse_device_arg("device=", None)
        self._project_path = Path(self._project)
        if not self._project_path.is_absolute():
            self._project_path = (self.base_dir / self._project_path).resolve()

        self._trainer = None
        self._model = None
        self._epoch_timestamps = {}
        self._epoch_regex = re.compile(r"\b(\d+)\s*/\s*(\d+)\b")
        self._last_prep_debug = 0.0
        self._last_parsed_epoch = None
        self._last_progress_value = -1
        self._last_batch_seen_at = 0.0
        self._batch_seen_debug_emitted = False
        self._epoch_started = False
        self._last_batch_index = -1
        self._internal_batch_counter = 0

    def _parse_str_arg(self, prefix, default):
        for token in self.training_cmd:
            if isinstance(token, str) and token.startswith(prefix):
                value = token[len(prefix):].strip()
                if value:
                    return value
        return default

    def _parse_int_arg(self, prefix, default):
        value = self._parse_str_arg(prefix, str(default))
        try:
            return int(value)
        except Exception:
            return default

    def _parse_device_arg(self, prefix, default):
        value = self._parse_str_arg(prefix, "")
        if value == "":
            return default
        try:
            return int(value)
        except Exception:
            return value

    @staticmethod
    def _format_eta(seconds):
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        if minutes > 0:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    def _emit_epoch_progress(self, current_epoch, total_epochs):
        now = time.time()
        if current_epoch not in self._epoch_timestamps:
            self._epoch_timestamps[current_epoch] = now

        # Progress is emitted in basis points (0..10000) for smooth UI movement.
        progress = int((current_epoch / max(1, total_epochs)) * 10000)
        progress = max(0, min(10000, progress))
        if current_epoch >= 1 and total_epochs > 1 and progress == 0:
            progress = 1

        if current_epoch <= 1:
            eta_text = "calculating..."
        else:
            start = self._epoch_timestamps.get(1, now)
            elapsed = max(0.001, now - start)
            avg_seconds_per_epoch = elapsed / max(1, current_epoch - 1)
            remaining = max(0, total_epochs - current_epoch)
            eta_text = self._format_eta(avg_seconds_per_epoch * remaining)

        self._last_progress_value = progress
        self.progress_signal.emit(progress, f"Epoch {current_epoch}/{total_epochs} | ETA: {eta_text}")

    def _emit_batch_progress(self, trainer):
        if not self._running:
            return

        epoch_idx = int(getattr(trainer, "epoch", 0))
        total_epochs = int(getattr(getattr(trainer, "args", None), "epochs", 0) or self._configured_epochs)
        current_epoch = max(1, epoch_idx + 1)

        batch_i = int(getattr(trainer, "batch_i", -1))
        num_batches = int(getattr(trainer, "nb", 0) or 0)

        if num_batches <= 0:
            try:
                train_loader = getattr(trainer, "train_loader", None)
                if train_loader is not None:
                    num_batches = len(train_loader)
            except Exception:
                num_batches = 0

        if num_batches <= 0:
            if not self._batch_seen_debug_emitted:
                self._batch_seen_debug_emitted = True
                self.debug_signal.emit("Debug: batch callback active, but total batch count is unavailable.")
            return

        self._last_batch_seen_at = time.time()
        if not self._batch_seen_debug_emitted:
            self._batch_seen_debug_emitted = True
            self.debug_signal.emit(f"Debug: batch callback active ({num_batches} batches/epoch).")

        # Some ultralytics builds expose batch_i inconsistently in callbacks.
        # Use an internal fallback counter so progress still moves.
        if batch_i < 0:
            self._internal_batch_counter += 1
            effective_batch = min(self._internal_batch_counter, num_batches)
        else:
            effective_batch = max(1, min(batch_i + 1, num_batches))
            # Ensure monotonic movement even if callback repeats same index.
            if effective_batch <= self._last_batch_index:
                self._internal_batch_counter += 1
                effective_batch = min(max(effective_batch, self._internal_batch_counter), num_batches)

        prev_batch_index = self._last_batch_index
        batch_progress = max(0.0, min(1.0, effective_batch / max(1, num_batches)))
        overall_progress = ((current_epoch - 1) + batch_progress) / max(1, total_epochs)

        # Drive bar from per-epoch progress so users see continuous motion.
        progress = int(batch_progress * 10000)
        progress = max(0, min(10000, progress))
        if progress == 0:
            progress = 1

        # Avoid flooding UI only when both progress and batch index are unchanged.
        if progress == self._last_progress_value and effective_batch == prev_batch_index:
            return

        self._last_batch_index = effective_batch
        self._last_progress_value = progress
        self.progress_signal.emit(
            progress,
            f"Epoch {current_epoch}/{total_epochs} | Batch {effective_batch}/{num_batches} | Overall {overall_progress * 100:.1f}%"
        )

    def _handle_train_output_line(self, line):
        lower = line.lower()
        if not self._epoch_started and "fast image access" in lower:
            self.progress_signal.emit(0, "Preparing image cache for training...")
            now = time.time()
            if now - self._last_prep_debug > 5:
                self._last_prep_debug = now
                self.debug_signal.emit("Debug: still preparing fast image cache...")

        if not self._epoch_started and "amp:" in lower and "checks" in lower:
            self.progress_signal.emit(0, "Running mixed-precision checks...")

        match = self._epoch_regex.search(line)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            if 1 <= current <= total <= 10000 and total == self._configured_epochs:
                if self._last_parsed_epoch != (current, total):
                    self._last_parsed_epoch = (current, total)
                    self._emit_epoch_progress(current, total)
                    self.debug_signal.emit(f"Debug: epoch parsed from output {current}/{total}")

    @staticmethod
    def _clear_cuda_memory():
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                if hasattr(torch.cuda, "ipc_collect"):
                    torch.cuda.ipc_collect()
        except Exception:
            pass
        gc.collect()

    def _resolve_device(self):
        if self._device is not None:
            return self._device

        forced = os.getenv("TRAILCAM_TRAIN_DEVICE", "").strip()
        if forced:
            return forced

        try:
            import torch
            if torch.cuda.is_available():
                return 0
        except Exception:
            pass

        return "cpu"

    def stop(self):
        self._running = False
        self.was_aborted = True
        self.progress_signal.emit(0, "Stopping training...")
        self.debug_signal.emit("Debug: abort requested.")
        trainer = self._trainer
        if trainer is not None:
            try:
                trainer.stop = True
            except Exception:
                pass

    def _on_train_start(self, trainer):
        self._trainer = trainer
        self.progress_signal.emit(0, "Training loop started...")
        self.debug_signal.emit("Debug: train loop started.")
        if not self._running:
            trainer.stop = True

    def _on_train_epoch_start(self, trainer):
        self._trainer = trainer
        if not self._running:
            trainer.stop = True
            return

        self._epoch_started = True
        epoch_idx = int(getattr(trainer, "epoch", 0))
        total_epochs = int(getattr(getattr(trainer, "args", None), "epochs", 0) or self._configured_epochs)
        current_epoch = max(1, epoch_idx + 1)
        self._last_batch_seen_at = time.time()
        self._batch_seen_debug_emitted = False
        self._last_batch_index = -1
        self._internal_batch_counter = 0
        self._emit_epoch_progress(current_epoch, total_epochs)
        self.debug_signal.emit(f"Debug: epoch started {current_epoch}/{total_epochs}")

    def _on_train_batch_end(self, trainer):
        self._trainer = trainer
        self._emit_batch_progress(trainer)
        if not self._running:
            trainer.stop = True

    def _on_train_epoch_end(self, trainer):
        self._trainer = trainer
        if not self._running:
            trainer.stop = True
            return

        epoch_idx = int(getattr(trainer, "epoch", 0))
        total_epochs = int(getattr(getattr(trainer, "args", None), "epochs", 0) or self._configured_epochs)
        current_epoch = max(1, epoch_idx + 1)
        self._emit_epoch_progress(current_epoch, total_epochs)
        self.debug_signal.emit(f"Debug: epoch completed {current_epoch}/{total_epochs}")

    def run(self):
        self.had_error = False
        self.was_aborted = False
        self._running = True
        self._trainer = None
        self._model = None
        self._epoch_timestamps = {}
        self._last_prep_debug = 0.0
        self._last_parsed_epoch = None
        self._last_progress_value = -1
        self._last_batch_seen_at = 0.0
        self._batch_seen_debug_emitted = False
        self._epoch_started = False
        self._last_batch_index = -1
        self._internal_batch_counter = 0

        try:
            self.progress_signal.emit(0, "Checking dataset configuration...")

            data_path = Path(self.drive) / "data.yaml"
            if not data_path.exists():
                fallback = self.base_dir / "data.yaml"
                if fallback.exists():
                    data_path = fallback
                else:
                    raise FileNotFoundError(
                        f"Could not find data.yaml in {Path(self.drive)} or {self.base_dir}"
                    )

            save_dir = (self._project_path / self._name).resolve()
            self.debug_signal.emit(
                f"Debug: epochs={self._configured_epochs}, workers={self._workers}, save_dir={save_dir}"
            )

            stream = self._SignalStream(self._handle_train_output_line)
            self.progress_signal.emit(0, "Loading YOLO model...")

            with redirect_stdout(stream), redirect_stderr(stream):
                model = YOLO("yolov8s.pt")
                self._model = model
                model.add_callback("on_train_start", self._on_train_start)
                model.add_callback("on_train_epoch_start", self._on_train_epoch_start)
                model.add_callback("on_train_batch_end", self._on_train_batch_end)
                model.add_callback("on_train_epoch_end", self._on_train_epoch_end)
                model.add_callback("on_train_batch_start", self._on_train_batch_end)

                device = self._resolve_device()
                if device is None: 
                    device = "cpu"
                
                self.debug_signal.emit(f"Debug: device={device}")
                self.progress_signal.emit(0, "Building training data...")

                results = model.train(
                    data=str(data_path),
                    epochs=self._configured_epochs,
                    imgsz=self._imgsz,
                    batch=self._batch,
                    device=device,
                    patience=self._patience,
                    workers=self._workers,
                    project=str(self._project_path),
                    name=self._name,
                    exist_ok=True,
                    verbose=True,
                )
                stream.flush()

            if self._last_batch_seen_at > 0:
                idle = time.time() - self._last_batch_seen_at
                if idle > 120:
                    self.debug_signal.emit(
                        "Debug: no batch callback activity for >120s; training may be stalled in dataloader/augment stage."
                    )

            if self.was_aborted:
                self.progress_signal.emit(0, "Training aborted")
                self.log_signal.emit("Training aborted by user.")
            else:
                result_dir = Path(getattr(results, "save_dir", save_dir))
                self.debug_signal.emit(f"Debug: actual results save_dir={result_dir}")
                source_model = result_dir / "weights" / "best.pt"
                if source_model.exists():
                    shutil.copy(source_model, self.models_dir / "best.pt")
                    self.progress_signal.emit(10000, "Training complete")
                else:
                    self.had_error = True
                    self.progress_signal.emit(0, "Training failed")
                    self.log_signal.emit(f"Training ended, but best.pt was not found in: {result_dir}")

        except Exception as exc:
            if self.was_aborted:
                self.progress_signal.emit(0, "Training aborted")
                self.log_signal.emit("Training aborted by user.")
            else:
                self.had_error = True
                self.progress_signal.emit(0, "Training failed")
                self.log_signal.emit(f"Training failed: {exc}")
                self.log_signal.emit(traceback.format_exc())
        finally:
            self.progress_signal.emit(0, "Releasing GPU resources...")
            self._trainer = None
            self._model = None
            self._clear_cuda_memory()
            self.finished.emit()
