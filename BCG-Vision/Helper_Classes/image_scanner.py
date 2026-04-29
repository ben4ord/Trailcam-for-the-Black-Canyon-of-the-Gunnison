"""Background thread that walks a directory tree and emits image paths in batches.

Using a QThread keeps the UI responsive during the scan so the viewer can
display the first images almost immediately, even over slow drives.
"""

import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'}
BATCH_SIZE = 2000


class ImageScanner(QThread):
    """Walks *root_path* in a background thread and emits image paths in batches."""

    batch_ready = Signal(list)   # list[str] — next batch of absolute paths
    scan_done = Signal(int)      # total images found

    def __init__(self, root_path: str, parent=None):
        super().__init__(parent)
        self.root_path = root_path
        self._abort = False

    def stop(self):
        self._abort = True

    def run(self):
        batch: list[str] = []
        total = 0

        for root, _dirs, files in os.walk(self.root_path):
            if self._abort:
                break
            for f in files:
                if self._abort:
                    break
                if Path(f).suffix.lower() in IMAGE_EXTENSIONS:
                    batch.append(os.path.join(root, f))
                    total += 1
                    if len(batch) >= BATCH_SIZE:
                        self.batch_ready.emit(batch)
                        batch = []

        if batch and not self._abort:
            self.batch_ready.emit(batch)

        self.scan_done.emit(total)
