"""Utilities for maintaining the verified training dataset on disk.

This module maps original camera image paths to deterministic dataset filenames
and keeps paired YOLO label files in sync.
"""

from pathlib import Path
import shutil
import re

class TrainingManager:
    def __init__(self, root_drive):
        self.root_drive = Path(root_drive)

        # Centralized training set location beside this module.
        # This is for the executable to work properly
        base_dir = Path.cwd()

        self.train_root = base_dir / "verified_images" / "dataset"

        self.images_dir = self.train_root / "images"
        self.labels_dir = self.train_root / "labels"

        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)

        self.verified_cache = set()
        self.refresh_verified_cache()

    # ============================
    # UTILITIES
    # ============================

    def sanitize(self, name: str) -> str:
        """Remove path-unsafe characters and normalize spaces."""
        return re.sub(r'[<>:"/\\|?*]', '', name).replace(" ", "_")

    def is_camera_folder(self, name: str) -> bool:
        """Heuristic used to stop ancestor traversal at camera folder boundary."""
        return "-" in name and len(name) <= 5
    
    def refresh_verified_cache(self):
        """Rebuild fast lookup set of all dataset image filenames."""
        self.verified_cache = {p.name for p in self.images_dir.glob("*") if p.is_file()}

    # ============================
    # CORE PATH PARSING
    # ============================

    def build_full_path_name(self, source_path: Path) -> str:
        """Build deterministic dataset filename from source ancestry + stem."""
        source_path = Path(source_path).resolve()

        parts = []

        for ancestor in source_path.parents:
            parts.append(ancestor.name)

            # Once camera folder is reached, do not include higher-level folders.
            if self.is_camera_folder(ancestor.name):
                break

        parts.reverse()

        parts = [self.sanitize(p) for p in parts if p]

        return "_".join(parts + [source_path.stem]) + source_path.suffix

    # ============================
    # PUBLIC API
    # ============================

    def generate_train_name(self, source_path):
        """Return destination path under dataset/images for given source image."""
        source_path = Path(source_path)

        new_filename = self.build_full_path_name(source_path)

        return self.images_dir / new_filename

    def verify_image(self, source_path, label_lines=None):
        """Copy source image into dataset and write/update its YOLO label file."""
        source_path = Path(source_path)

        destination = self.generate_train_name(source_path)

        shutil.copy2(source_path, destination)

        self.verified_cache.add(destination.name)

        label_path = self.labels_dir / f"{destination.stem}.txt"

        lines = label_lines or []
        label_content = "\n".join(lines)

        # Keep YOLO label files newline-terminated when non-empty.
        if label_content:
            label_content += "\n"

        label_path.write_text(label_content, encoding="utf-8")

        self.refresh_verified_cache()

        return destination, label_path

    
    def is_verified_cached(self, source_path):
        """Fast in-memory check: does this source image already have dataset copy."""
        source_path = Path(source_path)
        filename = self.build_full_path_name(source_path)

        return filename in self.verified_cache

    def unverify_image(self, source_path):
        """Remove dataset image and label pair for a previously verified source."""
        source_path = Path(source_path)

        training_image_path = self.generate_train_name(source_path)

        # Delete image file
        if training_image_path.exists():
            training_image_path.unlink()

        # Delete label file
        label_path = self.labels_dir / f"{training_image_path.stem}.txt"

        if label_path.exists():
            label_path.unlink()

        self.verified_cache.discard(training_image_path.name)

        self.refresh_verified_cache()
