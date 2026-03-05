from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path

from app_paths import app_base_dir
from training_config import TrainingConfig


class TrainingSession:
    def __init__(self):
        self._lock = threading.Lock()
        self.base_dir = app_base_dir()
        self.runtime_dir = self.base_dir / "runtime"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.runtime_dir / "training_state.json"
        self.events_file = self.runtime_dir / "training_events.jsonl"
        self.stop_file = self.runtime_dir / "training_stop.flag"
        self.launch_log_file = self.runtime_dir / "training_launcher.log"

        self._progress = 0
        self._status = "Idle"
        self._debug_lines = []
        self._log_lines = []
        self._running = False
        self._had_error = False
        self._was_aborted = False
        self._copied_best = False
        self._completion_counter = 0
        self._run_dir = None
        self._pid = None
        self._events_pos = 0
        self._last_updated_at = 0.0

        self._rehydrate_from_disk()

    def start(self, drive: str, config: TrainingConfig) -> tuple[bool, str]:
        with self._lock:
            self._refresh_from_disk_locked()
            if self._running:
                return False, "Training is already running."

            self._reset_state_locked(drive)

            if self.events_file.exists():
                self.events_file.unlink()
            self.stop_file.unlink(missing_ok=True)

            cmd = self._build_launch_command(drive, config)
            launch_log = self.launch_log_file.open("a", encoding="utf-8")
            kwargs = {
                "cwd": str(self.base_dir),
                "stdin": subprocess.DEVNULL,
                "stdout": launch_log,
                "stderr": launch_log,
            }

            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                kwargs["creationflags"] = (
                    subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                    | subprocess.CREATE_NO_WINDOW
                )  # type: ignore[attr-defined]
                kwargs["startupinfo"] = startupinfo
                kwargs["close_fds"] = True
            else:
                kwargs["start_new_session"] = True

            try:
                proc = subprocess.Popen(cmd, **kwargs)
            finally:
                launch_log.close()
            self._pid = proc.pid
            self._running = True
            self._status = "Launching training..."
            self._write_boot_state_locked()
            return True, "Training started."

    def request_stop(self) -> None:
        with self._lock:
            self._refresh_from_disk_locked()
            if not self._running:
                return
            self.stop_file.touch(exist_ok=True)
            self._status = "Stopping training (this may take a while)..."
            self._append_debug_locked("Debug: abort requested from UI.")

    def force_kill(self) -> bool:
        with self._lock:
            self._refresh_from_disk_locked()
            if not self._running or not self._pid:
                return False

            self._recover_partial_best_locked()
            self._append_log_locked("Force-stopping training subprocess.")
            self._append_debug_locked("Debug: terminating training subprocess.")

            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(self._pid), "/T", "/F"],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    os.kill(self._pid, signal.SIGKILL)
            except Exception:
                return False
            return True

    def snapshot(self) -> dict:
        with self._lock:
            self._refresh_from_disk_locked()
            return {
                "running": self._running,
                "progress": self._progress,
                "status": self._status,
                "debug_lines": list(self._debug_lines),
                "log_lines": list(self._log_lines),
                "had_error": self._had_error,
                "was_aborted": self._was_aborted,
                "copied_best": self._copied_best,
                "completion_counter": self._completion_counter,
                "run_dir": str(self._run_dir) if self._run_dir else "",
            }

    def _build_launch_command(self, drive: str, config: TrainingConfig) -> list[str]:
        config_json = json.dumps(asdict(config))
        bg_python = self._background_python_executable()

        if getattr(sys, "frozen", False):
            return [
                bg_python,
                "--training-subprocess",
                "--drive",
                drive,
                "--stop-file",
                str(self.stop_file),
                "--config-json",
                config_json,
                "--state-file",
                str(self.state_file),
                "--events-file",
                str(self.events_file),
            ]

        return [
            bg_python,
            str(self.base_dir / "training_subprocess.py"),
            "--drive",
            drive,
            "--stop-file",
            str(self.stop_file),
            "--config-json",
            config_json,
            "--state-file",
            str(self.state_file),
            "--events-file",
            str(self.events_file),
        ]

    def _background_python_executable(self) -> str:
        if getattr(sys, "frozen", False):
            return sys.executable

        exe = Path(sys.executable)
        if exe.name.lower() == "python.exe":
            pythonw = exe.with_name("pythonw.exe")
            if pythonw.exists():
                return str(pythonw)
        return str(exe)

    def _rehydrate_from_disk(self):
        with self._lock:
            self._refresh_from_disk_locked()

    def _refresh_from_disk_locked(self):
        self._load_events_locked()
        self._load_state_locked()
        self._resolve_stale_running_locked()

    def _load_state_locked(self):
        if not self.state_file.exists():
            return
        try:
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return

        updated_at = float(state.get("updated_at", 0.0) or 0.0)
        if updated_at < self._last_updated_at:
            return

        self._last_updated_at = updated_at
        self._running = bool(state.get("running", self._running))
        self._progress = int(state.get("progress", self._progress))
        self._status = str(state.get("status", self._status))
        self._had_error = bool(state.get("had_error", self._had_error))
        self._was_aborted = bool(state.get("was_aborted", self._was_aborted))
        self._copied_best = bool(state.get("copied_best", self._copied_best))
        self._completion_counter = int(state.get("completion_counter", self._completion_counter))
        run_dir = str(state.get("run_dir", "")).strip()
        self._run_dir = Path(run_dir) if run_dir else None
        pid = state.get("pid", self._pid)
        self._pid = int(pid) if pid else None

    def _load_events_locked(self):
        if not self.events_file.exists():
            return
        try:
            with self.events_file.open("r", encoding="utf-8") as f:
                f.seek(self._events_pos)
                for raw in f:
                    line = raw.strip()
                    if not line:
                        continue
                    self._handle_event_locked(line)
                self._events_pos = f.tell()
        except Exception:
            return

    def _handle_event_locked(self, line: str):
        try:
            event = json.loads(line)
        except Exception:
            self._append_log_locked(line)
            return

        event_type = event.get("type", "")
        if event_type == "debug":
            self._append_debug_locked(str(event.get("text", "")))
        elif event_type == "log":
            self._append_log_locked(str(event.get("text", "")))
        elif event_type == "run_dir":
            path = str(event.get("path", "")).strip()
            self._run_dir = Path(path) if path else None

    def _resolve_stale_running_locked(self):
        if not self._running or not self._pid:
            return
        if self._is_pid_alive(self._pid):
            return

        self._running = False
        if self._status not in ("Training complete", "Training failed", "Training aborted"):
            self._had_error = True
            self._status = "Training failed"
            self._append_log_locked("Training process exited unexpectedly.")
            self._append_log_locked(f"See launcher log: {self.launch_log_file}")
            self._completion_counter += 1

    def _is_pid_alive(self, pid: int) -> bool:
        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                output = (result.stdout or "").strip()
                if not output:
                    return False
                if "No tasks are running" in output:
                    return False
                return str(pid) in output

            os.kill(pid, 0)
            return True
        except Exception:
            return False

    def _reset_state_locked(self, drive: str):
        self._progress = 0
        self._status = "Launching training..."
        self._debug_lines = []
        self._log_lines = [f"Launching training from folder: {drive}"]
        self._running = False
        self._had_error = False
        self._was_aborted = False
        self._copied_best = False
        self._run_dir = None
        self._pid = None
        self._events_pos = 0
        self._last_updated_at = 0.0

    def _write_boot_state_locked(self):
        state = {
            "running": self._running,
            "progress": self._progress,
            "status": self._status,
            "had_error": self._had_error,
            "was_aborted": self._was_aborted,
            "copied_best": self._copied_best,
            "completion_counter": self._completion_counter,
            "run_dir": str(self._run_dir) if self._run_dir else "",
            "pid": self._pid,
            "updated_at": time.time(),
        }
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _append_log_locked(self, text: str):
        if not text:
            return
        self._log_lines.append(text)
        if len(self._log_lines) > 2000:
            self._log_lines = self._log_lines[-2000:]

    def _append_debug_locked(self, text: str):
        if not text:
            return
        self._debug_lines.append(text)
        if len(self._debug_lines) > 2000:
            self._debug_lines = self._debug_lines[-2000:]

    def _recover_partial_best_locked(self) -> bool:
        if self._run_dir is None:
            return False
        try:
            source = self._run_dir / "weights" / "best.pt"
            if not source.exists():
                return False
            destination = self.base_dir / "Models" / "best.pt"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            self._copied_best = True
            self._append_log_locked("Recovered latest best.pt before force-stop.")
            return True
        except Exception:
            return False


_SESSION = TrainingSession()


def get_training_session() -> TrainingSession:
    return _SESSION
