import json
from llm_parser import parse_instruction

rows = [json.loads(line) for line in open("real_test.jsonl")]
print(f"File contains {len(rows)} rows\n")

for row in rows[:5]:
    pred = parse_instruction(row["text"])
    gold = row.get("label", "<<< NO 'label' KEY >>>")
    print(f"TEXT: {row['text'][:70]}")
    print(f"GOLD: {gold}")
    print(f"PRED: {pred}")
    print()