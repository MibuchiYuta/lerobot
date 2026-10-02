import importlib.util

import pytest

from lerobot.perception.color_detection import HSVRange
from lerobot.perception.synthetic_data import generate
from lerobot.perception.yolo_self_label import label_images, split_dataset, train

cv2_available = importlib.util.find_spec("cv2") is not None
pytestmark = pytest.mark.skipif(not cv2_available, reason="OpenCV is not installed")


def test_self_label_split_and_dry_run(tmp_path):
    images = tmp_path / "images"
    labels = tmp_path / "labels"
    generate(images, count=3)

    assert label_images(images, labels, HSVRange((170, 100, 100), (10, 255, 255))) == 3
    dataset_yaml = split_dataset(images, labels, tmp_path / "dataset")

    assert dataset_yaml.exists()
    assert len(list((tmp_path / "dataset" / "images" / "train").iterdir())) == 2
    assert len(list((tmp_path / "dataset" / "images" / "val").iterdir())) == 1
    train(dataset_yaml, dry_run=True)
