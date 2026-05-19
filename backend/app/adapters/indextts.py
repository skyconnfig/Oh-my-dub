"""
IndexTTS2 adapter for OhMyDub.

Calls the indextts bridge script via subprocess (separate venv)
to generate TTS audio with voice cloning.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _resolve_index_root() -> Path:
    """Locate the index-tts project directory relative to the repo root."""
    repo_root = Path(__file__).resolve().parents[3]
    candidate = repo_root / "index-tts"
    if candidate.is_dir():
        return candidate
    # Fallback: environment override
    env_path = os.getenv("INDEXTTS_ROOT")
    if env_path:
        return Path(env_path).resolve()
    raise RuntimeError(
        "Cannot find index-tts directory. "
        "Set INDEXTTS_ROOT environment variable to point to the index-tts project."
    )


def _indextts_python(index_root: Path) -> str:
    """Path to the Python interpreter inside the index-tts venv."""
    venv_python = index_root / ".venv" / "Scripts" / "python.exe"
    if venv_python.is_file():
        return str(venv_python)
    # Fallback: system python (may work if indextts is installed globally)
    return sys.executable


def _log(msg: str) -> None:
    """Write a timestamped progress message to stderr so the backend can log it."""
    import sys
    print(f"[indextts] {msg}", file=sys.stderr, flush=True)


def generate_tts(translation_file: Path, vocals_dir: Path, session: Path) -> Path:
    output_dir = session / "segments" / "tts"
    output_dir.mkdir(parents=True, exist_ok=True)

    index_root = _resolve_index_root()
    bridge = index_root / "_ohmy_bridge.py"
    if not bridge.is_file():
        raise RuntimeError(f"Bridge script not found: {bridge}")

    data = json.loads(translation_file.read_text(encoding="utf-8"))
    translation = data["translation"]

    model_dir = os.getenv("INDEXTTS_MODEL_DIR", str(index_root / "checkpoints"))
    use_fp16 = os.getenv("INDEXTTS_FP16", "true").lower() == "true"
    batch_timeout = int(os.getenv("INDEXTTS_TIMEOUT", "1800"))

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

        text_lang = item.get("dst_lang", "zh")
        segments.append({
            "index": idx,
            "text": dst_text,
            "text_lang": text_lang,
            "ref_audio": str(ref_audio.resolve()),
            "output": str(output_file.resolve()),
        })

    # If all segments already cached, nothing to do
    if not segments:
        return output_dir

    # Process in batches so each subprocess call finishes faster
    batch_size = int(os.getenv("INDEXTTS_BATCH_SIZE", "20"))
    total = len(segments)
    _log(f"Generating {total} TTS segments, batch_size={batch_size}")

    for batch_start in range(0, total, batch_size):
        batch = segments[batch_start:batch_start + batch_size]
        _log(f"Processing batch {batch_start // batch_size + 1}/{(total + batch_size - 1) // batch_size} "
             f"({len(batch)} segments, indices {batch[0]['index']}-{batch[-1]['index']})")

        request = {
            "model_dir": model_dir,
            "segments": batch,
            "fp16": use_fp16,
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        ) as f:
            json.dump(request, f, ensure_ascii=False)
            req_path = f.name

        try:
            python_exe = _indextts_python(index_root)
            result = subprocess.run(
                [python_exe, str(bridge), req_path],
                capture_output=True,
                text=True,
                timeout=batch_timeout,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"indextts bridge failed (exit {result.returncode}):\n"
                    f"{result.stderr[:500] if result.stderr else result.stdout[:500]}"
                )

            # Parse the JSON output
            output = json.loads(result.stdout.strip())
            if not output.get("success"):
                raise RuntimeError(f"indextts bridge error: {output.get('error', 'unknown')}")

            # Check for individual failures
            errors = [r for r in output.get("results", []) if not r.get("success")]
            if errors:
                first = errors[0]
                raise RuntimeError(
                    f"TTS segment {first['index']} failed: {first.get('error', 'unknown')}"
                )

            success_count = len([r for r in output.get("results", []) if r.get("success")])
            _log(f"Batch done: {success_count}/{len(batch)} segments OK")

        finally:
            try:
                os.unlink(req_path)
            except OSError:
                pass

    _log("All TTS segments generated")
    return output_dir
