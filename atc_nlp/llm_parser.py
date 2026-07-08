from callsign import extract_callsign
from atc_numbers import extract_heading, extract_altitude
import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

SYSTEM_PROMPT = """You are an ATC instruction parser. Given a radio transmission, output ONLY a JSON object with exactly these fields:

{
  "callsign": "<canonical callsign like N172AB, or null>",
  "intent": "<one of: takeoff_clearance, landing_clearance, heading_change, altitude_change, frequency_change, hold, go_around, unknown>",
  "heading_deg": <number or null>,
  "altitude_ft": <number or null>,
  "runway": "<string like 27 or 09L, or null>",
  "frequency": "<string like 121.5, or null>"
}

Rules:
- Spoken digits become numbers: "two seven zero" -> 270, "three thousand" -> 3000
- Phonetic letters become letters: "alpha bravo" -> AB
- "Cessna one seven two alpha bravo" -> callsign N172AB
- If the transmission is not an ATC instruction, intent is "unknown"

Examples:

Input: "Cessna one seven two alpha bravo, turn left heading two seven zero"
Output: {"callsign": "N172AB", "intent": "heading_change", "heading_deg": 270, "altitude_ft": null, "runway": null, "frequency": null}

Input: "Cessna one seven two alpha bravo, climb and maintain three thousand"
Output: {"callsign": "N172AB", "intent": "altitude_change", "heading_deg": null, "altitude_ft": 3000, "runway": null, "frequency": null}

Input: "Cessna one seven two alpha bravo, runway two seven, cleared for takeoff"
Output: {"callsign": "N172AB", "intent": "takeoff_clearance", "heading_deg": null, "altitude_ft": null, "runway": "27", "frequency": null}

Input: "Cessna one seven two alpha bravo, cleared to land runway two seven"
Output: {"callsign": "N172AB", "intent": "landing_clearance", "heading_deg": null, "altitude_ft": null, "runway": "27", "frequency": null}

Input: "Cessna one seven two alpha bravo, go around"
Output: {"callsign": "N172AB", "intent": "go_around", "heading_deg": null, "altitude_ft": null, "runway": null, "frequency": null}

Input: "Cessna one seven two alpha bravo, contact tower one two one decimal five"
Output: {"callsign": "N172AB", "intent": "frequency_change", "heading_deg": null, "altitude_ft": null, "runway": null, "frequency": "121.5"}

Input: "Cessna one seven two alpha bravo, hold short runway two seven"
Output: {"callsign": "N172AB", "intent": "hold", "heading_deg": null, "altitude_ft": null, "runway": "27", "frequency": null}
"""


def parse_instruction(text: str) -> dict:
    resp = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": f'Input: "{text}"\nOutput:',
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }, timeout=60)
    resp.raise_for_status()
    d = json.loads(resp.json()["response"])
    d["callsign"] = extract_callsign(text)      # rules override LLM
    d["heading_deg"] = extract_heading(text)    # rules override LLM
    alt = extract_altitude(text)
    if alt is not None:
        d["altitude_ft"] = alt
    return validate(d)


def validate(d: dict) -> dict:
    """Never trust LLM output blindly."""
    expected = ["callsign", "intent", "heading_deg",
                "altitude_ft", "runway", "frequency"]
    for key in expected:
        d.setdefault(key, None)

    valid_intents = {"takeoff_clearance", "landing_clearance",
                     "heading_change", "altitude_change",
                     "frequency_change", "hold", "go_around", "unknown"}
    if d["intent"] not in valid_intents:
        d["intent"] = "unknown"

    if d["heading_deg"] is not None:
        try:
            d["heading_deg"] = float(d["heading_deg"])
            if not (0 <= d["heading_deg"] <= 360):
                d["intent"] = "unknown"
        except (TypeError, ValueError):
            d["heading_deg"] = None
            d["intent"] = "unknown"

    if d["altitude_ft"] is not None:
        try:
            d["altitude_ft"] = float(d["altitude_ft"])
            if not (0 < d["altitude_ft"] < 60000):
                d["intent"] = "unknown"
        except (TypeError, ValueError):
            d["altitude_ft"] = None
            d["intent"] = "unknown"

    return d


if __name__ == "__main__":
    tests = [
        "Cessna one seven two alpha bravo, turn left heading two seven zero",
        "Cessna one seven two alpha bravo, descend and maintain two thousand five hundred",
        "Cessna one seven two alpha bravo, runway two seven, cleared for takeoff",
        "Cessna four five x-ray yankee, cleared to land runway one eight",
        "hey what's the weather like today",
    ]
    for t in tests:
        print(f"\nIN:  {t}")
        print(f"OUT: {parse_instruction(t)}")