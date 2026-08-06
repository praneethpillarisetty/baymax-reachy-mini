from __future__ import annotations

import json
from typing import Any

from ..contracts import ActionRequest, ModelResponse

ALLOWED_EMOTIONS = {
    "neutral",
    "greeting",
    "listening",
    "thinking",
    "caring",
    "concern",
    "reminder",
    "goodbye",
}


def parse_model_response(payload: str | dict[str, Any]) -> ModelResponse:
    try:
        data = json.loads(payload) if isinstance(payload, str) else payload
    except json.JSONDecodeError as exc:
        raise ValueError("model response is not valid JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("message"), str):
        raise ValueError("model response requires a string message")
    if not data["message"].strip() or len(data["message"]) > 4000:
        raise ValueError("model message is empty or too long")
    raw_actions = data.get("actions", [])
    if not isinstance(raw_actions, list) or len(raw_actions) > 10:
        raise ValueError("actions must be a list of at most 10 items")
    actions = []
    for item in raw_actions:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("tool"), str)
            or not isinstance(item.get("arguments", {}), dict)
        ):
            raise ValueError("invalid action")
        actions.append(ActionRequest(item["tool"], item.get("arguments", {})))
    emotion = data.get("emotion", "neutral")
    if emotion not in ALLOWED_EMOTIONS:
        emotion = "neutral"
    return ModelResponse(data["message"].strip(), tuple(actions), emotion)
