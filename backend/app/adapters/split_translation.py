"""
Split long Chinese translation segments at sentence boundaries for more natural TTS.

Each segment whose dst text contains multiple sentences (split by 。！？；)
is divided into sub-segments with timing allocated proportionally by character count.

Also validates that translated text can fit within its time slot to prevent audio truncation.
Segments that are too long are split further (at commas if needed) to ensure each
sub-segment has enough time for natural TTS delivery.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

_CHINESE_BREAK = re.compile(r"(。|！|？|；)")
_COMMA_BREAK = re.compile(r"(，|、|；)")
_MIN_CHARS = 15

# Speech rate estimation constants (synchronized with audio.py limits)
_CHINESE_SPEECH_RATE = 4.0       # chars/sec for Chinese TTS at normal pace
_NON_CHINESE_RATE = 8.0          # chars/sec for English/digits (spoken faster per char)
_MAX_SPEEDUP = 1.24              # from audio.py: BASE_FACTOR_MAX(1.15) * LOCAL_FACTOR_MAX(1.08)
_MAX_EFFECTIVE_RATE = _CHINESE_SPEECH_RATE * _MAX_SPEEDUP  # ~5.0 chars/sec effective max

logger = logging.getLogger(__name__)


def estimate_speech_seconds(text: str) -> float:
    """Estimate spoken duration for mixed Chinese/English text.

    Chinese characters are the primary metric (~250ms each),
    non-Chinese chars (English, digits, punctuation) are faster.
    """
    if not text:
        return 0.0
    chinese = sum(1 for c in text if '一' <= c <= '鿿')
    other = len(text) - chinese
    return chinese / _CHINESE_SPEECH_RATE + other / _NON_CHINESE_RATE


def would_truncate(dst: str, start_time: float, end_time: float) -> tuple[bool, float]:
    """Check if translated text fits its time slot (accounting for max speedup).

    Returns (will_truncate, ratio) where ratio > 1.0 means truncation will occur.
    """
    available_ms = end_time - start_time
    if available_ms <= 0 or not dst:
        return True, float('inf')
    needed = estimate_speech_seconds(dst)
    effective_available = (available_ms / 1000.0) * _MAX_SPEEDUP
    if effective_available <= 0:
        return True, float('inf')
    ratio = needed / effective_available
    return ratio > 1.0, ratio


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


def _split_at_commas(text: str) -> list[str]:
    """Fallback: split at Chinese commas for long segments without sentence breaks."""
    if len(text) < _MIN_CHARS:
        return [text]
    parts = _COMMA_BREAK.split(text)
    segments: list[str] = []
    buf = ""
    for i in range(0, len(parts) - 1, 2):
        buf += parts[i] + (parts[i + 1] if i + 1 < len(parts) else "")
        if len(buf.strip()) >= 6:
            segments.append(buf.strip())
            buf = ""
    tail = buf.strip()
    if tail:
        segments.append(tail)
    if not segments:
        segments = [text]
    return segments


def _shorten_text(text: str, target_chars: int, time_s: float) -> str:
    """Shorten verbose Chinese text to fit within time constraints.

    Uses safe removals: modal particles, redundant adverbs, filler phrases.
    Falls back to truncating the longest phrases if still too long.
    """
    if estimate_speech_seconds(text) * _MAX_SPEEDUP <= time_s:
        return text

    # Shorten directly when text is too long — remove common filler words
    # that don't carry meaning
    removals = [
        (r"其实", ""),      # "actually" — often filler
        (r"所以呢", "所以"),  # "so then" → "so"
        (r"那么", ""),       # "well/then" — often filler at start
        (r"就是说", "即"),   # "that is to say" → "i.e."
        (r"基本上", ""),    # "basically" — filler
        (r"嗯,?", ""),     # "um" — filler
        (r"哦,?", ""),     # "oh" — filler
        (r"的啊", "的"),
        (r"了吗", "了"),
        (r"的呢", "的"),
        (r"非常 ", ""),
        (r" 非常", ""),
        (r"一个 ", " "),
        (r" 一个", ""),
        (r"的 ", " "),  # shorten by removing possessive/descriptive 的 where possible
        (r"在 ", ""),
    ]
    shortened = text
    for pattern, replacement in removals:
        shortened = re.sub(pattern, replacement, shortened)

    if estimate_speech_seconds(shortened) * _MAX_SPEEDUP <= time_s:
        return shortened

    # If still too long and we have a long tail, trim it
    # Better to have a slightly shortened sentence than truncated audio
    max_safe_chars = int(time_s * _CHINESE_SPEECH_RATE * _MAX_SPEEDUP)
    if max_safe_chars < len(shortened):
        # Try to find a good break point near the limit
        break_chars = max_safe_chars - 5
        if break_chars > 10:
            shortened = shortened[:break_chars].rstrip("，、；。！？，") + "。"
            return shortened

    return shortened


def _src_for_dst(original_src: str, original_dst: str, sub_dst: str) -> str:
    """Estimate the src text corresponding to a sub-dst by proportional length."""
    if not original_dst or not original_src:
        return ""
    ratio = len(sub_dst) / len(original_dst) if original_dst else 0
    src_chars = max(1, int(len(original_src) * ratio))
    mid = int(len(original_src) / 2)
    half = int(src_chars / 2)
    start = max(0, mid - half)
    end = min(len(original_src), start + src_chars)
    return original_src[start:end]


def split_translation(translation_file: Path) -> Path:
    """Split long translation segments and validate timing.

    Returns the path to the (possibly modified) translation file.
    Warnings are logged for segments that may still be truncated.
    """
    data = json.loads(translation_file.read_text(encoding="utf-8"))
    translation = data["translation"]

    total_segments = len(translation)
    truncated_count = 0
    split_count = 0

    new_translation: list[dict] = []
    for item in translation:
        start = int(item["start_time"])
        end = int(item["end_time"])
        duration = end - start
        src = item.get("src", "")
        dst = item.get("dst") or item.get("zh", "")

        # Check if the original segment would be truncated
        orig_will_truncate, orig_ratio = would_truncate(dst, start, end)
        if orig_will_truncate:
            truncated_count += 1
            if orig_ratio > 1.3:
                logger.warning(
                    "Segment [start=%.1fs] text is %.0f%% over time budget "
                    "(%.1fs needed, %.1fs available after speedup). "
                    "Text will be shortened to prevent audio cut-off: %s",
                    start / 1000.0,
                    (orig_ratio - 1) * 100,
                    estimate_speech_seconds(dst),
                    duration / 1000.0 * _MAX_SPEEDUP,
                    dst[:60],
                )

        # First try sentence-level splitting
        sentences = _split_dst(dst)

        # If no sentence breaks and segment is too long, try comma-splitting
        if len(sentences) <= 1 and orig_will_truncate:
            comma_parts = _split_at_commas(dst)
            if len(comma_parts) > 1:
                sentences = comma_parts

        if len(sentences) <= 1:
            # Single segment — shorten if it won't fit
            if orig_will_truncate:
                safe_time = duration / 1000.0
                max_safe_chars = int(safe_time * _MAX_EFFECTIVE_RATE)
                shortened = _shorten_text(dst, max_safe_chars, safe_time)
                if len(shortened) < len(dst):
                    item["dst"] = shortened
                    item["zh"] = shortened
                new_translation.append(item)
                continue

            new_translation.append(item)
            continue

        # Multiple sentences — split with proportional timing
        split_count += 1
        weights = [max(1, len(s)) for s in sentences]
        total_weight = sum(weights)
        cursor = start

        # Validate total fit — if overall text exceeds budget, shorten sub-segments
        time_budget_per_char = (duration * _MAX_SPEEDUP) / total_weight if total_weight > 0 else 0

        for i, sentence in enumerate(sentences):
            share = weights[i] / total_weight if total_weight > 0 else 1.0 / len(sentences)
            seg_end = cursor + int(duration * share)
            seg_duration_s = (seg_end - cursor) / 1000.0

            # Check if this sub-segment fits
            sub_will_truncate, _ = would_truncate(sentence, cursor, seg_end)
            if sub_will_truncate and seg_duration_s > 0.5:
                # Try to shorten the sub-segment
                sentence = _shorten_text(sentence, weights[i], seg_duration_s)

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

    elapsed = len(new_translation) - total_segments
    logger.info(
        "Translation check complete: %d segments, %d split, %d truncation warnings issued, %d new segments added",
        total_segments,
        split_count,
        truncated_count,
        elapsed,
    )
    return translation_file
