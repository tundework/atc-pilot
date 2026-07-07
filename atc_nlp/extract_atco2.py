import glob
import json
import xml.etree.ElementTree as ET

KEYWORDS = ["heading", "cleared for takeoff", "cleared to land",
            "climb", "descend", "go around", "maintain"]

rows = []
for f in glob.glob("atco2/ATCO2-ASRdataset-v1_beta/DATA/*.xml"):
    try:
        root = ET.parse(f).getroot()
    except ET.ParseError:
        continue
    for seg in root.findall("segment"):
        t = seg.find("text")
        sp = seg.find("speaker_label")
        if t is None or not t.text:
            continue
        text = t.text.strip()
        if "[#" in text:          # skip the tag-annotated ones
            continue
        speaker = sp.text if sp is not None else "?"
        if any(k in text.lower() for k in KEYWORDS):
            rows.append({"speaker": speaker, "text": text})

with open("atco2_candidates.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
print(f"Wrote {len(rows)} candidate instructions")