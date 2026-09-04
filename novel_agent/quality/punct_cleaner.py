"""Lightweight, zero-token punctuation and typography cleaner for novel prose."""

from __future__ import annotations

import re


def clean_punctuation_and_typography(text: str) -> str:
    """Clean common AI-generated punctuation and typography defects in Chinese prose.
    
    Operations performed:
    1. Normalize ascii punctuation in Chinese contexts (commas, colons, exclamation, question, semicolons).
    2. Deduplicate excessive repeated punctuation (e.g. !!! -> ！, ??? -> ？).
    3. Normalize ellipses to standard Chinese six-dot format (……).
    4. Normalize excessive em-dashes (———— -> ——).
    5. Clean trailing whitespace per line and collapse excessive blank lines.
    """
    if not text or not isinstance(text, str):
        return text or ""

    content = text

    # 1. 规范化破折号：3个或以上破折号收敛为中文标准双破折号 '——'
    content = re.sub(r"[—―-]{3,}", "——", content)

    # 2. 规范化省略号：3个以上连续点或多个省略号收敛为中文标准六点 '……'
    content = re.sub(r"\.{3,}", "……", content)
    # 一个或多个省略号字符统一为两个字符；对已经正确的“……”保持幂等。
    content = re.sub(r"…+", "……", content)

    # 3. 半角标点转全角（在中文或段落语境中）
    # 英文逗号紧随非数字或非英文单词，或位于汉字后
    content = re.sub(r"([\u4e00-\u9fa5]),\s*", r"\1，", content)
    content = re.sub(r",\s*([\u4e00-\u9fa5])", r"，\1", content)
    
    # 英文问号与感叹号
    content = re.sub(r"([\u4e00-\u9fa5])\?\s*", r"\1？", content)
    content = re.sub(r"\?\s*([\u4e00-\u9fa5])", r"？\1", content)
    content = re.sub(r"([\u4e00-\u9fa5])!\s*", r"\1！", content)
    content = re.sub(r"!\s*([\u4e00-\u9fa5])", r"！\1", content)

    # 英文句号（排除如 3.14 等数字情况，在中文语境下转为中文句号）
    content = re.sub(r"([\u4e00-\u9fa5”’])\.\s*", r"\1。", content)
    content = re.sub(r"\.\s*([\u4e00-\u9fa5“‘])", r"。\1", content)
    content = re.sub(r"([\u4e00-\u9fa5])\.\s*$", r"\1。", content, flags=re.MULTILINE)

    # 英文冒号与分号（排除 12:30 等时间格式）
    content = re.sub(r"([\u4e00-\u9fa5]):\s*", r"\1：", content)
    content = re.sub(r":\s*([\u4e00-\u9fa5])", r"：\1", content)
    content = re.sub(r"([\u4e00-\u9fa5]);\s*", r"\1；", content)
    content = re.sub(r";\s*([\u4e00-\u9fa5])", r"；\1", content)

    # 4. 治理重复感叹号与问号
    content = re.sub(r"[！!]{2,}", "！", content)
    content = re.sub(r"[？?]{2,}", "？", content)
    # 疑问感叹连用规范为 ！？
    content = re.sub(r"[？?][！!]", "！？", content)
    content = re.sub(r"[！!][？?]", "！？", content)

    # 5. 治理逗号堆叠
    content = re.sub(r"[，,]{2,}", "，", content)
    content = re.sub(r"[。\.]{2,}", "。", content)

    # 6. 行级空白清理与多余空行折叠
    lines = [line.rstrip() for line in content.splitlines()]
    cleaned_lines = []
    blank_count = 0
    for line in lines:
        if not line.strip():
            blank_count += 1
            if blank_count <= 1:  # 最多保留一个空行
                cleaned_lines.append("")
        else:
            blank_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip("\r\n")
