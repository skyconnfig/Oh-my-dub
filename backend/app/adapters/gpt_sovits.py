from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
from pydub import AudioSegment

_API_URL: str | None = None


def _api_url() -> str:
    global _API_URL
    if _API_URL is None:
        _API_URL = os.getenv("GPT_SOVITS_API_URL", "http://localhost:9880").rstrip("/")
    return _API_URL


def _find_reference(vocals_dir: Path, min_ms: int, max_ms: int) -> Path | None:
    files = sorted(vocals_dir.glob("*.wav"))
    for path in files:
        dur = len(AudioSegment.from_file(path))
        if min_ms <= dur <= max_ms:
            return path
    return None


def generate_tts(translation_file: Path, vocals_dir: Path, session: Path) -> Path:
    # Ensure all paths are absolute — GPT-SoVITS API runs from a different CWD
    session = session.resolve()
    vocals_dir = vocals_dir.resolve()
    translation_file = translation_file.resolve()
    output_dir = session / "segments" / "tts"
    output_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(translation_file.read_text(encoding="utf-8"))
    base_url = _api_url()
    min_ms = int(os.getenv("GPT_SOVITS_REF_MIN_MS", "3000"))
    max_ms = int(os.getenv("GPT_SOVITS_REF_MAX_MS", "10000"))
    fallback = _find_reference(vocals_dir, min_ms, max_ms)

    for index, item in enumerate(data["translation"], start=1):
        output_file = output_dir / f"{index:04d}.wav"
        if output_file.exists():
            continue

        reference = vocals_dir / f"{index:04d}.wav"
        if not reference.exists():
            if fallback is None:
                continue
            reference = fallback
        else:
            dur = len(AudioSegment.from_file(reference))
            if not (min_ms <= dur <= max_ms):
                if fallback is None:
                    continue
                reference = fallback

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
