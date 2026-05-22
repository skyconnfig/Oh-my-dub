"""
MeloTTS adapter for OhMyDub.

MeloTTS is a lightweight TTS engine by MyShell, supporting Chinese (ZH),
English (EN), Japanese (JP), Korean (KR), French (FR), and Spanish (ES).

Chinese model uses ZH_MIX_EN mode — handles mixed Chinese+English text naturally.
Each language requires its own model. Default is ZH (Chinese).

Supports 256 preset speaker IDs (0-255) depending on the model.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure MeloTTS source is on the Python path
_MELO_SRC = Path(__file__).resolve().parents[3] / "MeloTTS"
if str(_MELO_SRC) not in sys.path:
    sys.path.insert(0, str(_MELO_SRC))

_TTS = None


def _load_model():
    global _TTS
    if _TTS is None:
        language = os.getenv("MELOTTS_LANGUAGE", "ZH")
        from melo.api import TTS

        _TTS = TTS(language=language, device=os.getenv("DEVICE", "auto"))
    return _TTS


def generate_tts(translation_file: Path, vocals_dir: Path, session: Path) -> Path:
    output_dir = session / "segments" / "tts"
    output_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(translation_file.read_text(encoding="utf-8"))

    model = _load_model()
    speaker_id = int(os.getenv("MELOTTS_SPEAKER_ID", "0"))
    speed = float(os.getenv("MELOTTS_SPEED", "1.0"))

    for index, item in enumerate(data["translation"], start=1):
        output_file = output_dir / f"{index:04d}.wav"
        if output_file.exists():
            continue

        text = item.get("dst") or item.get("zh", "")
        if not text.strip():
            continue

        model.tts_to_file(text, speaker_id=speaker_id, output_path=str(output_file), speed=speed, quiet=True)

    return output_dir
