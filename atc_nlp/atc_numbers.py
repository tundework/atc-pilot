import re

DIGITS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "tree": "3",
    "four": "4", "five": "5", "fife": "5", "six": "6", "seven": "7",
    "eight": "8", "nine": "9", "niner": "9",
}


def extract_heading(text: str) -> float | None:
    """Find 'heading' followed by digit words, convert deterministically.
    'fly heading two nine zero' -> 290.0"""
    words = re.findall(r"[a-z-']+", text.lower())
    for i, w in enumerate(words):
        if w == "heading":
            digits = []
            for nxt in words[i + 1:]:
                if nxt in DIGITS:
                    digits.append(DIGITS[nxt])
                else:
                    break
            if digits:
                hdg = float("".join(digits))
                if 0 <= hdg <= 360:
                    return hdg
    return None


def extract_flight_level(text: str) -> float | None:
    """'descend to flight level seven zero' -> 7000.0 (FL70 = 7000 ft)"""
    words = re.findall(r"[a-z-']+", text.lower())
    for i in range(len(words) - 1):
        if words[i] == "flight" and words[i + 1] == "level":
            digits = []
            for nxt in words[i + 2:]:
                if nxt in DIGITS:
                    digits.append(DIGITS[nxt])
                else:
                    break
            if digits:
                fl = float("".join(digits))
                if 10 <= fl <= 450:
                    return fl * 100
    return None


def extract_altitude(text: str) -> float | None:
    """'climb and maintain two thousand five hundred' -> 2500.0
    Handles 'N thousand' / 'N hundred' spoken forms and flight levels
    ('flight level seven zero' -> 7000.0). An utterance won't contain both,
    so flight level wins if present."""
    fl = extract_flight_level(text)
    if fl is not None:
        return fl
    words = re.findall(r"[a-z-']+", text.lower())
    total = 0.0
    found = False
    for i, w in enumerate(words):
        if w == "thousand" and i > 0:
            # collect digit words immediately before 'thousand'
            j = i - 1
            digits = []
            while j >= 0 and words[j] in DIGITS:
                digits.insert(0, DIGITS[words[j]])
                j -= 1
            if digits:
                total += float("".join(digits)) * 1000
                found = True
        elif w == "hundred" and i > 0 and words[i - 1] in DIGITS:
            total += float(DIGITS[words[i - 1]]) * 100
            found = True
    if found:
        return total
    # Numeral fallback: Whisper often renders a spoken altitude as digits
    # ("one thousand five hundred" -> "1500") instead of words — observed
    # live in Week 7's reliability run, where this exact substitution
    # caused a real altitude_change instruction to be silently dropped.
    # Anchored on an altitude-context word so a stray 3+ digit number
    # elsewhere in the utterance (flight number, squawk code) can't be
    # misread as an altitude.
    if re.search(r"\b(climb|descend|maintain|altitude|feet)\b", text.lower()):
        m = re.search(r"\b(\d{3,5})\b", text.replace(",", ""))
        if m:
            val = float(m.group(1))
            if 100 <= val <= 60000:
                return val
    return None


SIDES = {"left": "L", "right": "R", "center": "C", "centre": "C"}


def extract_runway(text: str) -> str | None:
    """'cleared to land runway one eight left' -> '18L'.
    Fallback for keyword-less real ATC ('one six right cleared to land'
    -> '16R'): a 1-2 digit run anchored by a following side word."""
    words = re.findall(r"[a-z-']+", text.lower())
    for i, w in enumerate(words):
        if w == "runway":
            digits = []
            j = i + 1
            while j < len(words) and words[j] in DIGITS:
                digits.append(DIGITS[words[j]])
                j += 1
            if not digits or not 1 <= int("".join(digits)) <= 36:
                continue
            rwy = "".join(digits)
            if j < len(words) and words[j] in SIDES:
                rwy += SIDES[words[j]]
            return rwy
    # No 'runway' keyword: require the side-word anchor, so bare numbers
    # (headings, winds, frequencies) can never match
    for i, w in enumerate(words):
        if w in SIDES and i > 0:
            digits = []
            j = i - 1
            while j >= 0 and words[j] in DIGITS and len(digits) < 2:
                digits.insert(0, DIGITS[words[j]])
                j -= 1
            # reject if the digit run is longer than 2 (heading, not runway)
            if digits and (j < 0 or words[j] not in DIGITS) \
                    and 1 <= int("".join(digits)) <= 36:
                return "".join(digits) + SIDES[w]
    return None


if __name__ == "__main__":
    tests_h = [
        ("fly heading two nine zero", 290),
        ("turn right heading two nine zero, cessna one seven two alpha delta", 290),
        ("fly heading zero two zero", 20),
        ("turn left heading three six zero", 360),
        ("cleared to land runway two seven", None),
    ]
    tests_a = [
        ("climb and maintain three thousand", 3000),
        ("descend and maintain two thousand five hundred", 2500),
        ("maintain five thousand, expect higher in one zero minutes", 5000),
        ("go around", None),
    ]
    for t, exp in tests_h:
        got = extract_heading(t)
        print(f"{'OK ' if got == exp else 'FAIL'} heading {got!r:8} expected {exp!r:8} | {t[:45]}")
    for t, exp in tests_a:
        got = extract_altitude(t)
        print(f"{'OK ' if got == exp else 'FAIL'} alt     {got!r:8} expected {exp!r:8} | {t[:45]}")
        