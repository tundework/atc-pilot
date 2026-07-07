import json

KEEP_SPEAKER_PREFIX = "ATCO"   # instructions, not readbacks

rows = [json.loads(line) for line in open("atco2_candidates.jsonl")]
picked = [r for r in rows if r["speaker"].startswith(KEEP_SPEAKER_PREFIX)][:25]

with open("real_test_TEMPLATE.jsonl", "w") as f:
    for r in picked:
        entry = {
            "text": r["text"],
            "label": {
                "callsign": None,       # keep None for European callsigns
                "intent": "FILL_ME",    # one of: takeoff_clearance, landing_clearance,
                                        # heading_change, altitude_change, go_around,
                                        # hold, frequency_change, unknown
                "heading_deg": None,
                "altitude_ft": None,
                "runway": None,
                "frequency": None,
            },
        }
        f.write(json.dumps(entry) + "\n")

print(f"Wrote {len(picked)} template rows to real_test_TEMPLATE.jsonl")