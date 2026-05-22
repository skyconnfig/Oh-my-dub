"""
SuperTonic TTS adapter for OhMyDub.

SuperTonic is a lightweight on-device TTS engine (~99M params) powered by
ONNX Runtime. It runs on CPU and supports 31 languages with predefined
voice styles (F1-F5, M1-M5).

Limitations:
  - No voice cloning — uses predefined voice styles (not reference audio)
  - No GPU support yet (CPU-only via onnxruntime)
  - Chinese (zh) not natively supported; falls back to language-agnostic mode
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import soundfile as sf

_TTS = None
_STYLE = None

# SuperTonic language codes — maps our pipeline codes to SuperTonic codes
_LANG_MAP = {
    "en": "en",
    "zh": "na",         # Chinese not natively supported; use language-agnostic
    "ja": "ja",
    "ko": "ko",
    "ar": "ar",
    "bg": "bg",
    "cs": "cs",
    "da": "da",
    "de": "de",
    "el": "el",
    "es": "es",
    "et": "et",
    "fi": "fi",
    "fr": "fr",
    "hi": "hi",
    "hr": "hr",
    "hu": "hu",
    "id": "id",
    "it": "it",
    "lt": "lt",
    "lv": "lv",
    "nl": "nl",
    "pl": "pl",
    "pt": "pt",
    "ro": "ro",
    "ru": "ru",
    "sk": "sk",
    "sl": "sl",
    "sv": "sv",
    "tr": "tr",
    "uk": "uk",
    "vi": "vi",
}


def _load_model():
    global _TTS, _STYLE
    if _TTS is None:
        # Respect HF offline mode from .env — HuggingFace Hub may be unavailable
        from supertonic import TTS

        _TTS = TTS(auto_download=True)
    if _STYLE is None:
        voice = os.getenv("SUPERTONIC_VOICE", "M1")
        _STYLE = _TTS.get_voice_style(voice_name=voice)
    return _TTS, _STYLE


def _map_lang(lang_code: str) -> str:
    return _LANG_MAP.get(lang_code, lang_code)


def generate_tts(translation_file: Path, vocals_dir: Path, session: Path) -> Path:
    output_dir = session / "segments" / "tts"
    output_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(translation_file.read_text(encoding="utf-8"))

    tts, style = _load_model()
    total_steps = int(os.getenv("SUPERTONIC_STEPS", "8"))
    speed = float(os.getenv("SUPERTONIC_SPEED", "1.05"))

    for index, item in enumerate(data["translation"], start=1):
        output_file = output_dir / f"{index:04d}.wav"
        if output_file.exists():
            continue

        text = item.get("dst") or item.get("zh", "")
        if not text.strip():
            continue

        dst_lang = _map_lang(item.get("dst_lang", "zh"))

        wav, _ = tts.synthesize(
            text,
            lang=dst_lang,
            voice_style=style,
            total_steps=total_steps,
            speed=speed,
        )
        sf.write(output_file, wav[0], tts.sample_rate, subtype="PCM_16")

    return output_dir
