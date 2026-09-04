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


def repair_truncated_json(text: str) -> Any:
    """Attempt to repair and parse a truncated JSON text (e.g. cut off by max_tokens).

    Finds the last balanced structural boundary (e.g. after a completed array element),
    computes the missing closing brackets/braces, and parses the recovered data.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = _strip_code_fence(cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Reverse scan for potential cut-off points ending with '}' or ']'
    for i in range(len(cleaned) - 1, 0, -1):
        if cleaned[i] in ("}", "]"):
            sub = cleaned[:i + 1]
            stack = []
            in_str = False
            esc = False
            for c in sub:
                if in_str:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == '"':
                        in_str = False
                else:
                    if c == '"':
                        in_str = True
                    elif c in ("{", "["):
                        stack.append(c)
                    elif c == "}" and stack and stack[-1] == "{":
                        stack.pop()
                    elif c == "]" and stack and stack[-1] == "[":
                        stack.pop()
            if not in_str and stack:
                closing = "".join("}" if b == "{" else "]" for b in reversed(stack))
                try:
                    recovered = json.loads(sub + closing)
                    logger.info("Successfully repaired truncated JSON (recovered %d bytes)", len(sub))
                    return recovered
                except Exception:
                    continue
    return None


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

