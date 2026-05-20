"""
OhMyDub bridge script for CosyVoice2.

Called via subprocess from the main backend. Loads the model once,
generates TTS for all segments in a batch, then exits.

Usage:
    python cosyvoice_bridge.py <request.json>
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# --- Path setup: must happen before cosyvoice imports ---
# cosyvoice_root is passed in by the adapter so the subprocess can
# locate the CosyVoice package and its third_party/Matcha-TTS dependency
# regardless of where this bridge script lives on disk.
_req_path = sys.argv[1]
with open(_req_path, "r", encoding="utf-8") as _f:
    _request = json.load(_f)
_cosyvoice_root = _request.get("cosyvoice_root", "")
if _cosyvoice_root:
    sys.path.insert(0, _cosyvoice_root)
    sys.path.append(os.path.join(_cosyvoice_root, "third_party", "Matcha-TTS"))
# ----------------------------------------------------------

import torch
import torchaudio
from cosyvoice.cli.cosyvoice import AutoModel

# CosyVoice language tag mapping for cross-lingual mode
LANG_TAGS = {
    "zh": "<|zh|>",
    "en": "<|en|>",
    "ja": "<|ja|>",
    "ko": "<|ko|>",
    "yue": "<|yue|>",
}

# Per-segment timeout (seconds) — a segment taking longer is assumed hung
SEGMENT_TIMEOUT = int(os.getenv("COSYVOICE_SEGMENT_TIMEOUT", "120"))


def _map_lang(lang_code: str) -> str:
    """Map a language code to its CosyVoice cross-lingual tag."""
    return LANG_TAGS.get(lang_code, f"<|{lang_code}|>")


def _generate_segment(model, text: str, ref_audio: str, output_path: str) -> None:
    """Run CosyVoice cross-lingual inference for one segment."""
    for result in model.inference_cross_lingual(
        text, ref_audio, stream=False, speed=1.0
    ):
        speech = result["tts_speech"]
        # Ensure PCM int16 WAV (format 1) — float WAVs (format 3) can't be read
        # by Python's wave module and cause "unknown format: 3" in later stages.
        if speech.dtype in (torch.float16, torch.float32, torch.float64, torch.bfloat16):
            speech = (speech * 32767).clamp(-32768, 32767).to(torch.int16)
        torchaudio.save(output_path, speech, model.sample_rate)


def main() -> None:
    # Request already read at module level for path setup; reuse _request
    request = _request  # noqa: F811

    model_dir = request["model_dir"]
    segments = request["segments"]
    fp16 = request.get("fp16", True)
    load_jit = request.get("load_jit", True)
    worker_id = request.get("worker_id", 0)
    nfe = request.get("nfe", None)  # optional NFE override for flow matching

    tag = f"[cosyvoice:{worker_id}]"

    # Load model (fp16 flag passed to AutoModel/CosyVoice2 for autocast)
    print(f"{tag} Loading model from {model_dir} (fp16={fp16}, load_jit={load_jit})...", file=sys.stderr, flush=True)
    model = AutoModel(model_dir=model_dir, fp16=fp16, load_jit=load_jit)

    # Attempt NFE reduction (experimental — only works for models that expose it)
    if nfe is not None:
        for attr in ("nfe",):
            target = getattr(model.flow, "model", None)
            if target is not None and hasattr(target, attr):
                old = getattr(target, attr)
                setattr(target, attr, nfe)
                print(f"{tag} Flow {attr}: {old} -> {nfe}", file=sys.stderr, flush=True)
                break
            if hasattr(model.flow, attr):
                old = getattr(model.flow, attr)
                setattr(model.flow, attr, nfe)
                print(f"{tag} Flow {attr}: {old} -> {nfe}", file=sys.stderr, flush=True)
                break

    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True

    print(f"{tag} Model loaded, processing {len(segments)} segments...", file=sys.stderr, flush=True)

    results = []
    for i, seg in enumerate(segments, start=1):
        idx = seg["index"]
        text = seg["text"]
        ref_audio = seg["ref_audio"]
        output_path = seg["output"]
        src_lang = seg.get("src_lang", "")
        dst_lang = seg.get("dst_lang", "zh")
        prompt_text = seg.get("prompt_text", "")

        if not os.path.isfile(ref_audio):
            results.append({"index": idx, "success": False, "error": f"Reference audio not found: {ref_audio}"})
            continue

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        try:
            print(f"{tag} [{i}/{len(segments)}] Generating segment {idx}...", file=sys.stderr, flush=True)

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_generate_segment, model, text, ref_audio, output_path)
                try:
                    future.result(timeout=SEGMENT_TIMEOUT)
                    results.append({"index": idx, "success": True})
                except concurrent.futures.TimeoutError:
                    print(f"{tag} [{i}/{len(segments)}] Segment {idx} TIMEOUT after {SEGMENT_TIMEOUT}s", file=sys.stderr, flush=True)
                    results.append({"index": idx, "success": False, "error": f"Segment generation timed out after {SEGMENT_TIMEOUT}s"})
                except Exception as exc:
                    print(f"{tag} [{i}/{len(segments)}] Segment {idx} FAILED: {exc}", file=sys.stderr, flush=True)
                    results.append({"index": idx, "success": False, "error": str(exc)})
        except Exception as exc:
            print(f"{tag} [{i}/{len(segments)}] Segment {idx} FAILED: {exc}", file=sys.stderr, flush=True)
            results.append({"index": idx, "success": False, "error": str(exc)})

        # Clear CUDA cache between segments to prevent VRAM fragmentation
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    output = {"success": True, "results": results}
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
