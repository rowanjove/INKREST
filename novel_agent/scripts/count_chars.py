import re
from typing import Dict


def count_chinese_chars(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def wordcount_report(text: str, target_min: int, target_max: int) -> Dict[str, int]:
    count = count_chinese_chars(text)
    if count < target_min:
        return {
            "count": count,
            "target_min": target_min,
            "target_max": target_max,
            "status": "under",
            "missing": target_min - count,
            "excess": 0,
        }
    if count > target_max:
        return {
            "count": count,
            "target_min": target_min,
            "target_max": target_max,
            "status": "over",
            "missing": 0,
            "excess": count - target_max,
        }
    return {
        "count": count,
        "target_min": target_min,
        "target_max": target_max,
        "status": "ok",
        "missing": 0,
        "excess": 0,
    }

