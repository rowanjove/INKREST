import json
import re
from pathlib import Path
from typing import Dict, List, Mapping, Optional


def load_sensitive_words(words_file: Path) -> List[str]:
    words_file = Path(words_file)
    if not words_file.exists():
        return []
    words = []
    for line in words_file.read_text(encoding="utf-8").splitlines():
        word = line.strip()
        if word and not word.startswith("#"):
            words.append(word)
    return words


def _build_pattern(words: List[str]) -> re.Pattern:
    """Build a compiled regex pattern from word list for efficient scanning."""
    if not words:
        return re.compile(r"(?!)")  # Never-matching pattern
    # Escape special regex characters and join with OR
    escaped = [re.escape(word) for word in words]
    return re.compile("|".join(escaped))


def load_sensitive_replacements(path: Path) -> Dict[str, str]:
    path = Path(path)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if str(key) and str(value)}


def apply_sensitive_word_patches(
    text: str,
    words: List[str],
    replacements: Optional[Mapping[str, str]] = None,
) -> str:
    """Replace known sensitive hits in place. Longest words first."""
    if not text or not words:
        return text or ""
    mapping = dict(replacements or {})
    updated = text
    for word in sorted({item for item in words if item}, key=len, reverse=True):
        if word not in updated:
            continue
        repl = mapping.get(word)
        if repl is None:
            if len(word) < 2:
                continue
            repl = word[0] + "某"
            if repl == word:
                continue
        updated = updated.replace(word, repl)
    return updated


def scan_sensitive_words(text: str, words_file: Path) -> Dict[str, object]:
    if text is None:
        text = ""
    words = load_sensitive_words(words_file)
    if not words:
        return {"status": "clean", "hits": [], "word_count": 0}

    # Use compiled regex for O(n) scanning instead of O(n*m)
    pattern = _build_pattern(words)
    hits = []

    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in pattern.finditer(line):
            hits.append(
                {
                    "word": match.group(),
                    "line": line_no,
                    "column": match.start() + 1,
                    "text": line.strip(),
                }
            )

    return {
        "status": "hit" if hits else "clean",
        "hits": hits,
        "word_count": len(words),
    }

