"""Deterministic matching and conflict resolution for sorting rules."""

from __future__ import annotations

from lerobot.sorting.rules import Rule, RuleSet
from lerobot.sorting.types import Decision, DetectedObject


class RuleEngine:
    """Route perception results without calling a language model at decision time."""

    def __init__(self, ruleset: RuleSet):
        self.ruleset = ruleset

    def decide(self, detected_object: DetectedObject) -> Decision:
        """Return the deterministic destination and an explanation of its selection."""
        matches = [(index, rule) for index, rule in enumerate(self.ruleset.rules) if _matches(rule, detected_object)]
        if not matches:
            return Decision(
                destination=self.ruleset.default_destination,
                rule_id=None,
                matched_rule_ids=(),
                trace="No rule matched; using the default destination.",
            )

        ranked_matches = sorted(matches, key=_rank, reverse=True)
        winner_index, winner = ranked_matches[0]
        matched_ids = tuple(rule.id for _, rule in ranked_matches)
        return Decision(
            destination=winner.destination,
            rule_id=winner.id,
            matched_rule_ids=matched_ids,
            trace=(
                f"Selected '{winner.id}' (force={winner.force}, priority={winner.priority}, "
                f"specificity={winner.conditions.specificity}, order={winner_index}) from {matched_ids}."
            ),
        )


def _rank(match: tuple[int, Rule]) -> tuple[int, int, int, int]:
    index, rule = match
    return (int(rule.force), rule.priority, rule.conditions.specificity, -index)


def _matches(rule: Rule, detected_object: DetectedObject) -> bool:
    conditions = rule.conditions
    return (
        (not conditions.colors_any or bool(detected_object.colors & conditions.colors_any))
        and (not conditions.colors_all or conditions.colors_all <= detected_object.colors)
        and (not conditions.kinds_any or detected_object.kind in conditions.kinds_any)
        and (not conditions.shapes_any or detected_object.shape in conditions.shapes_any)
        and _in_range(detected_object.position.x, conditions.x_range)
        and _in_range(detected_object.position.y, conditions.y_range)
    )


def _in_range(value: float | None, bounds: tuple[float | None, float | None] | None) -> bool:
    if bounds is None:
        return True
    if value is None:
        return False
    minimum, maximum = bounds
    return (minimum is None or minimum <= value) and (maximum is None or value <= maximum)
