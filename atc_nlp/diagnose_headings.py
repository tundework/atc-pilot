import json
from llm_parser import parse_instruction

rows = [json.loads(line) for line in open("data_test.jsonl")]
rows = [r for r in rows[:100] if r["label"]["heading_deg"] is not None]

for row in rows:
    pred = parse_instruction(row["text"])
    gold = row["label"]["heading_deg"]
    if pred["heading_deg"] != gold:
        print(f"TEXT: {row['text']}")
        print(f"GOLD: {gold}   PRED: {pred['heading_deg']}   intent: {pred['intent']}\n")