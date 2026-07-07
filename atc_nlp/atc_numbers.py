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


def extract_altitude(text: str) -> float | None:
    """'climb and maintain two thousand five hundred' -> 2500.0
    Handles 'N thousand' and 'N hundred' spoken forms."""
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
    return total if found else None


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
        