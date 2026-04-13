"""Quick utility to report class counts from verified YOLO label files.

Usage:
    python count_verified_labels.py
    python count_verified_labels.py --labels-dir verified_images/dataset/labels
    python count_verified_labels.py --include-zero
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path


def read_classes(classes_path: Path) -> list[str]:
    if not classes_path.exists():
        return []
    return [
        line.strip()
        for line in classes_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def scan_label_counts(labels_dir: Path) -> tuple[Counter[int], Counter[int], int, int]:
    """Return (object_counts, image_counts, files_scanned, malformed_lines)."""
    object_counts: Counter[int] = Counter()
    image_counts: Counter[int] = Counter()
    files_scanned = 0
    malformed_lines = 0

    for label_file in labels_dir.glob("*.txt"):
        if not label_file.is_file():
            continue

        files_scanned += 1
        seen_in_file: set[int] = set()

        for raw in label_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line:
                continue

            class_token = line.split(maxsplit=1)[0]

            try:
                class_id = int(class_token)
            except ValueError:
                malformed_lines += 1
                continue

            object_counts[class_id] += 1
            seen_in_file.add(class_id)

        for class_id in seen_in_file:
            image_counts[class_id] += 1

    return object_counts, image_counts, files_scanned, malformed_lines


def class_name_for(class_id: int, class_names: list[str]) -> str:
    if 0 <= class_id < len(class_names):
        return class_names[class_id]
    return f"class_{class_id}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Report counts from verified label files.")
    parser.add_argument(
        "--labels-dir",
        type=Path,
        default=Path.cwd() / "verified_images" / "dataset" / "labels",
        help="Directory containing YOLO .txt label files.",
    )
    parser.add_argument(
        "--classes",
        type=Path,
        default=Path.cwd() / "classes.txt",
        help="Path to classes.txt (used for readable class names).",
    )
    parser.add_argument(
        "--include-zero",
        action="store_true",
        help="Also show classes from classes.txt with zero counts.",
    )
    args = parser.parse_args()

    labels_dir = args.labels_dir
    classes_path = args.classes

    if not labels_dir.exists():
        raise SystemExit(f"Labels directory not found: {labels_dir}")

    class_names = read_classes(classes_path)
    object_counts, image_counts, files_scanned, malformed_lines = scan_label_counts(labels_dir)

    class_ids = set(object_counts) | set(image_counts)
    if args.include_zero:
        class_ids.update(range(len(class_names)))

    class_ids = sorted(class_ids)

    print(f"Labels dir: {labels_dir}")
    print(f"Classes file: {classes_path} ({'found' if classes_path.exists() else 'not found'})")
    print(f"Label files scanned: {files_scanned}")
    print(f"Malformed lines skipped: {malformed_lines}")
    print()

    if not class_ids:
        print("No class data found.")
        return

    id_w = max(2, max(len(str(cid)) for cid in class_ids))
    name_w = max(10, max(len(class_name_for(cid, class_names)) for cid in class_ids))
    obj_w = max(7, max(len(str(object_counts.get(cid, 0))) for cid in class_ids))
    img_w = max(8, max(len(str(image_counts.get(cid, 0))) for cid in class_ids))

    header = (
        f"{'id':>{id_w}}  "
        f"{'class_name':<{name_w}}  "
        f"{'objects':>{obj_w}}  "
        f"{'images':>{img_w}}"
    )
    print(header)
    print("-" * len(header))

    for class_id in class_ids:
        class_name = class_name_for(class_id, class_names)
        print(
            f"{class_id:>{id_w}}  "
            f"{class_name:<{name_w}}  "
            f"{object_counts.get(class_id, 0):>{obj_w}}  "
            f"{image_counts.get(class_id, 0):>{img_w}}"
        )


if __name__ == "__main__":
    main()
