MY_CALLSIGN_SPOKEN = "one seven two alpha bravo"   # short form, standard after first contact


def spoken_digits(n) -> str:
    words = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
             "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "niner"}
    return " ".join(words[c] for c in str(int(n)))


def spoken_altitude(ft) -> str:
    ft = int(ft)
    if ft % 100 == 0 and ft >= 1000:
        th, rem = divmod(ft, 1000)
        parts = [f"{spoken_digits(th)} thousand"]
        if rem:
            parts.append(f"{spoken_digits(rem // 100)} hundred")
        return " ".join(parts)
    return spoken_digits(ft)


def spoken_runway(rwy: str) -> str:
    """'27' -> 'two seven', '18L' -> 'one eight left'"""
    sides = {"L": "left", "R": "right", "C": "center"}
    digits = "".join(c for c in rwy if c.isdigit())
    # per-char so 'runway 04' keeps its leading zero ('zero four')
    out = " ".join(spoken_digits(c) for c in digits) if digits else rwy
    if rwy and rwy[-1] in sides:
        out += " " + sides[rwy[-1]]
    return out


def generate_readback(instruction: dict) -> str:
    """Structured instruction in, ICAO-style readback text out."""
    intent = instruction["intent"]
    cs = MY_CALLSIGN_SPOKEN

    if intent == "takeoff_clearance":
        rwy = instruction.get("runway")
        if not rwy:
            return f"Say again runway, {cs}."
        return f"Cleared for takeoff runway {spoken_runway(rwy)}, {cs}."

    if intent == "landing_clearance":
        rwy = instruction.get("runway")
        if not rwy:
            return f"Say again runway, {cs}."
        return f"Cleared to land runway {spoken_runway(rwy)}, {cs}."

    if intent == "heading_change":
        hdg = instruction.get("heading_deg")
        if hdg is None:
            return f"Say again heading, {cs}."
        return f"Heading {spoken_digits(f'{int(hdg):03d}')}, {cs}."

    if intent == "altitude_change":
        alt = instruction.get("altitude_ft")
        if alt is None:
            return f"Say again altitude, {cs}."
        # Direction-neutral: the parse dict doesn't carry climb/descend, and
        # reading back 'climb' for a descend instruction is worse than neither
        return f"Maintain {spoken_altitude(alt)}, {cs}."

    if intent == "go_around":
        return f"Going around, {cs}."

    if intent == "hold":
        rwy = instruction.get("runway")
        if rwy:
            return f"Holding short runway {spoken_runway(rwy)}, {cs}."
        return f"Holding position, {cs}."

    if intent == "frequency_change":
        freq = instruction.get("frequency")
        if freq is None:
            return f"Say again frequency, {cs}."
        whole, _, dec = str(freq).partition(".")
        return f"Contacting {spoken_digits(whole)} decimal {spoken_digits(dec)}, {cs}."

    # unknown — the safety-correct response
    return f"Say again, {cs}."