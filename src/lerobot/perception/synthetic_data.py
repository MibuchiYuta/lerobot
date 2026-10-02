"""Generate deterministic, coloured-object images for offline pipeline tests."""

from __future__ import annotations

import argparse
from pathlib import Path


def _cv2():
    from .color_detection import _cv2 as get_cv2

    return get_cv2()


def create_sample(image_size: tuple[int, int] = (320, 240), offset: int = 0):
    """Create one BGR image containing a red rectangle on a neutral background."""
    cv2 = _cv2()
    width, height = image_size
    if width < 80 or height < 80:
        raise ValueError("image_size must be at least 80 pixels in each direction")
    image = cv2.cvtColor(cv2.UMat(height, width, cv2.CV_8UC1).get(), cv2.COLOR_GRAY2BGR)
    image[:] = (40, 40, 40)
    x, y = 30 + offset % 50, 40 + offset % 30
    cv2.rectangle(image, (x, y), (x + 60, y + 45), (0, 0, 255), thickness=-1)
    return image


def generate(output_dir: Path, count: int = 8) -> list[Path]:
    """Write ``count`` synthetic PNG files and return their paths."""
    if count <= 0:
        raise ValueError("count must be positive")
    cv2 = _cv2()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index in range(count):
        path = output_dir / f"sample_{index:04d}.png"
        if not cv2.imwrite(str(path), create_sample(offset=index * 7)):
            raise OSError(f"unable to write image: {path}")
        paths.append(path)
    return paths


def main() -> None:
    """Generate synthetic images from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args()
    generate(args.output_dir, args.count)


if __name__ == "__main__":
    main()
