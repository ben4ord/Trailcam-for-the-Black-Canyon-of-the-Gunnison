"""Utilities for maintaining the verified training dataset on disk.

This module maps original camera image paths to deterministic dataset filenames
and keeps paired YOLO label files in sync.
"""

from pathlib import Path
import shutil
import re
import csv
import os
from Helper_Classes.app_paths import verified_images_base_dir, verified_dataset_dir

base_path = verified_images_base_dir()

class TrainingManager:
    def __init__(self, root_drive):
        self.root_drive = Path(root_drive)

        # Centralized training set location beside this module.
        # This is for the executable to work properly

        self.train_root = verified_dataset_dir()

        self.images_dir = self.train_root / "images"
        self.labels_dir = self.train_root / "labels"

        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)
        self.cache_csv_path = ""
        self.verified_cache: set[str] = set()
        self.legacy_name_cache: set[str] = set()
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
        csv_path = base_path / "verified_image_cache.csv"

        if csv_path.exists():
            self.verified_cache = set()
            self.legacy_name_cache = set()
            with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                if reader.fieldnames and "image_path" in reader.fieldnames:
                    for row in reader:
                        raw_path = (row.get("image_path") or "").strip()
                        if not raw_path:
                            continue
                        normalized_path = self.normalize_cache_path(raw_path)
                        self.verified_cache.add(normalized_path)
                        self.legacy_name_cache.add(Path(normalized_path).name)
                else:
                    self.verified_cache = set()
                    self.legacy_name_cache = set()
        else:
            self.verified_cache = set()
            self.legacy_name_cache = set()

        self.cache_csv_path = csv_path

    def normalize_cache_path(self, path_like) -> str:
        """Normalize cache keys without hitting the filesystem."""
        return os.path.normcase(os.path.abspath(os.fspath(path_like)))

    def cache_key_for_source(self, source_path) -> str:
        """Normalize a source image path to the dataset image path stored in the CSV."""
        return self.normalize_cache_path(self.generate_train_name(source_path))


    # ============================
    # CORE PATH PARSING
    # ============================

    def build_full_path_name(self, source_path: Path) -> str:
        """Build deterministic dataset filename from source ancestry + stem."""
        source_path = Path(source_path)

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
        source_path = Path(source_path).resolve()

        # Already a verified copy — return as-is so the path math stays correct.
        try:
            source_path.relative_to(self.images_dir.resolve())
            return source_path
        except ValueError:
            pass

        new_filename = self.build_full_path_name(source_path)
        return self.images_dir / new_filename

    def verify_image(self, source_path, label_lines=None):
        """Copy source image into dataset and write/update its YOLO label file."""
        source_path = Path(source_path).resolve()

        destination = self.generate_train_name(source_path)

        shutil.copy2(source_path, destination)
        # Update in-memory cache
        cache_key = self.normalize_cache_path(destination)
        self.verified_cache.add(cache_key)
        self.legacy_name_cache.add(destination.name)

        # Persist to CSV
        self.write_cache()

        label_path = self.labels_dir / f"{destination.stem}.txt"

        lines = label_lines or []
        label_content = "\n".join(lines)
        # Keep YOLO label files newline-terminated when non-empty.
        if label_content:
            label_content += "\n"

        label_path.write_text(label_content, encoding="utf-8")

        return destination, label_path

    
    def is_verified_cached(self, source_path):
        """Fast in-memory check: does this source image already have dataset copy."""
        cache_key = self.cache_key_for_source(source_path)
        return cache_key in self.verified_cache or Path(cache_key).name in self.legacy_name_cache


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
        # Remove from cache
        cache_key = self.normalize_cache_path(training_image_path)
        self.verified_cache.discard(cache_key)
        self.legacy_name_cache.discard(training_image_path.name)

        self.write_cache()

    def write_cache(self):
        with self.cache_csv_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["image_path"])
            for image_path in sorted(self.verified_cache):
                writer.writerow([image_path])
