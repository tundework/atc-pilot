# Scenario library

Five scripted ATC exchanges, each run end to end through the real
pipeline — Piper TTS synthesizes the "ATC" audio, real Whisper ASR
transcribes it, the real DistilBERT parser classifies intent and
extracts values, the real phase-aware supervisor gates every
instruction, and (on ACCEPT) real `FlightAPI` calls fly the SITL
aircraft. Nothing here is mocked; a scenario can't tell the difference
between synthesized ATC and a human speaking into the mic.

Run one: `python run_one.py <name>` (SITL must already be up).
Run all five, N times each: `python run_all.py <N>`.

## pattern_flight

Standard traffic-pattern flight: takeoff, one circuit (climb to a safe
altitude on crosswind), land. The baseline case — if this doesn't pass,
nothing else will. Demonstrates the everyday path: clearance in on the
ground, one instruction airborne, clearance back down.

## vectors_and_altitude

ATC vectors the aircraft through two heading changes and an altitude
change before clearing to land. Demonstrates sustained multi-instruction
handling mid-flight — the supervisor tracking phase and executing five
separate real flight commands across one continuous flight, not just a
single request-response pair.

## straight_in_approach

A direct approach and landing without flying a full circuit first —
tests `landing_clearance` arriving from cruise rather than from a
standard pattern. Also documents a real parser gap found while building
this scenario: the natural phrase "cleared straight-in approach runway
two seven" gets misclassified as `takeoff_clearance` (a synthetic-
training-data gap — `generate_data.py`'s templates never generated that
phrasing). Worked around with alternate phrasing rather than retraining
the classifier, which is out of scope for a demo scenario; the gap
itself is worth fixing before real-world use.

## multi_instruction_sequence

A dense instruction sequence including a *repeated* heading command
(same heading, spoken twice) and a frequency change. The repeat
exercises Week 7 Day 2's idempotency rule live — a controller
re-confirming a heading you're already flying must be accepted again,
not rejected as spam. Building this scenario also found and fixed a
real, previously-unnoticed bug: `bert_parser.py` had never extracted
frequency values at all (`frequency: None` hardcoded, no
`extract_frequency()` existed) — every `frequency_change` instruction
was silently unusable regardless of phrasing, for the entire project
until now.

## go_around

The failure-handling showcase. ATC clears the aircraft to land, then —
timed to land while the plane is genuinely on final approach, before
touchdown — calls for a go-around. Tests the `approach -> airborne`
phase transition (built Week 6 Day 3) under real timing pressure for
the first time, plus that a second `landing_clearance` afterward can
re-establish the approach and land normally. The timing is deliberately
tuned (30s after the first landing clearance, not the original 45s) so
the go-around call lands mid-approach rather than after the plane has
already touched down — confirmed via `decisions.jsonl` showing
`phase="approach"` at the exact moment the go-around instruction is
processed, not `"ground"`.
