import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from callsign import extract_callsign
from atc_numbers import extract_heading, extract_altitude

MODEL_DIR = "bert_intent_model"

# Load once at import — this is the "cold start" cost, paid one time
_device = "cuda" if torch.cuda.is_available() else "cpu"
_tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
_model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(_device)
_model.eval()


def parse_instruction(text: str) -> dict:
    """Same interface as llm_parser.parse_instruction — swap freely."""
    inputs = _tokenizer(text, return_tensors="pt",
                        truncation=True, max_length=64).to(_device)
    with torch.no_grad():
        logits = _model(**inputs).logits
    intent_id = int(logits.argmax(dim=-1))
    intent = _model.config.id2label[intent_id]

    d = {
        "callsign": extract_callsign(text),
        "intent": intent,
        "heading_deg": extract_heading(text),
        "altitude_ft": None,
        "runway": None,       # LLM extracted this; BERT pipeline doesn't (yet) — noted in benchmark
        "frequency": None,
    }
    alt = extract_altitude(text)
    if alt is not None:
        d["altitude_ft"] = alt
    return d