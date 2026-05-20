"""
CosyVoice2 adapter for OhMyDub.

Calls the CosyVoice bridge script via subprocess (separate venv)
to generate TTS audio with voice cloning.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _resolve_cosyvoice_root() -> Path:
    """Locate the CosyVoice project directory relative to the repo root."""
    repo_root = Path(__file__).resolve().parents[3]
    candidate = repo_root / "CosyVoice"
    if candidate.is_dir():
        return candidate
    env_path = os.getenv("COSYVOICE_ROOT")
    if env_path:
        return Path(env_path).resolve()
    raise RuntimeError(
        "Cannot find CosyVoice directory. "
        "Set COSYVOICE_ROOT environment variable to point to the CosyVoice project."
    )


def _cosyvoice_python(cosyvoice_root: Path) -> str:
    """Path to the Python interpreter (uses root .venv to avoid duplicate torch)."""
    repo_root = cosyvoice_root.parent
    root_venv = repo_root / ".venv" / "Scripts" / "python.exe"
    if root_venv.is_file():
        return str(root_venv)
    venv_python = cosyvoice_root / "venv" / "Scripts" / "python.exe"
    if venv_python.is_file():
        return str(venv_python)
    return sys.executable


def _log(msg: str) -> None:
    print(f"[cosyvoice] {msg}", file=sys.stderr, flush=True)


def generate_tts(translation_file: Path, vocals_dir: Path, session: Path) -> Path:
    output_dir = session / "segments" / "tts"
    output_dir.mkdir(parents=True, exist_ok=True)

    cosyvoice_root = _resolve_cosyvoice_root()
    bridge = cosyvoice_root / "_cosyvoice_bridge.py"
    if not bridge.is_file():
        raise RuntimeError(f"Bridge script not found: {bridge}")

    data = json.loads(translation_file.read_text(encoding="utf-8"))
    translation = data["translation"]

    model_dir = os.getenv("COSYVOICE_MODEL_DIR", r"D:\AI\YouDub-webui\checkpoints\CosyVoice-300M")
    use_fp16 = os.getenv("COSYVOICE_FP16", "true").lower() == "true"
    batch_timeout = int(os.getenv("COSYVOICE_TIMEOUT", "600"))

    # Build segment list
    segments = []
    for idx, item in enumerate(translation, start=1):
        output_file = output_dir / f"{idx:04d}.wav"
        if output_file.exists():
            continue

        ref_audio = vocals_dir / f"{idx:04d}.wav"
        if not ref_audio.is_file():
            continue

        dst_text = item.get("dst") or item.get("zh", "")
        if not dst_text.strip():
            continue

        src_text = item.get("src", "")
        src_lang = item.get("src_lang", "")
        dst_lang = item.get("dst_lang", "zh")

        segments.append({
            "index": idx,
            "text": dst_text,
            "src_lang": src_lang,
            "dst_lang": dst_lang,
            "prompt_text": src_text,
            "ref_audio": str(ref_audio.resolve()),
            "output": str(output_file.resolve()),
        })

    if not segments:
        return output_dir

    total = len(segments)
    timeout = int(os.getenv("COSYVOICE_TIMEOUT", "600"))
    _log(f"Generating {total} TTS segments with CosyVoice (single batch)")

    request = {
        "model_dir": model_dir,
        "segments": segments,
        "fp16": use_fp16,
        "load_jit": False,
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", encoding="utf-8", delete=False
    ) as f:
        json.dump(request, f, ensure_ascii=False)
        req_path = f.name

    try:
        python_exe = _cosyvoice_python(cosyvoice_root)
        result = subprocess.run(
            [python_exe, str(bridge), req_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"cosyvoice bridge failed (exit {result.returncode}):\n"
                f"{result.stderr[:500] if result.stderr else result.stdout[:500]}"
            )

        output = json.loads(result.stdout.strip())
        if not output.get("success"):
            raise RuntimeError(f"cosyvoice bridge error: {output.get('error', 'unknown')}")

        errors = [r for r in output.get("results", []) if not r.get("success")]
        if errors:
            first = errors[0]
            raise RuntimeError(
                f"TTS segment {first['index']} failed: {first.get('error', 'unknown')}"
            )

        success_count = len([r for r in output.get("results", []) if r.get("success")])
        _log(f"Done: {success_count}/{total} segments OK")

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"cosyvoice bridge returned invalid JSON: {exc}\n"
            f"stderr: {result.stderr[:500]}"
        )
    finally:
        try:
            os.unlink(req_path)
        except OSError:
            pass

    _log("All CosyVoice TTS segments generated")
    return output_dir
