from .registry import ACTIONS
from .validator import validate_actions


def simulate_actions(actions):
    timeline = []
    elapsed_ms = 0
    sanitized, warnings = validate_actions(actions)
    for action in sanitized:
        spec = ACTIONS[action]
        timeline.append(
            {
                "start_ms": elapsed_ms,
                "action": action,
                "duration_ms": spec.duration_ms,
                "category": spec.category,
            }
        )
        elapsed_ms += spec.duration_ms
    return {
        "actions": sanitized,
        "timeline": timeline,
        "total_duration_ms": elapsed_ms,
        "warnings": warnings,
    }

