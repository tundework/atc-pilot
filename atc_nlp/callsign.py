import re

PHONETIC = {
    "alpha": "A", "bravo": "B", "charlie": "C", "delta": "D",
    "echo": "E", "foxtrot": "F", "golf": "G", "hotel": "H",
    "india": "I", "juliett": "J", "juliet": "J", "kilo": "K",
    "lima": "L", "mike": "M", "november": "N", "oscar": "O",
    "papa": "P", "quebec": "Q", "romeo": "R", "sierra": "S",
    "tango": "T", "uniform": "U", "victor": "V", "whiskey": "W",
    "xray": "X", "x-ray": "X", "yankee": "Y", "zulu": "Z",
}

DIGITS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "tree": "3",
    "four": "4", "five": "5", "fife": "5", "six": "6", "seven": "7",
    "eight": "8", "nine": "9", "niner": "9",
}

# Words that commonly precede a callsign and should be skipped
MAKES = {"cessna", "piper", "skyhawk", "cherokee", "november"}


def extract_callsign(text: str) -> str | None:
    """Extract a US GA callsign (digits + phonetic letters) from spoken ATC
    text. A run only starts after a recognized make word (cessna/november/...),
    which rejects airline-style callsigns like 'Fraction One Zero Three Mike'
    that happen to end in spoken digits + a letter."""
    words = re.findall(r"[a-z-']+", text.lower())

    runs = []
    current = []
    has_letter = False
    active = False
    for w in words:
        if not active:
            active = w in MAKES
            continue
        if w in DIGITS:
            current.append(DIGITS[w])
        elif w in PHONETIC and current:  # letters only after digits started
            current.append(PHONETIC[w])
            has_letter = True
        else:
            if current and has_letter:
                runs.append("".join(current))
            current, has_letter = [], False
            active = w in MAKES
    if current and has_letter:
        runs.append("".join(current))

    if not runs:
        return None
    # If multiple candidates, take the longest (most specific)
    return "N" + max(runs, key=len)


def matches(extracted: str | None, my_callsign: str) -> bool:
    """Paranoid matcher. Exact match, or exact partial (ATC often
    shortens N45XY to 'five x-ray yankee' after first contact)."""
    if extracted is None:
        return False
    if extracted == my_callsign:
        return True
    # partial: extracted suffix matches my suffix, min 3 chars
    if len(extracted) >= 4 and my_callsign.endswith(extracted[1:]):
        return True
    return False


def contains_my_callsign(text: str, my_callsign: str = "N172AB") -> bool:
    """Targeted search for OUR callsign's spoken form (full or ATC-shortened
    suffix), without loosening the MAKES gate on extract_callsign().
    'one seven two alpha bravo, turn left...' -> True for N172AB.
    Extraction-side counterpart of matches()'s suffix shortening."""
    words = re.findall(r"[a-z-']+", text.lower())
    # Build the spoken token sequence for our callsign body (drop the N prefix)
    rev_digits = {v: k for k, v in DIGITS.items()
                  if k not in ("tree", "fife", "niner")}
    rev_phon = {v: k for k, v in PHONETIC.items()
                if k not in ("juliet", "x-ray")}
    spoken = [rev_digits[c] if c.isdigit() else rev_phon[c]
              for c in my_callsign[1:]]
    # Accept spoken-variant tokens (tree/fife/niner, x-ray) when matching
    variants = {"tree": "three", "fife": "five", "niner": "nine",
                "x-ray": "xray", "juliet": "juliett"}
    norm = [variants.get(w, w) for w in words]
    # Full form or any suffix of length >= 3 tokens (ATC shortening)
    for start in range(len(spoken) - 2):
        seq = spoken[start:]
        for i in range(len(norm) - len(seq) + 1):
            if norm[i:i + len(seq)] == seq:
                return True
    return False


if __name__ == "__main__":
    tests = [
        ("cessna one seven two alpha bravo, turn left heading two seven zero", "N172AB"),
        ("cessna four five x-ray yankee, cleared to land runway one eight", "N45XY"),
        ("november eight eight two one quebec, hold short", "N8821Q"),
        ("cessna one seven two alpha delta, descend two thousand", "N172AD"),  # NOT us!
        ("hey what's the weather like today", None),
        ("turn left heading two seven zero, cessna one seven two alpha bravo", "N172AB"),
        ("traffic two o'clock five miles southbound", None),
        ("fraction one zero three mike wind one four zero degrees four knots", None),
        ("quadriga one six three foxtrot descend to flight level seven zero", None),
    ]
    MY_CALLSIGN = "N172AB"
    for text, expected in tests:
        got = extract_callsign(text)
        is_me = matches(got, MY_CALLSIGN)
        status = "OK " if got == expected else "FAIL"
        print(f"{status} extracted={got!r:10} expected={expected!r:10} for_me={is_me}  | {text[:50]}")