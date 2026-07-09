from readback import generate_readback
from speak import speak

cases = [
    {"intent": "takeoff_clearance", "runway": "27"},
    {"intent": "heading_change", "heading_deg": 270},
    {"intent": "altitude_change", "altitude_ft": 3000},
    {"intent": "altitude_change", "altitude_ft": None},   # truncation case → say again
    {"intent": "go_around"},
    {"intent": "unknown"},
]

for c in cases:
    text = generate_readback(c)
    print(f"{str(c):55} -> {text}")
    speak(text)