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

## Robustness: 24/25 (5 repeats x 5 scenarios)

See `docs/scenario_clips/robustness_pass_5x_result.log` for the full
grid. The one failure (`vectors_and_altitude`, repeat 4) was a genuine
one-off ASR mis-transcription, not a code bug: Whisper rendered "turn
left heading **two** seven zero" as "**tur** left heading **to** seven
zero" — the homophone "to" (not "two") broke the digit-word extractor.
Phase tracking was correct throughout; the value was simply
unparseable due to speech-recognition noise. Deliberately not patched
with a broad "to"->"two" alias, since "to" is common enough in English
that it risks false-positive number extraction elsewhere — this is
accepted, expected real-world ASR variability, not an architectural
gap.

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

## premature_landing_clearance

Week 9 Day 3's adversarial phase-injection case, live: a landing
clearance is sent immediately after takeoff, before telemetry has had
time to advance phase past `"takeoff"` (that only happens once the
altimeter crosses 30m via the telemetry poller — not the instant
takeoff is commanded). Confirms the phase gate consults actual current
state, not assumed/instantaneous state. Genuinely tight timing to
construct: `process_audio()`'s own round trip (ASR + parse + readback
synthesis/playback) adds ~5s of unavoidable overhead per step, and the
climb crosses 30m in as little as ~8s, leaving very little margin.
`wait_after_s=0` on the takeoff step turned out to be enough — the
step's own processing overhead alone provided the delay needed to land
the premature instruction while still genuinely in `"takeoff"` phase
(confirmed: REJECT at `phase="takeoff"`, landing before the
`takeoff -> airborne` transition fires), followed by the same
instruction correctly ACCEPTed once actually airborne.
