from pathlib import Path

from app_paths import classes_file, data_yaml_file, inactive_labels_file


class LabelStore:
    def __init__(self, classes_path: Path | None = None, data_yaml_path: Path | None = None):
        self.classes_path = Path(classes_path) if classes_path else classes_file()
        self.data_yaml_path = Path(data_yaml_path) if data_yaml_path else data_yaml_file()
        self.inactive_labels_path = inactive_labels_file()

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

    def read_inactive_labels(self) -> list[str]:
        if not self.inactive_labels_path.exists():
            return []
        return [
            line.strip()
            for line in self.inactive_labels_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def write_inactive_labels(self, labels: list[str]) -> None:
        content = "\n".join(labels)
        self.inactive_labels_path.write_text(content, encoding="utf-8")

    def read_active_labels(self) -> list[str]:
        labels = self.read_labels()
        inactive = set(self.read_inactive_labels())
        active = [label for label in labels if label not in inactive]
        return active

    def add_label(self, label: str) -> None:
        labels = self.read_labels()

        # grab the inactive labels so we can check if the label existed in the past
        inactive = self.read_inactive_labels()
        inactive_set = set(inactive)

        # if the label is in the inactive set, remove it from the set and return, we don't want to write it again
        if label in labels:
            if label in inactive_set:
                inactive_set.remove(label)
                self.write_inactive_labels(self.inactive_in_class_order(labels, inactive_set))
            return


        labels.append(label)
        self.write_labels(labels)
        self.write_yaml_names(labels)

    def update_label(self, old_label: str, new_label: str) -> None:
        labels = self.read_labels()
        labels = [new_label if value == old_label else value for value in labels]
        self.write_labels(labels)
        self.rename_inactive_label(old_label, new_label, labels)
        self.write_yaml_names(labels)

    def remove_label(self, label: str) -> None:
        labels = self.read_labels()
        if label not in labels:
            return

        inactive = set(self.read_inactive_labels())
        if label in inactive:
            return
        inactive.add(label)
        self.write_inactive_labels(self.inactive_in_class_order(labels, inactive))

    def rename_inactive_label(self, old_label: str, new_label: str, labels: list[str]) -> None:
        inactive = set(self.read_inactive_labels())
        if old_label not in inactive:
            return
        inactive.remove(old_label)
        inactive.add(new_label)
        self.write_inactive_labels(self.inactive_in_class_order(labels, inactive))

    @staticmethod
    def inactive_in_class_order(labels: list[str], inactive: set[str]) -> list[str]:
        return [label for label in labels if label in inactive]

    def write_yaml_names(self, names: list[str]) -> None:
        if not self.data_yaml_path.exists():
            return

        lines = self.data_yaml_path.read_text(encoding="utf-8").splitlines() # read in the individual lines from the yaml file
        name_lines = [
            (idx, line)
            for idx, line in enumerate(lines)
            if line.startswith("  ") and ": " in line
        ]
        if not name_lines:
            return

        new_name_lines = [f"  {idx}: {name}" for idx, name in enumerate(names)]

        # track the first and last index of the names, then we can append to the end
        first_idx = name_lines[0][0]
        last_idx = name_lines[-1][0]
        lines[first_idx:last_idx + 1] = new_name_lines

        # find the nc (number of classes) line and modify the count based on the new number of classes
        for idx, line in enumerate(lines):
            if line.startswith("nc: "):
                lines[idx] = f"nc: {len(names)}"
                break

        self.data_yaml_path.write_text("\n".join(lines), encoding="utf-8")