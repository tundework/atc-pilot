import json
import time
from llm_parser import parse_instruction

correct_intent = 0
correct_heading = 0
heading_total = 0
correct_callsign = 0
latencies = []

rows = [json.loads(line) for line in open("data_test.jsonl")]
N = 100  # subset first — LLM is slow; bump later
rows = rows[:N]

for i, row in enumerate(rows):
    t0 = time.time()
    pred = parse_instruction(row["text"])
    latencies.append(time.time() - t0)
    gold = row["label"]

    if pred["intent"] == gold["intent"]:
        correct_intent += 1
    if gold["heading_deg"] is not None:
        heading_total += 1
        if pred["heading_deg"] == gold["heading_deg"]:
            correct_heading += 1
    if pred["callsign"] == gold["callsign"]:
        correct_callsign += 1

    if (i + 1) % 10 == 0:
        print(f"{i+1}/{N} done")

lat_sorted = sorted(latencies)
print(f"\nIntent accuracy:   {correct_intent}/{N} = {correct_intent/N:.1%}")
print(f"Heading accuracy:  {correct_heading}/{heading_total}")
print(f"Callsign accuracy: {correct_callsign}/{N} = {correct_callsign/N:.1%}")
print(f"Latency p50: {lat_sorted[N//2]:.2f}s   p95: {lat_sorted[int(N*0.95)]:.2f}s")
