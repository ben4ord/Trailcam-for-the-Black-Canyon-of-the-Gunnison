from pathlib import Path
import sys


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def classes_file() -> Path:
    return app_base_dir() / "classes.txt"


def data_yaml_file() -> Path:
    return app_base_dir() / "data.yaml"
