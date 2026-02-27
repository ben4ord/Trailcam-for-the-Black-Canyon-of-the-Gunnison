from pathlib import Path
import shutil
import re


class TrainingManager:
    def __init__(self, root_drive):
        self.root_drive = Path(root_drive)

        # Centralized training set location beside this module.
        self.train_root = Path(__file__).resolve().parent / "verified_images/dataset"
        self.images_dir = self.train_root / "images"
        self.labels_dir = self.train_root / "labels"

        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)

        self._verified_cache = set()
        self._refresh_verified_cache()

    # ============================
    # UTILITIES
    # ============================

    def _sanitize(self, name: str) -> str:
        return re.sub(r'[<>:"/\\|?*]', '', name).replace(" ", "_")

    def _is_camera_folder(self, name: str) -> bool:
        return "-" in name and len(name) <= 5
    
    def _refresh_verified_cache(self):
        self._verified_cache = {
            p.name for p in self.images_dir.glob("*")
        }
    
    def _build_cache(self):
        self._verified_cache.clear()

        if not self.images_dir.exists():
            return

        for img in self.images_dir.iterdir():
            if img.is_file():
                self._verified_cache.add(img.name)

    # ============================
    # CORE PATH PARSING
    # ============================

    def _build_full_path_name(self, source_path: Path) -> str:
        source_path = Path(source_path).resolve()

        parts = []

        for ancestor in source_path.parents:
            parts.append(ancestor.name)

            if self._is_camera_folder(ancestor.name):
                break

        parts.reverse()

        parts = [self._sanitize(p) for p in parts if p]

        return "_".join(parts + [source_path.stem]) + source_path.suffix

    # ============================
    # PUBLIC API
    # ============================

    def generate_train_name(self, source_path):
        source_path = Path(source_path)

        new_filename = self._build_full_path_name(source_path)

        return self.images_dir / new_filename

    def verify_image(self, source_path, label_lines=None):
        source_path = Path(source_path)

        destination = self.generate_train_name(source_path)

        shutil.copy2(source_path, destination)

        self._verified_cache.add(destination.name)

        label_path = self.labels_dir / f"{destination.stem}.txt"

        lines = label_lines or []
        label_content = "\n".join(lines)

        if label_content:
            label_content += "\n"

        label_path.write_text(label_content, encoding="utf-8")

        self._refresh_verified_cache()

        return destination, label_path

    
    def is_verified_cached(self, source_path):
        source_path = Path(source_path)
        filename = self._build_full_path_name(source_path)

        image_path = self.images_dir / filename
        label_path = self.labels_dir / f"{Path(filename).stem}.txt"

        return filename in self._verified_cache

    def unverify_image(self, source_path):
        source_path = Path(source_path)

        training_image_path = self.generate_train_name(source_path)

        # Delete image file
        if training_image_path.exists():
            training_image_path.unlink()
            print(f"Deleted image: {training_image_path}")

        # Delete label file
        label_path = self.labels_dir / f"{training_image_path.stem}.txt"

        if label_path.exists():
            label_path.unlink()
            print(f"Deleted label: {label_path}")

        self._verified_cache.discard(training_image_path.name)

        self._refresh_verified_cache()
