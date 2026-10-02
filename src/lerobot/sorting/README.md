# SO-101 sorting rule engine

`lerobot.sorting` converts structured, human-authored sorting rules into a deterministic destination. It does not call an LLM at decision time.

Rules are JSON so they can be versioned, validated, and reviewed. Each rule preserves its original natural-language instruction in `text` and expresses its executable condition in `when`.

```python
from pathlib import Path

from lerobot.sorting import DetectedObject, RuleEngine, load_rules

rules = load_rules(Path("src/lerobot/sorting/sample_rules.json"))
object_to_sort = DetectedObject.from_mapping(
    {"kind": "ball", "colors": ["pink"], "shape": "round", "position": {"x": 0.4, "y": 0.5}}
)
decision = RuleEngine(rules).decide(object_to_sort)
assert decision.destination == "center"  # the forced round rule wins
```

## Rule format

The root object has `default_destination` and an ordered `rules` list. A rule has `id`, `text`, `destination`, optional integer `priority`, optional boolean `force`, and `when`.

`when` combines every supplied condition with AND:

- `colors_any`, `colors_all`, `kinds_any`, `shapes_any`: a string or list of case-insensitive labels.
- `x`, `y`: inclusive `[minimum, maximum]` normalized-coordinate ranges; use `null` for an open bound.

When several rules match, the engine selects, in order: `force: true`, higher `priority`, more populated condition fields, then earlier file order. `Decision.trace` and `matched_rule_ids` retain the full result for logging.

## Perception interface

The canonical input is `kind`, `colors`, `shape`, and `position: {x, y}`. `DetectedObject.from_mapping()` also accepts `label`/`category`/`type`, singular `color`, direct `x`/`y`, and `[x, y, width, height]` `bbox`. This is deliberately a small adapter while the subproject-2 perception schema is finalized.
