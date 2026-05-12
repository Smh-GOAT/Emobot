from dataclasses import dataclass


@dataclass(frozen=True)
class ActionSpec:
    name: str
    category: str
    duration_ms: int
    requires_center_after: bool = False


EYE_ACTIONS = (
    "eye_blink",
    "eye_happy",
    "eye_sad",
    "eye_anger",
    "eye_surprise",
    "eye_left",
    "eye_right",
)

HEAD_ACTIONS = (
    "head_left",
    "head_right",
    "head_up",
    "head_down",
    "head_nod",
    "head_shake",
    "head_roll_left",
    "head_roll_right",
    "head_center",
)

ANIMATION_ACTIONS = (
    "heart",
    "calendar",
    "face_id",
    "cola",
    "laugh",
    "dumbbell",
    "skateboard",
    "battery",
    "basketball",
    "rugby",
    "alarm",
    "screen",
    "wifi",
    "youtube",
    "tv",
    "movie",
    "cat",
    "write",
    "phone",
    "sunny",
    "cloudy",
    "rainy",
    "windy",
    "snow",
    "beer",
    "walk",
    "shit",
    "cry",
    "puzzled",
    "football",
    "volleyball",
    "badminton",
    "rice",
    "gym",
    "boat",
    "thinking",
    "money",
    "wait",
    "plane",
    "rocket",
    "ok",
    "love",
)

ALIASES = {
    "eye_angry": "eye_anger",
    "eye_surprised": "eye_surprise",
}

_DIRECTIONAL_HEAD_ACTIONS = {"head_left", "head_right", "head_up", "head_down"}

ACTIONS = {
    **{
        name: ActionSpec(name=name, category="eye", duration_ms=300)
        for name in EYE_ACTIONS
    },
    **{
        name: ActionSpec(
            name=name,
            category="head",
            duration_ms=1200 if name != "head_center" else 500,
            requires_center_after=name in _DIRECTIONAL_HEAD_ACTIONS,
        )
        for name in HEAD_ACTIONS
    },
    **{
        name: ActionSpec(name=name, category="animation", duration_ms=1200)
        for name in ANIMATION_ACTIONS
    },
    "delay": ActionSpec(name="delay", category="timing", duration_ms=1000),
}

VALID_ACTION_NAMES = frozenset(ACTIONS)

