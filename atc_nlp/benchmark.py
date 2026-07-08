import json
import time
import importlib

import llm_parser
import bert_parser

PARSERS = {"LLM (llama3.2:3b + rules)": llm_parser.parse_instruction,
           "BERT (DistilBERT + rules)": bert_parser.parse_instruction}

DATASETS = {"synthetic (100)": "data_test.jsonl",
            "REAL ATCO2 (20)": "real_test.jsonl"}


def evaluate(parse_fn, path, limit=None):
    rows = [json.loads(l) for l in open(path)]
    if limit:
        rows = rows[:limit]
    n = len(rows)
    intent_ok = 0
    latencies = []
    misses = []
    for r in rows:
        t0 = time.perf_counter()
        pred = parse_fn(r["text"])
        latencies.append(time.perf_counter() - t0)
        if pred["intent"] == r["label"]["intent"]:
            intent_ok += 1
        else:
            misses.append((r["text"][:60], r["label"]["intent"], pred["intent"]))
    latencies.sort()
    return {
        "n": n,
        "intent_acc": intent_ok / n,
        "p50_ms": latencies[n // 2] * 1000,
        "p95_ms": latencies[int(n * 0.95)] * 1000 if n >= 20 else latencies[-1] * 1000,
        "misses": misses,
    }


results = {}
for pname, fn in PARSERS.items():
    # warmup (avoid cold-start polluting p50)
    fn("cessna one seven two alpha bravo, cleared for takeoff runway two seven")
    for dname, path in DATASETS.items():
        limit = 100 if "synthetic" in dname else None   # keep LLM runtime sane
        print(f"Running {pname} on {dname}...")
        results[(pname, dname)] = evaluate(fn, path, limit)

print("\n=== BENCHMARK ===\n")
print(f"{'Parser':28} {'Dataset':18} {'Intent':>8} {'p50':>9} {'p95':>9}")
for (pname, dname), r in results.items():
    print(f"{pname:28} {dname:18} {r['intent_acc']:>7.1%} {r['p50_ms']:>7.1f}ms {r['p95_ms']:>7.1f}ms")

print("\n=== BERT misses on REAL data ===")
for text, gold, pred in results[("BERT (DistilBERT + rules)", "REAL ATCO2 (20)")]["misses"]:
    print(f"  gold={gold:20} pred={pred:20} | {text}")