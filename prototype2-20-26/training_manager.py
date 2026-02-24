from pathlib import Path
import shutil
import re

class TrainingManager:
    def __init__(self, root_drive):
        self.root_drive = Path(root_drive)
        self.train_dir = self.root_drive / "train"
        self.train_dir.mkdir(exist_ok=True)

    def generate_train_name(self, source_path):
        source_path = Path(source_path)

        camera_name = source_path.parent.name
        base_name = source_path.stem

        pattern = re.compile(
            rf"{re.escape(camera_name)}_{re.escape(base_name)}_(\d+)"
        )

        max_index = 0
        for file in self.train_dir.iterdir():
            match = pattern.match(file.stem)
            if match:
                max_index = max(max_index, int(match.group(1)))

        new_index = max_index + 1
        new_name = f"{camera_name}_{base_name}_{new_index}{source_path.suffix}"

        return self.train_dir / new_name

    def verify_image(self, source_path):
        destination = self.generate_train_name(source_path)
        shutil.copy2(source_path, destination)
        return destination
    
    def is_verified(self, source_path):
        source_path = Path(source_path)

        camera_name = source_path.parent.name
        base_name = source_path.stem

        pattern = re.compile(
            rf"{re.escape(camera_name)}_{re.escape(base_name)}_(\d+)"
        )

        for file in self.train_dir.iterdir():
            if pattern.match(file.stem):
                return True

        return False