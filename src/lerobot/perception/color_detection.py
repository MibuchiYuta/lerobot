"""Detect a coloured object with OpenCV HSV thresholds."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HSVRange:
    """Inclusive HSV bounds, using OpenCV's H=0..179 convention."""

    lower: tuple[int, int, int]
    upper: tuple[int, int, int]

    def validate(self) -> None:
        """Validate bounds before they are passed to OpenCV."""
        for value in (*self.lower, *self.upper):
            if not 0 <= value <= 255:
                raise ValueError("HSV values must be between 0 and 255")
        if self.lower[0] > 179 or self.upper[0] > 179:
            raise ValueError("OpenCV hue values must be between 0 and 179")
        if any(lower > upper for lower, upper in zip(self.lower[1:], self.upper[1:], strict=True)):
            raise ValueError("lower S/V bounds must not exceed upper bounds")


@dataclass(frozen=True)
class Detection:
    """A pixel bounding box produced by the colour detector."""

    x: int
    y: int
    width: int
    height: int
    area: float

    def yolo(self, image_width: int, image_height: int) -> tuple[float, float, float, float]:
        """Return normalized YOLO ``x_center, y_center, width, height`` coordinates."""
        if image_width <= 0 or image_height <= 0:
            raise ValueError("image dimensions must be positive")
        return (
            (self.x + self.width / 2) / image_width,
            (self.y + self.height / 2) / image_height,
            self.width / image_width,
            self.height / image_height,
        )


def _cv2() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as error:
        raise RuntimeError("OpenCV is required; install the base lerobot dependencies") from error
    return cv2


def detect_color(image: Any, hsv_range: HSVRange, min_area: float = 100.0) -> list[Detection]:
    """Return bounding boxes for connected regions within an HSV range.

    A hue range whose lower hue exceeds its upper hue wraps across red (179 -> 0).
    """
    if min_area < 0:
        raise ValueError("min_area must be non-negative")
    hsv_range.validate()
    cv2 = _cv2()
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower, upper = hsv_range.lower, hsv_range.upper
    if lower[0] <= upper[0]:
        mask = cv2.inRange(hsv, lower, upper)
    else:
        low_hue = cv2.inRange(hsv, lower, (179, upper[1], upper[2]))
        high_hue = cv2.inRange(hsv, (0, lower[1], lower[2]), upper)
        mask = cv2.bitwise_or(low_hue, high_hue)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detections = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area >= min_area:
            x, y, width, height = cv2.boundingRect(contour)
            detections.append(Detection(x, y, width, height, area))
    return sorted(detections, key=lambda detection: detection.area, reverse=True)


def annotate(image: Any, detections: list[Detection]) -> Any:
    """Return a copy of ``image`` with detected boxes drawn on it."""
    cv2 = _cv2()
    output = image.copy()
    for detection in detections:
        cv2.rectangle(
            output,
            (detection.x, detection.y),
            (detection.x + detection.width, detection.y + detection.height),
            (0, 255, 0),
            2,
        )
    return output


def main() -> None:
    """Run HSV detection for one image and emit boxes as JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--lower", nargs=3, type=int, required=True, metavar=("H", "S", "V"))
    parser.add_argument("--upper", nargs=3, type=int, required=True, metavar=("H", "S", "V"))
    parser.add_argument("--min-area", type=float, default=100.0)
    parser.add_argument("--annotated-output", type=Path)
    args = parser.parse_args()
    cv2 = _cv2()
    image = cv2.imread(str(args.image))
    if image is None:
        parser.error(f"unable to read image: {args.image}")
    detections = detect_color(image, HSVRange(tuple(args.lower), tuple(args.upper)), args.min_area)
    print(json.dumps([asdict(detection) for detection in detections]))
    if args.annotated_output:
        args.annotated_output.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(args.annotated_output), annotate(image, detections)):
            parser.error(f"unable to write image: {args.annotated_output}")


if __name__ == "__main__":
    main()
