"""Detached worker process that runs YOLO training and streams UI events.

The GUI does not train directly. It launches this script with file paths for:
- a state snapshot JSON (`training_state.json`)
- an append-only event stream (`training_events.jsonl`)
- a stop flag file used for graceful cancellation
"""

import argparse
import gc
import json
import os
import re
import shutil
import time
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
from pathlib import Path

from ultralytics import YOLO
from ultralytics.nn.tasks import load_checkpoint

from app_paths import app_base_dir
from training_config import TrainingConfig


class EventWriter:
    """Write both event stream updates and current-state snapshots.

    Events are append-only for logs/debug progress, while `state` is the latest
    consolidated view that polling UIs can read quickly.
    """

    def __init__(self, state_path: Path, events_path: Path):
        self.state_path = state_path
        self.events_path = events_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.events_path.parent.mkdir(parents=True, exist_ok=True)

        self.state = {
            "running": True,
            "progress": 0,
            "status": "Launching training...",
            "had_error": False,
            "was_aborted": False,
            "copied_best": False,
            "completion_counter": 0,
            "run_dir": "",
            "pid": os.getpid(),
            "updated_at": time.time(),
        }
        self.write_state()

    def emit(self, event_type: str, **payload) -> None:
        """Persist one event and fold key fields into the snapshot state."""
        event = {"type": event_type, "ts": time.time(), **payload}
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

        if event_type == "progress":
            self.state["progress"] = int(payload.get("progress", self.state["progress"]))
            self.state["status"] = str(payload.get("status", self.state["status"]))
        elif event_type == "run_dir":
            self.state["run_dir"] = str(payload.get("path", ""))
        elif event_type == "finished":
            self.state["running"] = False
            self.state["had_error"] = bool(payload.get("had_error", False))
            self.state["was_aborted"] = bool(payload.get("was_aborted", False))
            self.state["copied_best"] = bool(payload.get("copied_best", False))
            self.state["completion_counter"] = int(self.state.get("completion_counter", 0)) + 1
            if self.state["had_error"]:
                self.state["status"] = "Training failed"
            elif self.state["was_aborted"]:
                self.state["status"] = "Training aborted"
            else:
                self.state["status"] = "Training complete"

        self.state["updated_at"] = time.time()
        self.write_state()

    def write_state(self) -> None:
        # Atomic-ish replace prevents partially written JSON if process dies.
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)


WRITER = None


def emit(event_type: str, **payload) -> None:
    """Safe global event helper used throughout the subprocess."""
    if WRITER is not None:
        WRITER.emit(event_type, **payload)


def stop_requested(stop_file: Path) -> bool:
    """Stop signal is represented by existence of a shared flag file."""
    return stop_file.exists()


def clear_cuda_memory() -> None:
    """Best-effort release of CUDA memory so sequential runs are stable."""
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            if hasattr(torch.cuda, "ipc_collect"):
                torch.cuda.ipc_collect()
    except Exception:
        pass
    gc.collect()


def resolve_device(config_device):
    """Resolve training device using config override, env var, then auto-detect."""
    if config_device is not None:
        return config_device

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


def _checkpoint_is_resumable(path: str):
    """Check whether Ultralytics checkpoint has a non-negative epoch for resuming."""
    try:
        model, ckpt = load_checkpoint(path)
        epoch = int(ckpt.get("epoch", -1))
        if epoch < 0:
            # If epoch is -1, check train_results for actual last epoch
            train_results = ckpt.get("train_results", {})
            if "epoch" in train_results and train_results["epoch"]:
                epoch = int(train_results["epoch"][-1])
                # Update the checkpoint with correct epoch
                ckpt["epoch"] = epoch
                # Save the corrected checkpoint
                import torch
                torch.save({"model": model, **ckpt}, path)
                emit("debug", text=f"Debug: corrected checkpoint epoch from -1 to {epoch} at {path}")
        return epoch >= 0, epoch
    except Exception as exc:
        emit("debug", text=f"Debug: failed to inspect checkpoint for resume at {path}: {exc}")
        return False, None


# This grabs the next folder for storing information from the training run
def next_experiment_name(project_path: Path, requested_name: str) -> str:
    """Generate non-colliding run names (experiment1, experiment2, ...)."""
    name = (requested_name or "").strip() or "experiment1"
    project_path.mkdir(parents=True, exist_ok=True)

    requested_path = project_path / name
    if not requested_path.exists():
        return name

    match = re.fullmatch(r"^(.*?)(\d+)$", name)
    if match:
        prefix = match.group(1)
        start_index = int(match.group(2))
    else:
        prefix = name
        start_index = 1

    max_index = start_index
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    for child in project_path.iterdir():
        if not child.is_dir():
            continue
        folder_match = pattern.fullmatch(child.name)
        if folder_match:
            max_index = max(max_index, int(folder_match.group(1)))

    return f"{prefix}{max_index + 1}"


class StreamParser:
    def __init__(self, epochs: int):
        # Ultralytics writes carriage-return style progress; normalize to lines.
        self.buffer = ""

    def write(self, data):
        """File-like sink used by redirect_stdout/redirect_stderr."""
        if not data:
            return
        self.buffer += str(data).replace("\r", "\n")
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            self.handle_line(line.rstrip())

    def flush(self):
        if self.buffer.strip():
            self.handle_line(self.buffer.strip())
        self.buffer = ""

    def handle_line(self, line: str):
        """Translate selected library log lines into friendlier UI statuses."""
        if not line:
            return
        lower = line.lower()
        if "fast image access" in lower:
            emit("progress", progress=0, status="Preparing image cache for training...")
        if "amp:" in lower and "checks" in lower:
            emit("progress", progress=0, status="Running mixed-precision checks...")

        # Epoch/batch status is emitted from callbacks for accurate live progress.


class ProgressTracker:
    def __init__(self, epochs: int):
        # Keep lightweight timing/position signals for ETA + progress display.
        self.configured_epochs = epochs
        self.epoch_timestamps = {}
        self.last_progress_value = -1
        self.last_batch_index = -1
        self.internal_batch_counter = 0
        self.current_epoch = 1
        self.val_started_at = 0.0
        self.val_durations = []

    @staticmethod
    def format_eta(seconds: float) -> str:
        """Render ETA in compact human-readable format."""
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        if minutes > 0:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    def estimate_eta_text(self, current_epoch: int, total_epochs: int, epoch_fraction: float) -> str:
        """Estimate remaining time from average epoch throughput so far."""
        now = time.time()
        if 1 not in self.epoch_timestamps:
            self.epoch_timestamps[1] = now

        progress_epochs = (max(1, current_epoch) - 1) + max(0.0, min(1.0, epoch_fraction))
        if progress_epochs <= 0:
            return "calculating..."

        start = self.epoch_timestamps.get(1, now)
        elapsed = max(0.001, now - start)
        avg_seconds_per_epoch = elapsed / progress_epochs
        remaining = max(0.0, max(1, total_epochs) - progress_epochs)
        return self.format_eta(avg_seconds_per_epoch * remaining)

    def emit_batch_progress(self, trainer):
        """Emit high-frequency progress updates during training batches."""
        epoch_idx = int(getattr(trainer, "epoch", 0))
        total_epochs = int(getattr(getattr(trainer, "args", None), "epochs", 0) or self.configured_epochs)
        current_epoch = max(1, epoch_idx + 1)
        self.current_epoch = current_epoch

        batch_i = int(getattr(trainer, "batch_i", -1))
        num_batches = int(getattr(trainer, "nb", 0) or 0)
        if num_batches <= 0:
            # Fallback for versions where `nb` is not populated.
            try:
                train_loader = getattr(trainer, "train_loader", None)
                if train_loader is not None:
                    num_batches = len(train_loader)
            except Exception:
                num_batches = 0
        if num_batches <= 0:
            return

        if batch_i < 0:
            # Some callback contexts do not expose batch index; approximate.
            self.internal_batch_counter += 1
            effective_batch = min(self.internal_batch_counter, num_batches)
        else:
            effective_batch = max(1, min(batch_i + 1, num_batches))
            if effective_batch <= self.last_batch_index:
                # Guard against callback ordering duplicates/regressions.
                self.internal_batch_counter += 1
                effective_batch = min(max(effective_batch, self.internal_batch_counter), num_batches)

        prev_batch_index = self.last_batch_index
        batch_progress = max(0.0, min(1.0, effective_batch / max(1, num_batches)))
        overall_progress = ((current_epoch - 1) + batch_progress) / max(1, total_epochs)
        eta_text = self.estimate_eta_text(current_epoch, total_epochs, batch_progress)

        progress = int(batch_progress * 10000)
        progress = max(0, min(10000, progress))
        if progress == 0:
            progress = 1

        if progress == self.last_progress_value and effective_batch == prev_batch_index:
            # Skip duplicate events to reduce UI churn.
            return

        self.last_batch_index = effective_batch
        self.last_progress_value = progress
        emit(
            "progress",
            progress=progress,
            status=(
                f"Epoch {current_epoch}/{total_epochs} | Batch {effective_batch}/{num_batches} | "
                f"Overall {overall_progress * 100:.1f}% | ETA: {eta_text}"
            ),
        )

    def on_epoch_start(self, trainer):
        """Emit coarse progress when an epoch starts."""
        epoch_idx = int(getattr(trainer, "epoch", 0))
        total_epochs = int(getattr(getattr(trainer, "args", None), "epochs", 0) or self.configured_epochs)
        current_epoch = max(1, epoch_idx + 1)
        self.current_epoch = current_epoch
        self.last_batch_index = -1
        self.internal_batch_counter = 0
        eta_text = self.estimate_eta_text(current_epoch, total_epochs, 0.0)
        progress = int((current_epoch / max(1, total_epochs)) * 10000)
        progress = max(0, min(10000, progress))
        self.last_progress_value = progress
        emit("progress", progress=progress, status=f"Epoch {current_epoch}/{total_epochs} | ETA: {eta_text}")

    def on_epoch_end(self, trainer):
        """Emit coarse progress when an epoch completes."""
        epoch_idx = int(getattr(trainer, "epoch", 0))
        total_epochs = int(getattr(getattr(trainer, "args", None), "epochs", 0) or self.configured_epochs)
        current_epoch = max(1, epoch_idx + 1)
        self.current_epoch = current_epoch
        eta_text = self.estimate_eta_text(current_epoch, total_epochs, 1.0)
        progress = int((current_epoch / max(1, total_epochs)) * 10000)
        progress = max(0, min(10000, progress))
        self.last_progress_value = progress
        emit("progress", progress=progress, status=f"Epoch {current_epoch}/{total_epochs} complete | ETA: {eta_text}")

    def on_val_start(self):
        """Emit validation-start status, optionally with duration estimate."""
        self.val_started_at = time.time()
        total_epochs = self.configured_epochs
        current_epoch = max(1, min(self.current_epoch, total_epochs))
        if self.val_durations:
            avg_seconds = sum(self.val_durations) / len(self.val_durations)
            eta_text = self.format_eta(avg_seconds)
            status = f"Validating epoch {current_epoch}/{total_epochs}... (est. {eta_text})"
        else:
            status = f"Validating epoch {current_epoch}/{total_epochs}..."
        emit("progress", progress=0, status=status)

    def on_val_end(self):
        """Emit validation completion and update rolling validation timings."""
        total_epochs = self.configured_epochs
        current_epoch = max(1, min(self.current_epoch, total_epochs))
        progress = int((min(current_epoch, total_epochs) / max(1, total_epochs)) * 10000)
        progress = max(0, min(10000, progress))
        self.last_progress_value = progress

        duration = 0.0
        if self.val_started_at > 0:
            duration = max(0.0, time.time() - self.val_started_at)
            self.val_durations.append(duration)
            if len(self.val_durations) > 20:
                self.val_durations = self.val_durations[-20:]
        emit(
            "progress",
            progress=progress,
            status=f"Epoch {current_epoch}/{total_epochs} validation complete ({self.format_eta(duration)})",
        )


def try_copy_best(run_dir: Path, base_dir: Path) -> bool:
    """Copy run weights to the canonical model location used by prediction."""
    source = run_dir / "weights" / "best.pt"
    if not source.exists():
        return False
    dest = base_dir / "Models" / "best.pt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source, dest)
    emit("debug", text=f"Debug: copied best.pt from {source}")
    return True


def parse_args():
    """CLI contract used by training_session when launching subprocess."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--drive", required=True)
    parser.add_argument("--stop-file", required=True)
    parser.add_argument("--config-json", required=True)
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--events-file", required=True)
    return parser.parse_args()


def main() -> int:
    """Execute one training run and report status through event/state files."""
    global WRITER
    args = parse_args()
    base_dir = app_base_dir()
    stop_file = Path(args.stop_file)
    state_file = Path(args.state_file)
    events_file = Path(args.events_file)
    config = TrainingConfig(**json.loads(args.config_json))
    WRITER = EventWriter(state_path=state_file, events_path=events_file)

    had_error = False
    was_aborted = False
    copied_best = False
    run_dir = None

    # Record resolved config for troubleshooting mismatched runs.
    emit("debug", text=f"Debug: subprocess config={asdict(config)}")

    try:
        emit("progress", progress=0, status="Checking dataset configuration...")
        data_path = Path(args.drive) / "data.yaml"
        if not data_path.exists():
            # Fallback supports packaged app runs where dataset yaml lives by app.
            fallback = base_dir / "data.yaml"
            if fallback.exists():
                data_path = fallback
            else:
                raise FileNotFoundError(
                    f"Could not find data.yaml in {Path(args.drive)} or {base_dir}"
                )

        project_path = Path(config.project)
        if not project_path.is_absolute():
            project_path = (base_dir / project_path).resolve()

        # When resuming, use the existing run name; otherwise generate a new one.
        if config.resume:
            run_name = config.name
        else:
            run_name = next_experiment_name(project_path, config.name)
        run_dir = (project_path / run_name).resolve()
        emit("run_dir", path=str(run_dir))

        parser_stream = StreamParser(config.epochs)
        progress_tracker = ProgressTracker(config.epochs)
        emit("progress", progress=0, status="Loading YOLO model...")

        # Resolve model path: if relative, try Models/ first (for checkpoints), then base_dir.
        model_path = config.model
        if model_path and not Path(model_path).is_absolute():
            # First check if it's a checkpoint in Models/ (e.g., "experiment6/weights/best.pt")
            models_check = (project_path / model_path).resolve()
            if models_check.exists():
                model_path = str(models_check)
                print(f"Resolved model path from project directory: {model_path}")
            else:
                # Fall back to resolving from base_dir (for base models like "yolov8s.pt")
                model_path = str((base_dir / model_path).resolve())
                print(f"Resolved model path from base directory: {model_path}")

        # Route Ultralytics stdout/stderr through parser so UI can show key stages.
        with redirect_stdout(parser_stream), redirect_stderr(parser_stream):  # type: ignore
            model = YOLO(model_path)

            def on_train_start(trainer):
                # First callback confirms trainer loop is active.
                emit("progress", progress=0, status="Training loop started...")
                if stop_requested(stop_file):
                    trainer.stop = True

            def on_train_batch_end(trainer):
                # Batch updates produce smoother progress than epoch-only updates.
                progress_tracker.emit_batch_progress(trainer)
                if stop_requested(stop_file):
                    trainer.stop = True

            def on_train_epoch_start(trainer):
                progress_tracker.on_epoch_start(trainer)
                if stop_requested(stop_file):
                    trainer.stop = True

            def on_train_epoch_end(trainer):
                progress_tracker.on_epoch_end(trainer)
                if stop_requested(stop_file):
                    trainer.stop = True

            def on_val_start(trainer):
                progress_tracker.on_val_start()
                if stop_requested(stop_file):
                    trainer.stop = True
                    emit("progress", progress=0, status="Stopping training...")

            def on_val_end(trainer):
                progress_tracker.on_val_end()
                if stop_requested(stop_file):
                    trainer.stop = True
                    emit("progress", progress=0, status="Stopping training...")

            # Register lifecycle callbacks before invoking model.train.
            model.add_callback("on_train_start", on_train_start)
            model.add_callback("on_train_epoch_start", on_train_epoch_start)
            model.add_callback("on_train_batch_end", on_train_batch_end)
            # Also hook batch-start to capture progress for versions with sparse end events.
            model.add_callback("on_train_batch_start", on_train_batch_end)
            model.add_callback("on_train_epoch_end", on_train_epoch_end)
            model.add_callback("on_val_start", on_val_start)
            model.add_callback("on_val_end", on_val_end)

            device = resolve_device(config.device)
            emit("debug", text=f"Debug: device={device}")
            emit("progress", progress=0, status="Building training data...")

            # YOLO handles dataloader build + training loop + validation internally.

            resume_arg = None
            if config.resume:
                emit("debug", text=f"Debug: resume=True, resuming from {config.model}")

                if model_path and Path(model_path).exists():
                    # Check if resumable and not completed
                    resumable, ckpt_epoch = _checkpoint_is_resumable(model_path)
                    if resumable and ckpt_epoch >= config.epochs:
                        resume_arg = False
                        emit("log", text=f"Checkpoint has already completed {ckpt_epoch} epochs (target: {config.epochs}). Starting fresh training from weights.")
                        emit("debug", text=f"Debug: checkpoint already finished, using as pretrained weights")
                    elif resumable and ckpt_epoch < config.epochs:
                        resume_arg = model_path
                        emit("debug", text=f"Debug: training will resume from checkpoint {resume_arg} (epoch {ckpt_epoch})")
                    else:
                        resume_arg = model_path  # Try anyway, fallback will handle
                        emit("debug", text=f"Debug: attempting resume from checkpoint {resume_arg} (epoch {ckpt_epoch}), will fallback if fails")
                else:
                    resume_arg = False
                    emit("log", text=f"Resume path {model_path} not found. Starting fresh training.")
                    emit("debug", text=f"Debug: resume requested but path does not exist: {model_path}")

            try:
                results = model.train(
                    data=str(data_path),
                    epochs=config.epochs,
                    imgsz=config.imgsz,
                    batch=config.batch,
                    device=device,
                    patience=config.patience,
                    workers=config.workers,
                    project=str(project_path),
                    name=run_name,
                    exist_ok=True,
                    verbose=True,
                    resume=resume_arg,
                )
            except AssertionError as e:
                if "nothing to resume" in str(e) and resume_arg:
                    emit("log", text=f"Resume failed: {e}. Falling back to fresh training from weights.")
                    emit("debug", text=f"Debug: resume assertion failed, retrying with resume=False")
                    results = model.train(
                        data=str(data_path),
                        epochs=config.epochs,
                        imgsz=config.imgsz,
                        batch=config.batch,
                        device=device,
                        patience=config.patience,
                        workers=config.workers,
                        project=str(project_path),
                        name=run_name,
                        exist_ok=True,
                        verbose=True,
                        resume=False,  # Fallback to fresh training
                    )
                else:
                    raise
            parser_stream.flush()

        # save_dir can vary by Ultralytics version; fallback to planned run_dir.
        result_dir = Path(getattr(results, "save_dir", run_dir))
        copied_best = try_copy_best(result_dir, base_dir)
        was_aborted = stop_requested(stop_file)

        if was_aborted:
            emit("progress", progress=0, status="Training aborted")
            if copied_best:
                emit("log", text="Training aborted by user. Best weights were preserved.")
            else:
                emit("log", text="Training aborted by user.")
        else:
            if copied_best:
                emit("progress", progress=10000, status="Training complete")
            else:
                had_error = True
                emit("progress", progress=0, status="Training failed")
                emit("log", text=f"Training ended, but best.pt was not found in: {result_dir}")

    except KeyboardInterrupt:
        # Handles Ctrl+C and similar interrupts cleanly.
        was_aborted = True
        emit("progress", progress=0, status="Training aborted")
        if run_dir is not None:
            copied_best = try_copy_best(run_dir, base_dir)
        if copied_best:
            emit("log", text="Training interrupted. Best weights were preserved.")
        else:
            emit("log", text="Training interrupted.")
    except Exception as exc:
        # Distinguish user-requested stop from genuine runtime failures.
        if stop_requested(stop_file):
            was_aborted = True
            emit("progress", progress=0, status="Training aborted")
            if run_dir is not None:
                copied_best = try_copy_best(run_dir, base_dir)
            if copied_best:
                emit("log", text="Training aborted by user. Best weights were preserved.")
            else:
                emit("log", text="Training aborted by user.")
        else:
            had_error = True
            emit("progress", progress=0, status="Training failed")
            emit("log", text=f"Training failed: {exc}")
    finally:
        # Always publish terminal state and cleanup stop flag for next run.
        emit("progress", progress=0, status="Releasing GPU resources...")
        clear_cuda_memory()
        emit(
            "finished",
            had_error=had_error,
            was_aborted=was_aborted,
            copied_best=copied_best,
            run_dir=str(run_dir) if run_dir else "",
        )
        try:
            stop_file.unlink(missing_ok=True)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
