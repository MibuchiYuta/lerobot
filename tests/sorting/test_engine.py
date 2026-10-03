import json
from pathlib import Path

import pytest

from lerobot.sorting import DetectedObject, RuleEngine, RuleSet, load_rules


SAMPLE_RULES = Path(__file__).parents[2] / "src/lerobot/sorting/sample_rules.json"


@pytest.fixture
def engine():
    return RuleEngine(load_rules(SAMPLE_RULES))


@pytest.mark.parametrize(
    ("raw_object", "destination", "rule_id"),
    [
        ({"kind": "toy", "color": "pink"}, "left", "pink-left"),
        ({"kind": "ball", "colors": ["pink"], "shape": "round"}, "center", "round-center"),
        ({"kind": "cube", "colors": ["red"]}, "right", "red-cube-right"),
        ({"kind": "disc", "colors": ["blue"], "position": {"x": 0.2}}, "left", "blue-left-zone"),
        ({"kind": "cylinder", "colors": ["green"]}, "right", "green-cylinder-right"),
        ({"kind": "token", "colors": ["yellow"], "shape": "triangle"}, "center", "yellow-triangle-center"),
        ({"kind": "gear", "colors": ["silver"]}, "left", "silver-gear-left"),
        ({"kind": "token", "colors": ["purple"], "shape": "star"}, "right", "purple-star-right"),
        ({"kind": "tile", "colors": ["orange"], "shape": "square"}, "center", "orange-square-center"),
        ({"kind": "cube", "colors": ["black"], "position": {"y": 0.8}}, "right", "black-lower-cube-right"),
    ],
)
def test_sample_rules_route_sample_objects(engine, raw_object, destination, rule_id):
    decision = engine.decide(DetectedObject.from_mapping(raw_object))

    assert decision.destination == destination
    assert decision.rule_id == rule_id


def test_force_rule_resolves_conflicts():
    rules = RuleSet.from_mapping(
        {
            "default_destination": "reject",
            "rules": [
                {"id": "first", "text": "first", "destination": "left", "priority": 3, "when": {"colors_any": "red"}},
                {"id": "specific", "text": "specific", "destination": "right", "priority": 3, "when": {"colors_any": "red", "kinds_any": "cube"}},
                {"id": "forced", "text": "forced", "destination": "center", "priority": 0, "force": True, "when": {"colors_any": "red"}},
            ],
        }
    )

    # This object matches every rule: ``specific`` requires both red and cube,
    # while ``first`` and ``forced`` require red only. Forced rules rank first;
    # between the two non-forced equal-priority rules, ``specific`` ranks first.
    decision = RuleEngine(rules).decide(DetectedObject.from_mapping({"kind": "cube", "color": "red"}))

    assert decision.destination == "center"
    assert decision.matched_rule_ids == ("forced", "specific", "first")


@pytest.mark.parametrize(
    ("raw_object", "expected_colors"),
    [
        ({"kind": "cube", "color": None}, frozenset()),
        ({"kind": "cube", "colors": None}, frozenset()),
        ({"kind": "cube", "colors": None, "color": "red"}, frozenset({"red"})),
    ],
)
def test_detected_object_treats_none_colors_as_missing(raw_object, expected_colors):
    assert DetectedObject.from_mapping(raw_object).colors == expected_colors


@pytest.mark.parametrize(
    ("rules", "expected_rule_id"),
    [
        (
            [
                {"id": "low", "text": "low", "destination": "left", "priority": 1, "when": {"colors_any": "red"}},
                {"id": "high", "text": "high", "destination": "right", "priority": 2, "when": {"colors_any": "red"}},
            ],
            "high",
        ),
        (
            [
                {"id": "simple", "text": "simple", "destination": "left", "when": {"colors_any": "red"}},
                {"id": "specific", "text": "specific", "destination": "right", "when": {"colors_any": "red", "kinds_any": "cube"}},
            ],
            "specific",
        ),
        (
            [
                {"id": "first", "text": "first", "destination": "left", "when": {"colors_any": "red"}},
                {"id": "second", "text": "second", "destination": "right", "when": {"colors_any": "red"}},
            ],
            "first",
        ),
    ],
)
def test_priority_specificity_and_file_order_resolve_remaining_conflicts(rules, expected_rule_id):
    ruleset = RuleSet.from_mapping({"default_destination": "reject", "rules": rules})

    decision = RuleEngine(ruleset).decide(DetectedObject.from_mapping({"kind": "cube", "color": "red"}))

    assert decision.rule_id == expected_rule_id


def test_default_destination_and_perception_aliases(engine):
    decision = engine.decide(
        DetectedObject.from_mapping({"label": "unknown", "color": "beige", "bbox": [0.1, 0.2, 0.2, 0.2]})
    )

    assert decision.destination == "center"
    assert decision.rule_id is None
    assert "No rule matched" in decision.trace


def test_rejects_invalid_rule_data(tmp_path):
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text(json.dumps({"default_destination": "left", "rules": [{"id": "bad"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="requires a 'when' mapping"):
        load_rules(invalid_path)
