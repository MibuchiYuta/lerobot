import json

import pytest

from lerobot.perception.vlm_client import OllamaVLMClient


def test_vlm_client_defaults_to_installed_vision_model():
    assert OllamaVLMClient().model == "qwen2.5vl:7b"


def test_vlm_client_uses_injected_transport(tmp_path):
    image = tmp_path / "image.png"
    image.write_bytes(b"fake-image")
    received = {}

    def transport(url, body, timeout):
        received.update(url=url, body=json.loads(body), timeout=timeout)
        return {"message": {"content": "red block"}}

    result = OllamaVLMClient(model="test-model", transport=transport).classify(image)

    assert result == "red block"
    assert received["url"].endswith("/api/chat")
    assert received["body"]["model"] == "test-model"
    assert received["body"]["messages"][0]["images"]


def test_vlm_client_explains_how_to_debug_an_unexpected_response(tmp_path):
    image = tmp_path / "image.png"
    image.write_bytes(b"fake-image")

    with pytest.raises(ValueError, match="installed model and Ollama version"):
        OllamaVLMClient(transport=lambda *_args: {}).classify(image)
