import json
import random

random.seed(42)  # reproducible dataset

DIGIT_WORDS = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
}
PHONETIC = {
    "A": "alpha", "B": "bravo", "C": "charlie", "D": "delta",
    "E": "echo", "F": "foxtrot", "G": "golf", "H": "hotel",
    "K": "kilo", "L": "lima", "M": "mike", "P": "papa",
    "Q": "quebec", "R": "romeo", "S": "sierra", "T": "tango",
    "U": "uniform", "V": "victor", "W": "whiskey",
    "X": "x-ray", "Y": "yankee", "Z": "zulu",
}


def speak_digits(s: str) -> str:
    """'270' -> 'two seven zero'"""
    return " ".join(DIGIT_WORDS[c] for c in s)


def speak_altitude(alt: int) -> str:
    """3000 -> 'three thousand'; 2500 -> 'two thousand five hundred'"""
    thousands, rem = divmod(alt, 1000)
    parts = []
    if thousands:
        parts.append(f"{speak_digits(str(thousands))} thousand")
    if rem:
        parts.append(f"{DIGIT_WORDS[str(rem // 100)]} hundred")
    return " ".join(parts)


def speak_callsign(cs: str) -> str:
    """'N172AB' -> 'cessna one seven two alpha bravo' (varied prefix)"""
    body = cs[1:]  # drop the N
    spoken = []
    for c in body:
        spoken.append(DIGIT_WORDS[c] if c.isdigit() else PHONETIC[c])
    prefix = random.choice(["cessna", "november", "skyhawk"])
    return f"{prefix} {' '.join(spoken)}"


CALLSIGNS = ["N172AB", "N45XY", "N8821Q", "N301TW", "N9DK",
             "N172AD", "N728PR", "N55VS"]
RUNWAYS = ["09", "18", "27", "36", "04", "22", "13", "31"]


def gen_heading_change(cs):
    hdg = random.choice(range(10, 361, 10))
    direction = random.choice(["left", "right"])
    templates = [
        f"{speak_callsign(cs)}, turn {direction} heading {speak_digits(f'{hdg:03d}')}",
        f"{speak_callsign(cs)}, fly heading {speak_digits(f'{hdg:03d}')}",
        f"turn {direction} heading {speak_digits(f'{hdg:03d}')}, {speak_callsign(cs)}",
    ]
    return random.choice(templates), {
        "callsign": cs, "intent": "heading_change",
        "heading_deg": hdg, "altitude_ft": None,
        "runway": None, "frequency": None,
    }


def gen_altitude_change(cs):
    alt = random.choice(range(2000, 10001, 500))
    verb = random.choice(["climb and maintain", "descend and maintain", "maintain"])
    templates = [
        f"{speak_callsign(cs)}, {verb} {speak_altitude(alt)}",
        f"{speak_callsign(cs)}, {verb} {speak_altitude(alt)}, expect higher in one zero minutes",
    ]
    return random.choice(templates), {
        "callsign": cs, "intent": "altitude_change",
        "heading_deg": None, "altitude_ft": alt,
        "runway": None, "frequency": None,
    }


def gen_takeoff(cs):
    rwy = random.choice(RUNWAYS)
    templates = [
        f"{speak_callsign(cs)}, runway {speak_digits(rwy)}, cleared for takeoff",
        f"{speak_callsign(cs)}, cleared for takeoff runway {speak_digits(rwy)}",
        f"{speak_callsign(cs)}, wind two seven zero at five, runway {speak_digits(rwy)}, cleared for takeoff",
    ]
    return random.choice(templates), {
        "callsign": cs, "intent": "takeoff_clearance",
        "heading_deg": None, "altitude_ft": None,
        "runway": rwy, "frequency": None,
    }


def gen_landing(cs):
    rwy = random.choice(RUNWAYS)
    templates = [
        f"{speak_callsign(cs)}, cleared to land runway {speak_digits(rwy)}",
        f"{speak_callsign(cs)}, runway {speak_digits(rwy)}, cleared to land",
        f"{speak_callsign(cs)}, number one, cleared to land runway {speak_digits(rwy)}",
    ]
    return random.choice(templates), {
        "callsign": cs, "intent": "landing_clearance",
        "heading_deg": None, "altitude_ft": None,
        "runway": rwy, "frequency": None,
    }


def gen_go_around(cs):
    templates = [
        f"{speak_callsign(cs)}, go around",
        f"{speak_callsign(cs)}, go around, traffic on the runway",
    ]
    return random.choice(templates), {
        "callsign": cs, "intent": "go_around",
        "heading_deg": None, "altitude_ft": None,
        "runway": None, "frequency": None,
    }


def gen_unknown(_cs):
    templates = [
        "traffic two o'clock five miles southbound",
        "attention all aircraft, bird activity reported near the field",
        "hey what's the weather like today",
        "say again",
        "radar contact",
    ]
    return random.choice(templates), {
        "callsign": None, "intent": "unknown",
        "heading_deg": None, "altitude_ft": None,
        "runway": None, "frequency": None,
    }


GENERATORS = [gen_heading_change, gen_altitude_change, gen_takeoff,
              gen_landing, gen_go_around, gen_unknown]


def main(n=2000):
    rows = []
    for _ in range(n):
        gen = random.choice(GENERATORS)
        cs = random.choice(CALLSIGNS)
        text, label = gen(cs)
        rows.append({"text": text, "label": label})

    random.shuffle(rows)
    split = int(n * 0.85)
    with open("data_train.jsonl", "w") as f:
        for r in rows[:split]:
            f.write(json.dumps(r) + "\n")
    with open("data_test.jsonl", "w") as f:
        for r in rows[split:]:
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {split} train / {n - split} test examples")
    for r in rows[:5]:
        print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()