"""Minimal Ollama vision client with a replaceable HTTP transport for tests."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

Transport = Callable[[str, bytes, float], dict]


def ollama_transport(url: str, body: bytes, timeout: float) -> dict:
    """POST JSON to Ollama and return its JSON response without extra dependencies."""
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 -- URL is configured by the local operator.
            return json.loads(response.read())
    except URLError as error:
        raise ConnectionError(f"Ollama request failed: {error.reason}") from error


class OllamaVLMClient:
    """Ask a locally hosted Ollama vision model to name the object in an image."""

    def __init__(
        self,
        model: str = "qwen3:14b",
        host: str = "http://127.0.0.1:11434",
        timeout: float = 30.0,
        transport: Transport = ollama_transport,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def classify(self, image_path: Path, prompt: str = "Identify the main object. Answer concisely.") -> str:
        """Return Ollama's textual answer for ``image_path``."""
        image = image_path.read_bytes()
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "user", "content": prompt, "images": [base64.b64encode(image).decode()]}],
        }
        response = self.transport(f"{self.host}/api/chat", json.dumps(payload).encode(), self.timeout)
        try:
            content = response["message"]["content"]
        except (KeyError, TypeError) as error:
            raise ValueError("Ollama response lacks message.content") from error
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama response contains an empty message.content")
        return content.strip()
