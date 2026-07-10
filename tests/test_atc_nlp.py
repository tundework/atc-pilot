"""Pure unit tests for the rule extractors — no SITL, no GPU, CI-friendly.

Covers the Week 6 Day 1 extraction gaps (CLAUDE.md issues #9, #14, #16)
plus regression cases for the earned fixes (MAKES gate, suffix matching).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "atc_nlp"))

from atc_numbers import (extract_heading, extract_altitude,
                         extract_flight_level, extract_runway)
from callsign import extract_callsign, matches, contains_my_callsign


# ---------- #9: flight levels ----------

def test_flight_level_basic():
    assert extract_flight_level("descend to flight level seven zero") == 7000.0

def test_flight_level_three_digits():
    assert extract_flight_level("climb flight level one one zero") == 11000.0

def test_flight_level_niner_variant():
    assert extract_flight_level("maintain flight level niner zero") == 9000.0

def test_flight_level_absent():
    assert extract_flight_level("climb and maintain three thousand") is None

def test_flight_level_out_of_range():
    # FL5 (below 10) and FL990 (above 450) are not plausible clearances
    assert extract_flight_level("flight level five") is None
    assert extract_flight_level("flight level niner niner zero") is None

def test_altitude_returns_flight_level():
    assert extract_altitude("quadriga descend to flight level seven zero") == 7000.0

def test_altitude_thousand_hundred_still_works():
    assert extract_altitude("climb and maintain three thousand") == 3000.0
    assert extract_altitude("descend and maintain two thousand five hundred") == 2500.0

def test_altitude_none_when_no_altitude():
    assert extract_altitude("go around") is None


# ---------- #14: runways ----------

def test_runway_plain():
    assert extract_runway("cleared for takeoff runway two seven") == "27"

def test_runway_with_side():
    assert extract_runway("cleared to land runway one eight left") == "18L"
    assert extract_runway("runway three one right cleared for takeoff") == "31R"
    assert extract_runway("line up and wait runway two two centre") == "22C"

def test_runway_zero_padded():
    assert extract_runway("cleared for takeoff runway zero four") == "04"

def test_runway_absent():
    assert extract_runway("turn left heading two seven zero") is None

def test_runway_word_without_digits():
    assert extract_runway("cross the runway when able") is None

def test_runway_out_of_range():
    assert extract_runway("runway nine nine") is None
    assert extract_runway("runway zero zero") is None

def test_runway_keywordless_with_side_anchor():
    # Real ATCO2 phrasing: no 'runway' keyword, side word anchors it
    assert extract_runway("one six right cleared to land jetex seven four three four") == "16R"
    assert extract_runway("two two left cleared for takeoff") == "22L"

def test_runway_fallback_never_fires_without_anchor():
    # bare digit runs (headings, winds) must not match without a side word
    assert extract_runway("turn left heading two seven zero") is None
    assert extract_runway("wind one four zero degrees four knots") is None
    # side word after a 3-digit run is a heading, not a runway
    assert extract_runway("heading two seven zero right traffic") is None


# ---------- #16: short-form own callsign ----------

MY = "N172AB"

def test_short_callsign_no_make_word():
    # The live miss that motivated this: controller shorthand after first contact
    assert contains_my_callsign(
        "one seven two alpha bravo, turn left heading two seven zero", MY)

def test_full_callsign_with_make_word():
    assert contains_my_callsign(
        "cessna one seven two alpha bravo, cleared for takeoff", MY)

def test_suffix_shortening():
    # ATC may shorten to the last 3+ tokens
    assert contains_my_callsign("seven two alpha bravo, descend two thousand", MY)
    assert contains_my_callsign("two alpha bravo, contact tower", MY)

def test_too_short_suffix_rejected():
    # 2 tokens is below the min-3 threshold — too ambiguous
    assert not contains_my_callsign("alpha bravo, turn left", MY)

def test_other_aircraft_not_matched():
    # N172AD is one letter off — must NOT match us
    assert not contains_my_callsign(
        "one seven two alpha delta, descend two thousand", MY)

def test_unrelated_text_not_matched():
    assert not contains_my_callsign("traffic two o'clock five miles southbound", MY)

def test_spoken_variant_digits():
    # ASR / controllers may say 'niner', 'tree', 'fife'
    assert contains_my_callsign("one seven two alpha bravo cleared to land", MY)
    assert contains_my_callsign(
        "niner five one alpha bravo say again", "N951AB")


# ---------- regressions: MAKES gate + matches() unchanged ----------

def test_airline_callsign_still_rejected():
    assert extract_callsign(
        "fraction one zero three mike wind one four zero degrees four knots") is None
    assert extract_callsign(
        "quadriga one six three foxtrot descend to flight level seven zero") is None

def test_extract_callsign_still_works():
    assert extract_callsign(
        "cessna one seven two alpha bravo, turn left heading two seven zero") == "N172AB"
    assert extract_callsign(
        "november eight eight two one quebec, hold short") == "N8821Q"

def test_matches_regressions():
    assert matches("N172AB", MY)
    assert not matches("N172AD", MY)
    assert not matches(None, MY)

def test_heading_regressions():
    assert extract_heading("fly heading two nine zero") == 290.0
    assert extract_heading("turn left heading three six zero") == 360.0
    assert extract_heading("cleared to land runway two seven") is None
