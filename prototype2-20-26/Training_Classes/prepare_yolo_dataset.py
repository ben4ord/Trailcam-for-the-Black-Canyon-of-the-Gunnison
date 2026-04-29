"""Prepare a filtered YOLO dataset that excludes inactive class IDs.

This keeps the output head size fixed by preserving the full classes list
while dropping inactive labels from the copied label files.
"""

from __future__ import annotations

import argparse
import os
import shutil
import time
from pathlib import Path


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def resolve_inactive_ids(inactive_lines: list[str], classes: list[str]) -> set[int]:
    inactive_ids: set[int] = set()
    for token in inactive_lines:
        try:
            class_id = int(token)
            if 0 <= class_id < len(classes):
                inactive_ids.add(class_id)
            continue
        except ValueError:
            pass

        if token in classes:
            inactive_ids.add(classes.index(token))
    return inactive_ids


def format_path(path: Path) -> str:
    try:
        rel = path.relative_to(Path.cwd())
        return rel.as_posix()
    except ValueError:
        return path.as_posix()


def link_or_copy(src: Path, dst: Path, force_copy: bool) -> None:
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if force_copy:
        shutil.copy2(src, dst)
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def write_filtered_yaml(base_yaml: Path, output_yaml: Path, output_root: Path, classes: list[str]) -> None:
    if base_yaml.exists():
        lines = base_yaml.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    output_path = format_path(output_root)

    replaced_path = False
    for idx, line in enumerate(lines):
        if line.startswith("path:"):
            lines[idx] = f"path: {output_path}"
            replaced_path = True
            break
    if not replaced_path:
        lines.insert(0, f"path: {output_path}")

    replaced_nc = False
    for idx, line in enumerate(lines):
        if line.startswith("nc:"):
            lines[idx] = f"nc: {len(classes)}"
            replaced_nc = True
            break
    if not replaced_nc:
        lines.append(f"nc: {len(classes)}")

    names_index = None
    for idx, line in enumerate(lines):
        if line.strip() == "names:":
            names_index = idx
            break

    name_lines = [f"  {idx}: {name}" for idx, name in enumerate(classes)]

    if names_index is None:
        lines.append("")
        lines.append("names:")
        lines.extend(name_lines)
    else:
        block_start = names_index + 1
        block_end = block_start
        while block_end < len(lines) and lines[block_end].startswith("  "):
            block_end += 1
        lines = lines[:block_start] + name_lines + lines[block_end:]

    output_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a filtered YOLO dataset.")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.cwd() / "verified_images" / "dataset",
        help="Source dataset root containing images/ and labels/.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.cwd() / "verified_images" / "dataset_filtered",
        help="Output dataset root for filtered labels.",
    )
    parser.add_argument(
        "--classes",
        type=Path,
        default=Path.cwd() / "classes.txt",
        help="Path to classes.txt (full class list).",
    )
    parser.add_argument(
        "--inactive",
        type=Path,
        default=Path.cwd() / "inactive_labels.txt",
        help="Path to inactive_labels.txt (names or IDs).",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path.cwd() / "data.yaml",
        help="Base data.yaml to copy settings from.",
    )
    parser.add_argument(
        "--output-yaml",
        type=Path,
        default=None,
        help="Optional output data.yaml path (default: <output>/data.yaml).",
    )
    parser.add_argument(
        "--copy-images",
        action="store_true",
        help="Copy images instead of using hardlinks when possible.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=200,
        help="Print progress every N files (0 disables).",
    )
    args = parser.parse_args()

    source_root = args.source.resolve()
    output_root = args.output.resolve()
    images_dir = source_root / "images"
    labels_dir = source_root / "labels"

    if not images_dir.exists():
        raise SystemExit(f"Images dir not found: {images_dir}")
    if not labels_dir.exists():
        raise SystemExit(f"Labels dir not found: {labels_dir}")

    classes = read_lines(args.classes)
    inactive_lines = read_lines(args.inactive)
    inactive_ids = resolve_inactive_ids(inactive_lines, classes)

    output_images = output_root / "images"
    output_labels = output_root / "labels"
    output_images.mkdir(parents=True, exist_ok=True)
    output_labels.mkdir(parents=True, exist_ok=True)

    label_files = [p for p in labels_dir.rglob("*.txt") if p.is_file()]
    total_labels = len(label_files)
    start_time = time.time()

    def maybe_print_progress(kind: str, current: int, total: int) -> None:
        if args.progress_every <= 0:
            return
        if current == total or current % args.progress_every == 0:
            elapsed = max(0.001, time.time() - start_time)
            rate = current / elapsed if current else 0.0
            eta = (total - current) / rate if rate > 0 else 0.0
            print(f"{kind}: {current}/{total} | {rate:.1f} files/s | ETA {eta:.1f}s")

    image_candidates: list[Path] = []
    image_exts = [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"]

    for idx, label_path in enumerate(label_files, start=1):
        if not label_path.is_file():
            continue
        rel = label_path.relative_to(labels_dir)
        dest = output_labels / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        kept: list[str] = []
        for raw in label_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line:
                continue
            parts = line.split()
            try:
                class_id = int(parts[0])
            except ValueError:
                continue
            if class_id in inactive_ids:
                continue
            kept.append(line)

        if kept:
            dest.write_text("\n".join(kept) + "\n", encoding="utf-8")
            image_dir = images_dir / rel.parent
            image_path = None
            for ext in image_exts:
                candidate = image_dir / f"{label_path.stem}{ext}"
                if candidate.exists():
                    image_path = candidate
                    break
            if image_path is None:
                matches = list(image_dir.glob(f"{label_path.stem}.*"))
                if matches:
                    image_path = matches[0]
            if image_path is not None:
                image_candidates.append(image_path)
        maybe_print_progress("Labels", idx, total_labels)

    unique_images = list(dict.fromkeys(image_candidates))
    total_images = len(unique_images)
    for idx, image_path in enumerate(unique_images, start=1):
        rel = image_path.relative_to(images_dir)
        dest = output_images / rel
        link_or_copy(image_path, dest, args.copy_images)
        maybe_print_progress("Images", idx, total_images)

    output_yaml = args.output_yaml or (output_root / "data.yaml")
    write_filtered_yaml(args.data, output_yaml, output_root, classes)

    print(f"Filtered dataset created at: {output_root}")
    print(f"Filtered data.yaml: {output_yaml}")
    print(f"Inactive class IDs: {sorted(inactive_ids)}")


if __name__ == "__main__":
    main()
