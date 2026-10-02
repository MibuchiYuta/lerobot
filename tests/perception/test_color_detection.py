import importlib.util

import pytest

from lerobot.perception.color_detection import HSVRange, detect_color
from lerobot.perception.synthetic_data import create_sample

cv2_available = importlib.util.find_spec("cv2") is not None
pytestmark = pytest.mark.skipif(not cv2_available, reason="OpenCV is not installed")


def test_detect_color_handles_hue_wraparound():
    image = create_sample()

    detections = detect_color(image, HSVRange((170, 100, 100), (10, 255, 255)))

    assert len(detections) == 1
    assert detections[0].x == 30
    assert detections[0].y == 40
    assert detections[0].width >= 60
    assert detections[0].height >= 45


def test_yolo_coordinates_are_normalized():
    detection = detect_color(create_sample(), HSVRange((170, 100, 100), (10, 255, 255)))[0]

    assert all(0.0 <= coordinate <= 1.0 for coordinate in detection.yolo(320, 240))
