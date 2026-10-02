"""Small helpers for safe, cooperating access to experiment JSON Lines logs."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

try:  # ``fcntl`` is available on the Linux hosts used for robot operation.
    import fcntl
except ImportError:  # pragma: no cover - preserve importability on Windows.
    fcntl = None  # type: ignore[assignment]


@contextmanager
def locked_log_file(path: Path, mode: str) -> Iterator[TextIO]:
    """Open a log and take a cooperating shared/exclusive process lock when available."""
    if "a" in mode:
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode, encoding="utf-8") as log_file:
        if fcntl is not None:
            lock_type = fcntl.LOCK_EX if "a" in mode else fcntl.LOCK_SH
            fcntl.flock(log_file.fileno(), lock_type)
        try:
            yield log_file
        finally:
            if fcntl is not None:
                fcntl.flock(log_file.fileno(), fcntl.LOCK_UN)


def append_json_line(path: Path, payload: str) -> None:
    """Append one complete record durably while excluding cooperating readers/writers."""
    with locked_log_file(path, "a") as log_file:
        log_file.write(f"{payload}\n")
        log_file.flush()
        os.fsync(log_file.fileno())
