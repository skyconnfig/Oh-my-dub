from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import numpy as np
import soundfile as sf
from pydub import AudioSegment

_API_URL: str | None = None

# GPT-SoVITS v2 generation defaults for natural speech
_DEFAULT_TEMPERATURE = 0.6
_DEFAULT_TOP_P = 0.7
_DEFAULT_TOP_K = 10


def _api_url() -> str:
    global _API_URL
    if _API_URL is None:
        _API_URL = os.getenv("GPT_SOVITS_API_URL", "http://localhost:9880").rstrip("/")
    return _API_URL


def _index_closest(sorted_durs: list[tuple[int, Path]], target_dur: float) -> int:
    """Find index of the duration closest to target_dur in a sorted list."""
    target = target_dur
    lo, hi = 0, len(sorted_durs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if sorted_durs[mid][0] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    # Check lo and hi for closest
    candidates = [i for i in (lo, hi) if 0 <= i < len(sorted_durs)]
    return min(candidates, key=lambda i: abs(sorted_durs[i][0] - target))


def _normalize_gain(wav_path: Path, target_dbfs: float = -20.0) -> None:
    """Normalize a wav file's peak gain in-place for consistent GPT-SoVITS input."""
    try:
        y, sr = sf.read(str(wav_path))
        if len(y) == 0:
            return
        peak = np.max(np.abs(y))
        if peak < 1e-6:
            return
        current_dbfs = 20 * np.log10(peak)
        gain_db = target_dbfs - current_dbfs
        if abs(gain_db) > 1.0:
            gain_linear = 10 ** (gain_db / 20)
            sf.write(str(wav_path), (y * gain_linear).astype(y.dtype), sr)
    except Exception:
        pass  # Non-critical — skip normalization on error


def _build_reference_index(vocals_dir: Path, min_ms: int, max_ms: int) -> list[tuple[int, Path]]:
    """Build a sorted list of (duration_ms, path) for all usable reference segments."""
    index: list[tuple[int, Path]] = []
    for path in sorted(vocals_dir.glob("*.wav")):
        try:
            dur = len(AudioSegment.from_file(path))
        except Exception:
            continue
        if dur < min_ms:
            continue
        index.append((dur, path))
    index.sort(key=lambda x: x[0])
    return index


def _pick_reference(
    target_segment_index: int,
    vocals_dir: Path,
    ref_index: list[tuple[int, Path]],
    min_ms: int,
    max_ms: int,
) -> Path | None:
    """Pick the best reference for a given TTS segment.

    Strategy: prefer the segment-specific vocal reference if it falls in the
    acceptable duration range.  Otherwise, find the reference whose duration
    is *closest* to the segment's expected vocal duration (from the original),
    to keep voice timbre consistent.
    """
    specific = vocals_dir / f"{target_segment_index:04d}.wav"
    if specific.exists():
        try:
            dur = len(AudioSegment.from_file(specific))
        except Exception:
            dur = 0
        if min_ms <= dur <= max_ms:
            return specific

    if not ref_index:
        return None

    # Fallback: pick the global reference whose duration is closest to median
    # of the index, which tends to be the most "typical" reference.
    median_idx = len(ref_index) // 2
    median_dur = ref_index[median_idx][0]
    best_idx = _index_closest(ref_index, median_dur)
    return ref_index[best_idx][1]


def generate_tts(translation_file: Path, vocals_dir: Path, session: Path) -> Path:
    # Ensure all paths are absolute — GPT-SoVITS API runs from a different CWD
    session = session.resolve()
    vocals_dir = vocals_dir.resolve()
    translation_file = translation_file.resolve()
    output_dir = session / "segments" / "tts"
    output_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(translation_file.read_text(encoding="utf-8"))
    base_url = _api_url()
    min_ms = int(os.getenv("GPT_SOVITS_REF_MIN_MS", "2000"))
    max_ms = int(os.getenv("GPT_SOVITS_REF_MAX_MS", "15000"))
    ref_index = _build_reference_index(vocals_dir, min_ms, max_ms)

    temperature = float(os.getenv("GPT_SOVITS_TEMPERATURE", str(_DEFAULT_TEMPERATURE)))
    top_p = float(os.getenv("GPT_SOVITS_TOP_P", str(_DEFAULT_TOP_P)))
    top_k = int(os.getenv("GPT_SOVITS_TOP_K", str(_DEFAULT_TOP_K)))
    enable_normalize = os.getenv("GPT_SOVITS_NORMALIZE_REF", "true").lower() == "true"

    for index, item in enumerate(data["translation"], start=1):
        output_file = output_dir / f"{index:04d}.wav"
        if output_file.exists():
            continue

        reference = _pick_reference(index, vocals_dir, ref_index, min_ms, max_ms)
        if reference is None:
            continue

        # Normalize reference audio for consistent input level
        if enable_normalize:
            _normalize_gain(reference)

        dst_text = item.get("dst") or item.get("zh", "")
        if not dst_text.strip():
            continue

        payload = {
            "text": dst_text,
            "text_lang": item.get("dst_lang", "zh"),
            "ref_audio_path": str(reference.resolve()),
            "prompt_text": item.get("src", ""),
            "prompt_lang": item.get("src_lang", "en"),
            "media_type": "wav",
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "cut": "cut1",
        }

        try:
            resp = httpx.post(
                f"{base_url}/tts",
                json=payload,
                timeout=int(os.getenv("GPT_SOVITS_TIMEOUT", "120")),
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"GPT-SoVITS API error (HTTP {resp.status_code}): {resp.text}"
                )
            output_file.write_bytes(resp.content)
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to GPT-SoVITS API at {base_url}. "
                "Make sure GPT-SoVITS is running: python api_v2.py"
            )

    return output_dir
