"""
Split long Chinese translation segments at sentence boundaries for more natural TTS.

Each segment whose dst text contains multiple sentences (split by 。！？；)
is divided into sub-segments with timing allocated proportionally by character count.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_CHINESE_BREAK = re.compile(r"(。|！|？|；)")
_MIN_CHARS = 15  # minimum Chinese characters before attempting to split


def _split_dst(text: str) -> list[str]:
    """Split Chinese text at sentence boundaries, keeping the delimiter."""
    if len(text) < _MIN_CHARS:
        return [text]
    parts = _CHINESE_BREAK.split(text)
    sentences: list[str] = []
    buf = ""
    for i in range(0, len(parts) - 1, 2):
        buf += parts[i] + (parts[i + 1] if i + 1 < len(parts) else "")
        candidate = buf.strip()
        if len(candidate) >= 6 or i == len(parts) - 2:
            sentences.append(candidate)
            buf = ""
    tail = (buf + (parts[-1] if len(parts) % 2 == 1 else "")).strip()
    if tail:
        if len(sentences) == 0:
            return [tail]
        sentences[-1] = (sentences[-1] + tail).strip()
    elif not sentences:
        sentences = [text]
    return [s for s in sentences if s]


def _src_for_dst(original_src: str, original_dst: str, sub_dst: str) -> str:
    """Estimate the src text corresponding to a sub-dst by proportional length."""
    if not original_dst or not original_src:
        return ""
    ratio = len(sub_dst) / len(original_dst)
    src_chars = max(1, int(len(original_src) * ratio))
    # take a sliding window of the original src centered by ratio
    mid = int(len(original_src) / 2)
    half = int(src_chars / 2)
    start = max(0, mid - half)
    end = min(len(original_src), start + src_chars)
    return original_src[start:end]


def split_translation(translation_file: Path) -> Path:
    data = json.loads(translation_file.read_text(encoding="utf-8"))
    translation = data["translation"]

    new_translation: list[dict] = []
    for item in translation:
        start = int(item["start_time"])
        end = int(item["end_time"])
        duration = end - start
        src = item.get("src", "")
        dst = item.get("dst") or item.get("zh", "")
        sentences = _split_dst(dst)
        if len(sentences) <= 1:
            new_translation.append(item)
            continue

        weights = [max(1, len(s)) for s in sentences]
        total_weight = sum(weights)
        cursor = start
        for i, sentence in enumerate(sentences):
            share = weights[i] / total_weight if total_weight > 0 else 1.0 / len(sentences)
            seg_end = cursor + int(duration * share)
            sub_src = _src_for_dst(src, dst, sentence)
            new_translation.append({
                "src": sub_src,
                "dst": sentence,
                "zh": sentence,
                "src_lang": item.get("src_lang", "en"),
                "dst_lang": item.get("dst_lang", "zh"),
                "start_time": cursor,
                "end_time": seg_end,
                "speaker": item.get("speaker", "1"),
            })
            cursor = seg_end

    data["translation"] = new_translation
    translation_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return translation_file
