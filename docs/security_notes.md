# Security / adversarial notes (Week 9)

Summary of what's structurally immune to prompt-injection-style attacks
on spoken/transcribed ATC text, what required an explicit guard to be
safe, and what's still an open risk. See `tests/test_adversarial.py`
for the executable version of every claim below.

## Structurally immune — no guard needed, by design

**BERT's fixed label space.** `bert_parser.py` (the primary, live-path
parser) classifies text into exactly 8 fixed intents. There is no
free-text generation surface for injected text to redirect the way
there is with an LLM completing arbitrary text — a crafted "ignore
previous instructions" clause has nowhere to go except into one of the
8 buckets. This is architectural immunity, not a behavioral property
that needs re-verifying every release. `llm_parser.py` (not the
primary path — see docs/benchmark.md) is generative and therefore has
a real, if narrow, injection surface; it's covered by explicit guards
below rather than by architecture.

## Required an explicit guard — found and fixed this week

**`extract_callsign()`'s run-selection on multi-callsign text.** When
an utterance contains both our callsign and another aircraft's (e.g. a
traffic advisory), the extractor used to pick whichever candidate
produced the LONGEST alphanumeric string, not necessarily the one
actually addressed to us. Fixed to take the FIRST candidate instead,
matching real ATC phraseology (the addressed aircraft is named first).
The ownership gate itself was never actually fooled by this even
before the fix — `pipeline.py`'s `contains_my_callsign()` fallback
independently confirms ownership by searching for our own callsign's
spoken form directly — but the *logged* `instruction["callsign"]`
value was factually wrong, and nothing guarantees every future caller
of `extract_callsign()` will have that same fallback available.

**Anomalously long/padded instruction text.** Padding an instruction
with enough filler pushes the real instruction past BERT's
64-subword-token truncation window. This is the one finding in this
suite that's a genuine safety-relevant bug, not just an
adversarial-suite technicality: a verified "cleared for takeoff" was
classified as `frequency_change` once buried under ~60+ words of
filler — an actual intent MISCLASSIFICATION, not a safe fallback.
Rule-based slot extraction (runway, heading, etc.) was unaffected,
since it always scans the full untruncated text — only BERT's intent
classification is vulnerable to the truncation. Fixed with a
word-count sanity gate (`MAX_REASONABLE_WORDS = 40` in
`bert_parser.py`): text longer than any realistic legitimate ATC
transmission forces `intent="unknown"` (safe — triggers "say again" in
`readback.py`) rather than trusting whatever intent falls out of a
truncation artifact. This is a defensive input-sanity gate, not a BERT
retrain — retraining was explicitly out of scope this week per the
Week 9 brief, and risked disturbing the Week 4 benchmark.

**`llm_parser.py`'s `validate()` range checks.** Even if a well-formed
but dangerous JSON payload made it out of the LLM (out-of-range
heading/altitude, an invalid intent string, a non-numeric value where
a number is expected), `validate()` catches it and forces
`intent="unknown"` rather than letting a passing-looking-but-wrong
value through. This was already in place (a Week 3 design decision —
"never trust the LLM blindly") and is exercised directly in this
week's adversarial suite as a regression guard, not a new fix.

## Numeral-form parsing gaps — same class of bug, three more instances found

Not prompt-injection per se, but adjacent: Week 7 found and fixed
`extract_heading()`/`extract_altitude()` silently failing on
numeral-form ASR output ("270" vs "two seven zero") because their
word-tokenization regex (`re.findall(r"[a-z-']+", ...)`) cannot see
digit characters at all. This week's audit found the exact same gap,
never fixed, in `extract_flight_level()`, `extract_runway()`, and
`extract_frequency()` — all three were silently invisible to numeral
input. Fixed with the same numeral-fallback pattern (regex directly
against the raw text, anchored on the relevant keyword) for all three.
Not a security vulnerability in the adversarial sense, but a real
correctness gap that would have silently dropped legitimate
instructions in exactly the kind of "ASR renders digits as numerals"
scenario this whole suite is built to probe.

## Open risks — documented, not fixed this week

**Two-aircraft near-simultaneous transmission.** Not meaningfully
testable at the text level — the garbling that would occur from
overlapping audio is an audio-domain phenomenon (two overlapping
waveforms), not a text-domain one. Would need real or synthesized
overlapping audio to construct a genuine test case. Flagged as future
work in `tests/test_adversarial.py::TestCallsignConfusion`.

**No cross-instruction memory or rate-of-change limiting.** The
supervisor validates every instruction completely independently — a
climb to near-maximum altitude immediately followed by a descent to
near-minimum altitude is accepted as two individually-valid
instructions, with no absurd-maneuver or rate-of-change guard between
them. This is documented current behavior (see
`TestEnvelopeViolations::test_contradictory_instruction_pairs_validated_independently`),
not something broken by this week's testing — but a reasonable future
addition if the project moves toward more autonomous, less
directly-ATC-driven operation.

**ASR homophone noise.** Confirmed in Week 8's 5x robustness pass and
unrelated to injection, but adjacent: Whisper can render a spoken digit
word as an unrelated homophone ("two" -> "to"), which breaks exact
digit-word matching in the rule-based extractors. Not patched with a
broad alias, since common English words like "to" risk false-positive
number extraction elsewhere. Accepted as real-world ASR variability.
