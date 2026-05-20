"""
CosyVoice2 adapter for OhMyDub.

Calls the CosyVoice bridge script via subprocess (separate venv)
to generate TTS audio with voice cloning.

Supports parallel workers — splits segments into chunks and runs
concurrent bridge subprocesses to utilize GPU VRAM efficiently.
"""
from __future__ import annotations

import concurrent.futures
import json
import math
import os
import shutil
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


def _split_into_chunks(segments: list, n_chunks: int) -> list[list]:
    """Split a list into n_chunks contiguous chunks (last may be smaller)."""
    if n_chunks < 1:
        n_chunks = 1
    n = len(segments)
    if n == 0:
        return []
    if n_chunks >= n:
        return [[s] for s in segments]
    chunk_size = math.ceil(n / n_chunks)
    return [segments[i : i + chunk_size] for i in range(0, n, chunk_size)]


def _run_bridge_worker(
    python_exe: str, bridge: str, req_path: str, timeout: int, worker_id: int
) -> dict:
    """Execute a single bridge worker subprocess and return parsed output."""
    result = subprocess.run(
        [python_exe, bridge, req_path],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"worker-{worker_id} bridge failed (exit {result.returncode}):\n"
            f"{result.stderr[:500] if result.stderr else result.stdout[:500]}"
        )
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"worker-{worker_id} bridge returned invalid JSON: {exc}\n"
            f"stderr: {result.stderr[:500]}"
        )
    if not output.get("success"):
        raise RuntimeError(
            f"worker-{worker_id} bridge error: {output.get('error', 'unknown')}"
        )
    return output


def generate_tts(translation_file: Path, vocals_dir: Path, session: Path) -> Path:
    output_dir = session / "segments" / "tts"
    output_dir.mkdir(parents=True, exist_ok=True)

    cosyvoice_root = _resolve_cosyvoice_root()
    bridge = Path(__file__).resolve().parent / "cosyvoice_bridge.py"
    if not bridge.is_file():
        raise RuntimeError(f"Bridge script not found: {bridge}")

    data = json.loads(translation_file.read_text(encoding="utf-8"))
    translation = data["translation"]

    model_dir = os.getenv("COSYVOICE_MODEL_DIR", r"D:\AI\YouDub-webui\checkpoints\CosyVoice-300M")
    use_fp16 = os.getenv("COSYVOICE_FP16", "true").lower() == "true"
    worker_count = int(os.getenv("COSYVOICE_WORKERS", "2"))
    nfe = os.getenv("COSYVOICE_NFE", None)  # optional NFE override (e.g. "6")
    timeout = int(os.getenv("COSYVOICE_TIMEOUT", "1800"))
    python_exe = _cosyvoice_python(cosyvoice_root)

    # Build list of unfinished segments
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

    # Split into chunks for parallel workers
    chunks = _split_into_chunks(segments, worker_count)
    actual_workers = len(chunks)
    _log(
        f"Generating {total} TTS segments with {actual_workers} worker(s) "
        f"({[len(c) for c in chunks]})"
    )

    # Prepare base request template
    base_request = {
        "model_dir": model_dir,
        "segments": [],  # filled per chunk
        "fp16": use_fp16,
        "load_jit": False,
        "cosyvoice_root": str(cosyvoice_root.resolve()),
    }
    if nfe is not None:
        base_request["nfe"] = int(nfe)

    # Write request files and launch concurrent workers
    work_dir = Path(tempfile.mkdtemp(prefix="cosyvoice_"))
    try:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=actual_workers
        ) as executor:
            futures = []
            for wid, chunk in enumerate(chunks):
                if not chunk:
                    continue
                req = {**base_request, "segments": chunk, "worker_id": wid}
                req_file = work_dir / f"request_{wid}.json"
                req_file.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")
                futures.append(
                    executor.submit(
                        _run_bridge_worker,
                        python_exe,
                        str(bridge),
                        str(req_file),
                        timeout,
                        wid,
                    )
                )

            # Collect results — raise first error found
            errors = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    output = future.result()
                    bad = [
                        r for r in output.get("results", [])
                        if not r.get("success")
                    ]
                    if bad:
                        first = bad[0]
                        errors.append(
                            f"segment {first['index']}: {first.get('error', 'unknown')}"
                        )
                except Exception as exc:
                    errors.append(str(exc))

            if errors:
                raise RuntimeError(
                    f"TTS generation failed ({len(errors)} error(s)):\n"
                    + "\n".join(errors)
                )

        _log(f"Done: {total}/{total} segments OK")

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    _log("All CosyVoice TTS segments generated")
    return output_dir
