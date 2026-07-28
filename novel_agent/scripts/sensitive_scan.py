import re
from pathlib import Path
from typing import Dict, List


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

