import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from callsign import extract_callsign
from atc_numbers import (extract_heading, extract_altitude, extract_runway,
                         extract_frequency)

# Anchor to this file's own directory, not the caller's cwd
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "bert_intent_model")

# Load once at import — this is the "cold start" cost, paid one time
_device = "cuda" if torch.cuda.is_available() else "cpu"
_tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
_model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(_device)
_model.eval()

# Real ATC transmissions are short (a sentence or two); this is well above
# any realistic legitimate one. Found in Week 9's adversarial audit: the
# tokenizer's truncation (max_length=64 subword tokens) silently drops
# anything past it, and once a real instruction gets pushed past that
# window by enough padding/rambling text, BERT classifies whatever's left
# in the window instead — a verified "cleared for takeoff" was
# misclassified as frequency_change once buried under ~60+ words of
# filler. Rule-based slot extraction below is unaffected (it always scans
# the full untruncated text), but intent alone can't be trusted on
# anomalously long input, so it's forced to "unknown" (safe: triggers
# "say again" in readback.py) rather than trusting a truncation artifact.
MAX_REASONABLE_WORDS = 40


def parse_instruction(text: str) -> dict:
    """Same interface as llm_parser.parse_instruction — swap freely."""
    inputs = _tokenizer(text, return_tensors="pt",
                        truncation=True, max_length=64).to(_device)
    with torch.no_grad():
        logits = _model(**inputs).logits
    intent_id = int(logits.argmax(dim=-1))
    intent = _model.config.id2label[intent_id]
    if len(text.split()) > MAX_REASONABLE_WORDS:
        intent = "unknown"

    d = {
        "callsign": extract_callsign(text),
        "intent": intent,
        "heading_deg": extract_heading(text),
        "altitude_ft": None,
        "runway": extract_runway(text),
        "frequency": extract_frequency(text),
    }
    alt = extract_altitude(text)
    if alt is not None:
        d["altitude_ft"] = alt
    return d