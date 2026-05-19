from __future__ import annotations

from dataclasses import dataclass

from .config import tts_engine, tts_engine_label


@dataclass(frozen=True)
class StageSpec:
    name: str
    label: str


def get_stages(engine: str | None = None) -> tuple[StageSpec, ...]:
    if engine is None:
        engine = tts_engine()
    return (
        StageSpec("download", "Download"),
        StageSpec("separate", "Demucs"),
        StageSpec("asr", "Whisper"),
        StageSpec("asr_fix", "Split sentences"),
        StageSpec("translate", "Translate"),
        StageSpec("split_audio", "Split audio"),
        StageSpec("tts", tts_engine_label(engine)),
        StageSpec("merge_audio", "Merge audio"),
        StageSpec("merge_video", "Merge video"),
    )


STAGES: tuple[StageSpec, ...] = get_stages()
STAGE_NAMES = tuple(stage.name for stage in STAGES)
