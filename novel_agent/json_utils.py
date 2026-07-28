import json
from typing import Any

from novel_agent.logging_config import get_logger

logger = get_logger("json_utils")


# Maximum input size for JSON parsing (1MB)
_MAX_JSON_SIZE = 1_048_576


def loads_json_object(text: str):
    if len(text) > _MAX_JSON_SIZE:
        raise ValueError(f"JSON input too large: {len(text)} bytes (max {_MAX_JSON_SIZE})")
    text = text.strip()
    if text.startswith("```"):
        text = _strip_code_fence(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON object {...}
        obj_start = text.find("{")
        obj_end = text.rfind("}")
        # Try to extract JSON array [...]
        arr_start = text.find("[")
        arr_end = text.rfind("]")

        # Pick whichever comes first and is valid
        candidates = []
        if obj_start != -1 and obj_end > obj_start:
            candidates.append((obj_start, obj_end, "{", "}"))
        if arr_start != -1 and arr_end > arr_start:
            candidates.append((arr_start, arr_end, "[", "]"))

        if not candidates:
            raise

        # Use whichever appears first in the text
        candidates.sort(key=lambda c: c[0])
        for start, end, _, _ in candidates:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
        raise


def safe_loads_json(text: str, fallback: Any = None) -> Any:
    """Parse JSON with automatic fallback on failure.

    Unlike ``loads_json_object`` which raises on parse failure,
    this returns ``fallback`` and logs a warning.
    """
    try:
        return loads_json_object(text)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        logger.warning("JSON parse failed, using fallback: %s", exc)
        return fallback


def _strip_code_fence(text: str) -> str:
    if text is None:
        return ""
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()

