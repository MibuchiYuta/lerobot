"""Create YOLO labels from HSV detections, split data, and optionally train Ultralytics YOLO."""

from __future__ import annotations

import argparse
import fcntl
import random
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .color_detection import HSVRange, _cv2, detect_color

IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}


@contextmanager
def _output_lock(output_dir: Path) -> Iterator[None]:
    """Serialise writers targeting the same generated dataset directory."""
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output_dir.parent / f".{output_dir.name}.lock"
    with lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def image_paths(images_dir: Path) -> list[Path]:
    """Return sorted image files directly under ``images_dir``."""
    return sorted(path for path in images_dir.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)


def label_images(images_dir: Path, labels_dir: Path, hsv_range: HSVRange, min_area: float = 100.0) -> int:
    """Generate one class-0 YOLO label file per image; empty labels are intentional negatives."""
    cv2 = _cv2()
    labels_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for image_path in image_paths(images_dir):
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"unable to read image: {image_path}")
        height, width = image.shape[:2]
        lines = []
        for detection in detect_color(image, hsv_range, min_area):
            x_center, y_center, box_width, box_height = detection.yolo(width, height)
            lines.append(f"0 {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}")
        (labels_dir / f"{image_path.stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
        count += 1
    return count


def split_dataset(images_dir: Path, labels_dir: Path, output_dir: Path, train_ratio: float = 0.8, seed: int = 0) -> Path:
    """Copy images and generated labels into the conventional YOLO train/val structure."""
    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio must be between 0 and 1")
    paths = image_paths(images_dir)
    if len(paths) < 2:
        raise ValueError("at least two images are required to create train and validation splits")
    random.Random(seed).shuffle(paths)
    split_index = min(max(1, round(len(paths) * train_ratio)), len(paths) - 1)
    with _output_lock(output_dir):
        for split, split_paths in (("train", paths[:split_index]), ("val", paths[split_index:])):
            for image_path in split_paths:
                label_path = labels_dir / f"{image_path.stem}.txt"
                if not label_path.exists():
                    raise FileNotFoundError(f"missing label for {image_path.name}: {label_path}")
                image_target = output_dir / "images" / split / image_path.name
                label_target = output_dir / "labels" / split / label_path.name
                image_target.parent.mkdir(parents=True, exist_ok=True)
                label_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(image_path, image_target)
                shutil.copy2(label_path, label_target)
        config = output_dir / "dataset.yaml"
        config.write_text(f"path: {output_dir.resolve()}\ntrain: images/train\nval: images/val\nnames:\n  0: object\n")
    return config


def train(dataset_yaml: Path, epochs: int = 1, model: str = "yolo11n.pt", dry_run: bool = False) -> None:
    """Train on CPU, or validate all non-training setup in ``dry_run`` mode."""
    if not dataset_yaml.exists():
        raise FileNotFoundError(dataset_yaml)
    if dry_run:
        return
    try:
        from ultralytics import YOLO
    except ModuleNotFoundError as error:
        raise RuntimeError("install with `pip install -e '.[perception]'` to train YOLO") from error
    YOLO(model).train(data=str(dataset_yaml), epochs=epochs, device="cpu")


def _hsv_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--lower", nargs=3, type=int, required=True, metavar=("H", "S", "V"))
    parser.add_argument("--upper", nargs=3, type=int, required=True, metavar=("H", "S", "V"))
    parser.add_argument("--min-area", type=float, default=100.0)


def main() -> None:
    """Expose labeling, splitting, and CPU training as subcommands."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    label = commands.add_parser("label")
    label.add_argument("images_dir", type=Path)
    label.add_argument("labels_dir", type=Path)
    _hsv_arguments(label)
    split = commands.add_parser("split")
    split.add_argument("images_dir", type=Path)
    split.add_argument("labels_dir", type=Path)
    split.add_argument("output_dir", type=Path)
    split.add_argument("--train-ratio", type=float, default=0.8)
    split.add_argument("--seed", type=int, default=0)
    training = commands.add_parser("train")
    training.add_argument("dataset_yaml", type=Path)
    training.add_argument("--epochs", type=int, default=1)
    training.add_argument("--model", default="yolo11n.pt")
    training.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.command == "label":
        label_images(args.images_dir, args.labels_dir, HSVRange(tuple(args.lower), tuple(args.upper)), args.min_area)
    elif args.command == "split":
        split_dataset(args.images_dir, args.labels_dir, args.output_dir, args.train_ratio, args.seed)
    else:
        train(args.dataset_yaml, args.epochs, args.model, args.dry_run)


if __name__ == "__main__":
    main()
