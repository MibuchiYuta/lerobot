"""Structured JSON rule definitions and validation for object sorting."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Conditions:
    """All populated fields must match for a rule to apply."""

    colors_any: frozenset[str] = frozenset()
    colors_all: frozenset[str] = frozenset()
    kinds_any: frozenset[str] = frozenset()
    shapes_any: frozenset[str] = frozenset()
    x_range: tuple[float | None, float | None] | None = None
    y_range: tuple[float | None, float | None] | None = None

    @property
    def specificity(self) -> int:
        """Return independent constraints used in conflict resolution."""
        return sum(
            condition is not None and condition != frozenset()
            for condition in (
                self.colors_any,
                self.colors_all,
                self.kinds_any,
                self.shapes_any,
                self.x_range,
                self.y_range,
            )
        )


@dataclass(frozen=True)
class Rule:
    """A deterministic routing instruction with an auditable source sentence."""

    id: str
    text: str
    destination: str
    conditions: Conditions
    priority: int = 0
    force: bool = False


@dataclass(frozen=True)
class RuleSet:
    """Ordered rules and the destination used when none match."""

    rules: tuple[Rule, ...]
    default_destination: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> RuleSet:
        """Validate and build a ruleset from decoded JSON-compatible data."""
        default_destination = _required_string(data, "default_destination")
        raw_rules = data.get("rules")
        if not isinstance(raw_rules, Sequence) or isinstance(raw_rules, str):
            raise ValueError("'rules' must be a list of rule mappings.")
        rules = tuple(_rule_from_mapping(item, index) for index, item in enumerate(raw_rules))
        ids = [rule.id for rule in rules]
        if len(ids) != len(set(ids)):
            raise ValueError("Rule IDs must be unique.")
        return cls(rules=rules, default_destination=default_destination)


def load_rules(path: str | Path) -> RuleSet:
    """Load a JSON ruleset without a runtime inference-model dependency."""
    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, Mapping):
        raise ValueError("Rules file must contain a JSON object.")
    return RuleSet.from_mapping(data)


def _rule_from_mapping(value: Any, index: int) -> Rule:
    if not isinstance(value, Mapping):
        raise ValueError(f"Rule at index {index} must be a mapping.")
    conditions = value.get("when")
    if not isinstance(conditions, Mapping):
        raise ValueError(f"Rule '{value.get('id', index)}' requires a 'when' mapping.")
    parsed_conditions = Conditions(
        colors_any=_labels(conditions, "colors_any"),
        colors_all=_labels(conditions, "colors_all"),
        kinds_any=_labels(conditions, "kinds_any"),
        shapes_any=_labels(conditions, "shapes_any"),
        x_range=_range(conditions, "x"),
        y_range=_range(conditions, "y"),
    )
    if not parsed_conditions.specificity:
        raise ValueError(f"Rule '{value.get('id', index)}' must have at least one condition.")
    priority = value.get("priority", 0)
    force = value.get("force", False)
    if not isinstance(priority, int) or isinstance(priority, bool):
        raise ValueError("'priority' must be an integer.")
    if not isinstance(force, bool):
        raise ValueError("'force' must be a boolean.")
    return Rule(
        id=_required_string(value, "id"),
        text=_required_string(value, "text"),
        destination=_required_string(value, "destination"),
        conditions=parsed_conditions,
        priority=priority,
        force=force,
    )


def _required_string(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"'{key}' must be a non-empty string.")
    return result.strip()


def _labels(value: Mapping[str, Any], key: str) -> frozenset[str]:
    raw_labels = value.get(key, ())
    if isinstance(raw_labels, str):
        raw_labels = (raw_labels,)
    if not isinstance(raw_labels, Sequence):
        raise ValueError(f"'{key}' must be a string or list of strings.")
    if not all(isinstance(label, str) and label.strip() for label in raw_labels):
        raise ValueError(f"'{key}' must contain non-empty strings only.")
    return frozenset(label.strip().lower() for label in raw_labels)


def _range(value: Mapping[str, Any], key: str) -> tuple[float | None, float | None] | None:
    raw_range = value.get(key)
    if raw_range is None:
        return None
    if not isinstance(raw_range, Sequence) or isinstance(raw_range, str) or len(raw_range) != 2:
        raise ValueError(f"'{key}' must be a [minimum, maximum] list.")
    minimum, maximum = raw_range
    if minimum is not None and not isinstance(minimum, (int, float)):
        raise ValueError(f"'{key}' minimum must be a number or null.")
    if maximum is not None and not isinstance(maximum, (int, float)):
        raise ValueError(f"'{key}' maximum must be a number or null.")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError(f"'{key}' minimum cannot exceed maximum.")
    return (float(minimum) if minimum is not None else None, float(maximum) if maximum is not None else None)
