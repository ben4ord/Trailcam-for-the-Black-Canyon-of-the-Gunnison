from pathlib import Path
import shutil


class TrainingManager:
    def __init__(self, root_drive):
        self.root_drive = Path(root_drive)
        # Centralized training set location beside this module.
        self.train_root = Path(__file__).resolve().parent / "train"
        self.images_dir = self.train_root / "images"
        self.labels_dir = self.train_root / "labels"

        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)

    def _camera_and_check_name(self, source_path: Path) -> tuple[str, str]:
        """
        Expected layout: camera -> check folder -> (optional subfolders) -> image.
        Finds the nearest ancestor containing 'check' and uses its parent as camera.
        """
        check_folder = None
        for ancestor in source_path.parents:
            if "check" in ancestor.name.lower():
                check_folder = ancestor
                break

        if check_folder is not None and check_folder.parent != check_folder:
            camera_name = check_folder.parent.name
            check_name = check_folder.name
            return camera_name, check_name

        # Fallback if no check folder is found.
        if source_path.parent.parent != source_path.parent:
            return source_path.parent.parent.name, source_path.parent.name
        return source_path.parent.name, source_path.parent.name

    def generate_train_name(self, source_path):
        source_path = Path(source_path)

        camera_name, check_name = self._camera_and_check_name(source_path)
        base_name = source_path.stem
        new_name = f"{camera_name}_{check_name}_{base_name}{source_path.suffix}"
        return self.images_dir / new_name

    def verify_image(self, source_path, label_lines=None):
        destination = self.generate_train_name(source_path)
        shutil.copy2(source_path, destination)

        label_path = self.labels_dir / f"{destination.stem}.txt"
        lines = label_lines or []
        label_content = "\n".join(lines)
        if label_content:
            label_content += "\n"
        label_path.write_text(label_content, encoding="utf-8")

        return destination, label_path

    def is_verified(self, source_path):
        source_path = Path(source_path)

        camera_name, check_name = self._camera_and_check_name(source_path)
        base_name = source_path.stem
        stem = f"{camera_name}_{check_name}_{base_name}"
        image_name = f"{stem}{source_path.suffix}"
        image_path = self.images_dir / image_name
        label_path = self.labels_dir / f"{stem}.txt"
        return image_path.exists() and label_path.exists()
