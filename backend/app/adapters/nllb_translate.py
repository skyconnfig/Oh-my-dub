"""
Local EN→ZH translation using Meta NLLB-200-distilled-600M.

Runs entirely on GPU with no API dependency.  Model is downloaded from
HuggingFace on first use (~1.2 GB).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import torch

log = logging.getLogger(__name__)

_MODEL = None
_TOKENIZER = None

MODEL_ID = os.getenv("NLLB_MODEL_ID", "facebook/nllb-200-distilled-600M")
SRC_LANG = "eng_Latn"
DST_LANG = "zho_Hans"
BATCH_SIZE = int(os.getenv("NLLB_BATCH_SIZE", "16"))
MAX_LENGTH = int(os.getenv("NLLB_MAX_LENGTH", "200"))


def _load_model():
    global _MODEL, _TOKENIZER
    if _MODEL is not None:
        return _MODEL, _TOKENIZER

    from transformers import AutoModelForSeq2SeqLM, NllbTokenizer

    log.info("Loading NLLB-200 from %s ...", MODEL_ID)
    _TOKENIZER = NllbTokenizer.from_pretrained(
        MODEL_ID, src_lang=SRC_LANG, local_files_only=True
    )
    _MODEL = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_ID,
        dtype=torch.float16,
        low_cpu_mem_usage=True,
        local_files_only=True,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _MODEL = _MODEL.to(device)
    log.info("NLLB-200 loaded on %s", device)
    return _MODEL, _TOKENIZER


def _translate_batch(texts: list[str]) -> list[str]:
    """Translate a batch of English texts to Chinese."""
    model, tokenizer = _load_model()
    if not texts:
        return []

    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    ).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids(DST_LANG),
            max_length=MAX_LENGTH * 2,
            num_beams=2,
        )

    results = tokenizer.batch_decode(outputs, skip_special_tokens=True)
    return [r.strip() for r in results]


def translate_asr(
    asr_file: Path,
    session: Path,
    settings: dict[str, str] | None = None,
    source: Any = None,
) -> Path:
    dst_lang = "zh" if source is None else source.target_language
    output_file = session / "metadata" / f"translation.{dst_lang}.json"
    if output_file.exists():
        return output_file

    data = json.loads(asr_file.read_text(encoding="utf-8"))
    utterances = data["result"]["utterances"]
    texts = [u["text"].strip() for u in utterances if u["text"].strip()]

    if not texts:
        raise RuntimeError("No text to translate")

    log.info("NLLB translating %d sentences (batch_size=%d) ...", len(texts), BATCH_SIZE)
    dst_list: list[str] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        dst_list.extend(_translate_batch(batch))
        log.info("  %d/%d", min(i + BATCH_SIZE, len(texts)), len(texts))

    translation = [
        {
            "src": utt["text"],
            "dst": dst,
            "src_lang": "en" if source is None else source.asr_language,
            "dst_lang": dst_lang,
            "start_time": utt["start_time"],
            "end_time": utt["end_time"],
            "speaker": str(utt.get("additions", {}).get("speaker", "1"))
                if isinstance(utt.get("additions"), dict) else "1",
        }
        for utt, dst in zip(utterances, dst_list)
    ]

    output_file.write_text(
        json.dumps({"translation": translation}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info("Translation saved to %s (%d segments)", output_file, len(translation))
    return output_file
