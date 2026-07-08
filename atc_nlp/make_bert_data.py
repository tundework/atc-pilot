import json
from pathlib import Path

INTENTS = ["takeoff_clearance", "landing_clearance", "heading_change",
           "altitude_change", "frequency_change", "hold", "go_around",
           "unknown"]
INTENT_TO_ID = {name: i for i, name in enumerate(INTENTS)}

BASE_DIR = Path(__file__).resolve().parent


def convert(src, dst):
    with open(BASE_DIR / dst, "w") as out:
        for line in open(BASE_DIR / src):
            row = json.loads(line)
            out.write(json.dumps({
                "text": row["text"],
                "label": INTENT_TO_ID[row["label"]["intent"]],
            }) + "\n")


convert("data_train.jsonl", "bert_train.jsonl")
convert("data_test.jsonl", "bert_test.jsonl")
print("Wrote bert_train.jsonl and bert_test.jsonl")
