from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]

# Auto-detect ffmpeg in the project directory or common install paths
_FFMPEG_CANDIDATES = [
    REPO_ROOT / "ffmpeg" / "ffmpeg-8.0.1-essentials_build" / "bin",
    REPO_ROOT / "ffmpeg" / "ffmpeg-8.1.1-full_build" / "bin",
    Path(os.environ.get("ProgramW6432", "C:\\Program Files")) / "ffmpeg" / "bin",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages" / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe" / "ffmpeg-8.1.1-full_build" / "bin",
]
for _p in _FFMPEG_CANDIDATES:
    if _p.joinpath("ffmpeg.exe").exists():
        os.environ.setdefault("PATH", "")
        os.environ["PATH"] = str(_p) + os.pathsep + os.environ["PATH"]
        break
DATA_DIR = REPO_ROOT / "data"
COOKIE_DIR = DATA_DIR / "cookies"
DB_PATH = DATA_DIR / "ohmy-dub.sqlite"
YOUTUBE_COOKIE_PATH = COOKIE_DIR / "youtube.txt"
_wf = os.getenv("WORKFOLDER", "")
WORKFOLDER = (REPO_ROOT / _wf if _wf and not Path(_wf).is_absolute() else Path(_wf or str(REPO_ROOT / "workfolder"))).resolve()
LOG_DIR = DATA_DIR / "logs"
MODEL_CACHE_DIR = Path(os.getenv("MODEL_CACHE_DIR", str(DATA_DIR / "modelscope"))).expanduser()


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    COOKIE_DIR.mkdir(parents=True, exist_ok=True)
    WORKFOLDER.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def device() -> str:
    configured = os.getenv("DEVICE") or os.getenv("CUDA_DEVICE")
    if configured:
        return configured
    return "cuda"


def openai_defaults() -> dict[str, str]:
    return {
        "base_url": os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": os.getenv("OPENAI_MODEL") or os.getenv("OPENAI_MODEL_NAME") or "gpt-4o-mini",
        "translate_concurrency": os.getenv("OPENAI_TRANSLATE_CONCURRENCY", "50"),
    }


def tts_engine() -> str:
    return (os.getenv("TTS_ENGINE") or "voxcpm").lower()


def tts_engine_label(engine: str | None = None) -> str:
    labels = {"voxcpm": "VoxCPM", "gpt_sovits": "GPT-SoVITS", "indextts": "IndexTTS", "cosyvoice": "CosyVoice2"}
    return labels.get(engine or tts_engine(), engine or tts_engine())


def ytdlp_defaults() -> dict[str, str]:
    return {
        "proxy_port": os.getenv("YTDLP_PROXY_PORT", ""),
    }
