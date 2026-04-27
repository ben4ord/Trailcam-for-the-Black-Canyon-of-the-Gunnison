from pathlib import Path
import sys


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def verified_images_base_dir() -> Path:
    if getattr(sys, "frozen", False) and sys.platform == "darwin":
        exe_path = Path(sys.executable).resolve()
        app_index = next(
            (idx for idx, part in enumerate(exe_path.parts) if part.endswith(".app")),
            -1,
        )
        if app_index >= 0:
            path = Path(*exe_path.parts[: app_index + 1]).parent
        else:
            path = exe_path.parent
    else:
        path = app_base_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def models_dir() -> Path:
    return app_base_dir() / "Models"


def verified_images_dir() -> Path:
    path = verified_images_base_dir() / "verified_images"
    path.mkdir(parents=True, exist_ok=True)
    return path


def verified_dataset_dir() -> Path:
    path = verified_images_dir() / "dataset"
    path.mkdir(parents=True, exist_ok=True)
    return path


def verified_filtered_dataset_dir() -> Path:
    return verified_images_dir() / "dataset_filtered"


def runtime_dir() -> Path:
    path = app_base_dir() / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def classes_file() -> Path:
    return app_base_dir() / "classes.txt"


def data_yaml_file() -> Path:
    return app_base_dir() / "data.yaml"


def inactive_labels_file() -> Path:
    return app_base_dir() / "inactive_labels.txt"
