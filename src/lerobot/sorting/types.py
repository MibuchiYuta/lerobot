"""Types exchanged between the perception pipeline and sorting rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


def _normalise_label(value: str) -> str:
    return value.strip().lower()


@dataclass(frozen=True)
class Position:
    """Object centre in normalized image coordinates, when available."""

    x: float | None = None
    y: float | None = None


@dataclass(frozen=True)
class DetectedObject:
    """Lightweight perception result consumed by :class:`RuleEngine`.

    ``from_mapping`` accepts canonical ``kind``, ``colors`` and ``position`` fields
    plus common perception aliases, keeping this module detector-independent.
    """

    kind: str
    colors: frozenset[str] = frozenset()
    shape: str | None = None
    position: Position = Position()
    object_id: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> DetectedObject:
        """Create an object from a perception-pipeline result mapping."""
        kind = value.get("kind", value.get("label", value.get("category", value.get("type"))))
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("Detected object requires a non-empty 'kind' or 'label'.")

        raw_colors = value.get("colors", value.get("color", ()))
        if isinstance(raw_colors, str):
            colors = frozenset({_normalise_label(raw_colors)})
        elif isinstance(raw_colors, Sequence):
            if not all(isinstance(color, str) for color in raw_colors):
                raise ValueError("'colors' must contain only strings.")
            colors = frozenset(_normalise_label(color) for color in raw_colors)
        else:
            raise ValueError("'color' or 'colors' must be a string or a sequence of strings.")

        raw_shape = value.get("shape", value.get("form"))
        if raw_shape is not None and not isinstance(raw_shape, str):
            raise ValueError("'shape' must be a string when supplied.")
        object_id = value.get("object_id", value.get("id"))
        if object_id is not None and not isinstance(object_id, str):
            raise ValueError("'object_id' must be a string when supplied.")
        return cls(
            kind=_normalise_label(kind),
            colors=colors,
            shape=_normalise_label(raw_shape) if raw_shape else None,
            position=_position_from_mapping(value),
            object_id=object_id,
        )


def _position_from_mapping(value: Mapping[str, Any]) -> Position:
    raw_position = value.get("position")
    if isinstance(raw_position, Mapping):
        return Position(x=_number_or_none(raw_position.get("x")), y=_number_or_none(raw_position.get("y")))
    if "x" in value or "y" in value:
        return Position(x=_number_or_none(value.get("x")), y=_number_or_none(value.get("y")))
    bbox = value.get("bbox")
    if isinstance(bbox, Sequence) and not isinstance(bbox, str) and len(bbox) == 4:
        x, y, width, height = bbox
        if all(isinstance(item, (int, float)) for item in bbox):
            return Position(x=float(x) + float(width) / 2, y=float(y) + float(height) / 2)
    return Position()


def _number_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError("Position coordinates must be numbers.")
    return float(value)


@dataclass(frozen=True)
class Decision:
    """The destination and auditable reason selected by the rule engine."""

    destination: str
    rule_id: str | None
    matched_rule_ids: tuple[str, ...]
    trace: str
