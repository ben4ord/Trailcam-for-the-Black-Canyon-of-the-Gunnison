from pathlib import Path

from app_paths import classes_file, data_yaml_file


class LabelStore:
    def __init__(self, classes_path: Path | None = None, data_yaml_path: Path | None = None):
        self.classes_path = Path(classes_path) if classes_path else classes_file()
        self.data_yaml_path = Path(data_yaml_path) if data_yaml_path else data_yaml_file()

    def read_labels(self) -> list[str]:
        if not self.classes_path.exists():
            return []
        return [
            line.strip()
            for line in self.classes_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def write_labels(self, labels: list[str]) -> None:
        content = "\n".join(labels)
        self.classes_path.write_text(content, encoding="utf-8")

    def add_label(self, label: str) -> None:
        labels = self.read_labels()

        replaced = False
        for index, check_label in enumerate(labels):
            if check_label == "$DUMMY_ANIMAL":
                labels[index] = label
                replaced = True
                break

        if not replaced:
            labels.append(label)

        self.write_labels(labels)
        self.write_yaml_names(labels)

    def update_label(self, old_label: str, new_label: str) -> None:
        labels = self.read_labels()
        labels = [new_label if value == old_label else value for value in labels]
        self.write_labels(labels)
        self.write_yaml_names(labels)

    def remove_label(self, label: str) -> None:
        labels = self.read_labels()
        for index, value in enumerate(labels):
            if value == label:
                labels[index] = "$DUMMY_ANIMAL"
                break
        self.write_labels(labels)
        self.write_yaml_names(labels)

    def write_yaml_names(self, names: list[str]) -> None:
        if not self.data_yaml_path.exists():
            return

        lines = self.data_yaml_path.read_text(encoding="utf-8").splitlines()

        # find the nc (number of classes) line and modify the count based on the new number of classes
        for idx, line in enumerate(lines):
            if line.startswith("nc: "):
                lines[idx] = f"nc: {len(names)}"
                break

        names_index = None
        for idx, line in enumerate(lines):
            if line.strip() == "names:":
                names_index = idx
                break
        if names_index is None:
            return

        block_start = names_index + 1
        block_end = block_start
        while block_end < len(lines) and lines[block_end].startswith("  "):
            block_end += 1

        name_lines = [f"  {idx}: {name}" for idx, name in enumerate(names)]
        lines = lines[:block_start] + name_lines + lines[block_end:]

        self.data_yaml_path.write_text("\n".join(lines), encoding="utf-8")
