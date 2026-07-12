# CLAUDE.md — atc-pilot Project Context

## What this project is

An AI-piloted RC plane (simulation-first) that responds to **spoken ATC instructions**.
Pipeline: microphone → speech-to-text → instruction parser → safety supervisor → MAVLink → ArduPilot SITL.

**Deliverable:** YouTube video + blog post + this public repo (github.com/tundework/atc-pilot).
**Timeline:** 12-week plan at ~20 hrs/week. Currently **starting Week 10** —
Weeks 1-9 complete (see [docs/week6_milestone.md](docs/week6_milestone.md)
for the first fully voice-commanded flight,
[scenarios/README.md](scenarios/README.md) for the 5-scenario library, and
[docs/security_notes.md](docs/security_notes.md) for the Week 9
adversarial-suite results).
**Owner background:** one semester of deep learning; learning Linux/git/MAVLink through this project.

## Environment & conventions (IMPORTANT)

- Windows 11 + **WSL2 Ubuntu 22.04**; VS Code connected via WSL extension
- **ALL Python runs inside the single canonical venv: `~/atc-pilot/venv`**
  (`source venv/bin/activate`). NEVER install with `--user` or into system Python.
  (History: split-brain across system Python + 3 venvs already happened once;
  VS Code's Python extension auto-created duplicate `.venv` folders — since deleted.
  Interpreter should be pinned to `~/atc-pilot/venv/bin/python`.)
- **GPU: NVIDIA RTX 4060, 8GB VRAM (confirmed via nvidia-smi). Local training is
  the default — no Colab needed.** DistilBERT fine-tune runs in ~17s.
- Installed stack: torch 2.5.1+cu121, transformers 5.13.0, datasets 5.0.0,
  accelerate, scikit-learn, pymavlink, mavproxy, pytest, requests
- ArduPilot at `~/ardupilot`, built for SITL (ArduPlane 4.8.0-dev).
  SITL launch: `cd ~/ardupilot/ArduPlane && sim_vehicle.py --console --map --out=udp:127.0.0.1:14550`
- Mission Planner on Windows, TCP 127.0.0.1:5763
- Ollama in WSL serving `llama3.2:3b` at http://localhost:11434 (GPU-accelerated;
  can OOM if Windows apps hog VRAM — restart ollama after freeing memory)
- Key SITL params: `RTL_AUTOLAND=2`, `ARMING_CHECK=0` (sim only), `WP_RADIUS=30`
- **SITL relaunches with `-w` wipe ALL params — tests must self-provision via
  `FlightAPI.ensure_sim_params()`; never rely on ambient SITL state.** Also:
  ensure_sim_params() must be refused/no-op'd on real hardware (ARMING_CHECK=0
  is sim-only) — guard via autopilot type or an explicit `i_am_simulated=True`
  flag, decided in Phase 2. And arming is REFUSED while the autopilot thinks
  it's mid-landing-sequence (e.g. leftover RTL mode + landing mission from a
  killed test) — reset to MANUAL first.
- MAVProxy (system-Python install) currently crashes on a numpy 2.x/matplotlib
  ABI mismatch (`_ARRAY_API not found`) — part of the issue-#13 env saga. Until
  fixed, connect FlightAPI directly to SITL's own TCP port
  (`tcp:127.0.0.1:5763` externally, or `tcp:127.0.0.1:5760` if nothing else
  holds it) instead of the usual `udp:14550` MAVProxy relay.
- Commit at the end of every session, even WIP. Placeholders in ALL CAPS mean "replace me."

## Architecture

```
[Mic] → [VAD] → [Whisper ASR]          (Week 5, DONE — live, <1s response)
                     |
              [ATC PARSER]              (swappable implementations)
                text → intent classifier → one of 8 intents
                                LLM (llm_parser.py) or DistilBERT (bert_parser.py, DONE)
                text → rule modules → callsign, heading, altitude  (shared by both)
                     → validate()   → range checks
                     |
              [Callsign filter]         (only act on MY instructions)
                     |
              [Supervisor]              (Week 6, DONE — phase-aware gates, JSONL audit trail)
                     |
              [FlightAPI]               (Week 2, DONE — verified calls (Week 6 Day 4))
                     |
              [ArduPilot SITL]
```

**Core design principle (earned through eval failures):** the model classifies
*intent only*; deterministic rules extract *every value*. llama3.2:3b hallucinated
spoken-digit conversions ("two nine zero" -> 270 errors) and invented callsigns.
Rules fixed both. Same NASA-funded hybrid rule+NER pattern published Jan 2026;
same architecture family as Merlin Labs' Pilot.

## Intents (8)

`takeoff_clearance, landing_clearance, heading_change, altitude_change,
frequency_change, hold, go_around, unknown` — all 8 now have generator templates
and training data (179–230 examples per class).

## Repo structure

```
atc-pilot/
├── flight_api/
│   ├── flight_api.py        # FlightAPI class (18 methods incl. context manager)
│   └── demo_full_mission.py # takeoff->climb->turn->hold->RTL demo (+ test scripts)
├── atc_nlp/
│   ├── llm_parser.py        # parse_instruction(text)->dict via Ollama few-shot
│   ├── callsign.py          # rule-based extractor; gated on MAKES words (fixed)
│   ├── atc_numbers.py       # extract_heading(), extract_altitude() — rules
│   ├── generate_data.py     # synthetic generator, all 8 intents
│   ├── make_bert_data.py    # converts to flat int labels for BERT
│   ├── train_bert.py        # DistilBERT fine-tune, fp16, ~17s on the 4060
│   ├── bert_parser.py       # parse_instruction(text)->dict via bert_intent_model
│   ├── bert_intent_model/   # trained model (8 intents), 20/20 (100%) on real data
│   ├── benchmark.py         # head-to-head LLM vs BERT: synthetic + real + latency
│   ├── eval_parser.py / eval_real.py / diagnose_real.py
│   ├── real_test.jsonl      # 20 hand-labeled REAL ATCO2 transcripts (gold)
│   ├── data_train/test.jsonl, bert_train/test.jsonl
│   └── atco2/               # 288MB real dataset — gitignored, licensed data
├── tests/test_flight_api.py # 5 pytest tests vs live SITL
├── tests/test_atc_nlp.py    # 35 pure unit tests for rule extractors (no SITL/GPU)
├── tests/test_supervisor*.py # gate + idempotency tests (Week 6/7)
├── tests/test_adversarial.py # Week 9 adversarial suite, 28 tests, 100% pass —
│                             #   see docs/security_notes.md
├── voice/                   # ASR, TTS, pipeline.py, watch.py + worker.py (live, Week 5/6)
├── supervisor/              # supervisor.py (4 gates, phase state machine, decisions.jsonl)
├── scenarios/                # 6-scenario library (Weeks 8-9) — see scenarios/README.md
│   ├── scenario.py          # Scenario/ScenarioStep dataclasses
│   ├── run_scenario.py      # core runner: synth ATC line -> real pipeline -> verify verdict
│   ├── run_one.py           # CLI: run one named scenario against live SITL
│   ├── run_all.py           # CLI: run every scenario N times, tabulate pass/fail
│   └── lib.py               # pattern_flight, vectors_and_altitude, straight_in_approach,
│                             #   multi_instruction_sequence, go_around,
│                             #   premature_landing_clearance (Week 9 Day 3)
├── docs/security_notes.md   # Week 9: structural immunity vs explicit guards vs open risks
├── main.py                  # single entry point: starts watch.py + worker.py together (Week 7)
├── scripts/day4_reliability_run.py  # no-voice reliability loop (TTS-synthesized ATC)
└── README.md
```

## Data provenance (be precise about this)

- **Training: 100% synthetic** (1,700 examples from generate_data.py templates)
- **Eval set 1: synthetic held-out** (300 examples, same templates — easy)
- **Eval set 2: REAL** — 20 hand-labeled ATCO2 transcripts (European ATC audio
  transcripts). Never used in training. This is the honest number.

## Current metrics (benchmark.py, post flight-level + ordering fixes)

| Metric | LLM (llama3.2:3b + rules) | BERT (DistilBERT + rules) |
|---|---|---|
| Synthetic intent (n=100 held-out) | 93.0% | 100.0% |
| REAL intent (ATCO2, n=20) | **90.0% (18/20)** | **100.0% (20/20)** |
| Real callsign (shared rules) | 20/20 | 20/20 |
| Real heading (shared rules) | 3/3 | 3/3 |
| Latency p50 | ~650ms | **~4ms (~150x faster)** |
| Deterministic | yes (`temperature=0`) | yes by construction |

**Headline: BERT trained in ~17s on synthetic-only data now matches or beats a
3B-parameter LLM on real ATC audio, at ~150x lower latency.** Two data-quality
fixes closed the gap — see below.

## Known issues / open items

1. ~~LLM non-determinism~~ **FIXED:** `temperature=0` on the Ollama request.
2. ~~Duplicate `d["callsign"]` line~~ **FIXED** (removed).
3. ~~BERT real-data eval not run~~ **FIXED:** bert_parser.py built, wired into
   benchmark.py. BERT now at 20/20 (100%) on real_test.jsonl.
4. ~~BERT's only 2 real misses were flight-level altitudes~~ **FIXED:**
   generate_data.py's gen_altitude_change only ever produced US-GA-style
   altitudes ("three thousand"); real ATC used European/IFR "flight level
   seven zero" phrasing BERT had never seen. Added a 35%-probability flight-level
   branch, regenerated (1700/300, 8 balanced classes), retrained. BERT closed
   from 18/20 to 20/20 on real data.
5. ~~LLM synthetic accuracy dropped after adding frequency_change/hold~~ **FIXED:**
   added one few-shot example each to SYSTEM_PROMPT (previously zero examples of
   either intent) — same fairness fix given to BERT above.
6. ~~Real architecture bug: validate() ran on the LLM's raw heading_deg/altitude_ft
   BEFORE the rule-based overrides applied~~ **FIXED:** reordered parse_instruction()
   so callsign/heading/altitude are rule-extracted first, then validate() runs on
   the corrected values. Previously, an LLM hallucination like heading_deg=1000 for
   "one zero zero" (should be 100) triggered validate()'s range check and nuked
   intent to "unknown" — even though the rule-extracted heading_deg=100.0 would have
   overwritten the bad number moments later anyway. This directly violated the
   project's own design principle ("rules extract every value") by letting a
   soon-to-be-discarded LLM number veto the intent. Fixing the order recovered LLM
   real intent from 17/20 to 18/20.
7. ~~benchmark.py mislabeled the synthetic dataset as "(300)"~~ **FIXED:** it was
   actually capped to the first 100 rows via `limit = 100 if "synthetic" in dname`
   (deliberate, to keep LLM runtime sane) — label now correctly reads "(100)".
8. Remaining LLM real misses (2/20, both genuine, not pipeline bugs):
   - Long utterance with "cleared for takeoff" at the very end after lots of
     route/wind context -> "unknown".
   - Compound/unusual phrasing: "when departure low defined climb to flight level
     nine zero" -> "unknown".
9. ~~extract_altitude() doesn't handle flight levels~~ **FIXED (Week 6 Day 1):**
   added extract_flight_level() to atc_numbers.py ("flight level seven zero" ->
   7000.0; FL range 10–450 enforced); extract_altitude() checks flight level
   first (an utterance won't contain both). Real-data altitude values: 5/5.
10. `set_heading()` (GUIDED yaw) unreliable on fixed-wing — planned fix in Week 6:
    project heading into a waypoint and call goto_waypoint.
11. RTL only lands if a mission with DO_LAND_START+LAND is loaded; mission upload
    from code is a Week 6 TODO.
12. LLM cold start ~8s after Ollama restart — live system needs a warmup query.
13. System-Python leftover packages from the env saga — dead weight, no urgency.
14. **bert_parser.py doesn't extract runway numbers** — `runway` is hardcoded
    `None` always (comment: "LLM extracted this; BERT pipeline doesn't (yet)").
    Confirmed live in Week 5 voice pipeline testing: "cleared for takeoff runway
    two seven" parsed correctly as `takeoff_clearance` but with `rwy=None`.
    readback.py's takeoff/landing branches now guard this correctly (FIXED:
    they used to silently emit "Cleared for takeoff runway , N172AB" — a
    malformed readback that looked like a confirmed clearance with the runway
    silently blanked; now they emit "Say again runway" instead, matching the
    existing heading/altitude/frequency degradation pattern). The underlying
    extraction gap is now **FIXED (Week 6 Day 1):** extract_runway() in
    atc_numbers.py handles "runway two seven" -> "27", side letters ("one
    eight left" -> "18L"), leading zeros ("zero four" -> "04"), range check
    1–36, plus a keyword-less fallback anchored on a side word for real ATC
    phrasing ("one six right cleared to land" -> "16R" — the anchor means
    bare digit runs like headings/winds can never match). Wired into
    bert_parser.py. Real-data runway values: 12/12 (was 0/12). readback.py
    also gained spoken_runway() ("18L" -> "one eight left" for TTS) and its
    altitude readback is now direction-neutral ("Maintain seven thousand" —
    it used to say "Climb and maintain" even for descend instructions).
15. **Week 6 supervisor should be suspicious of "all extracted values None"
    intents, not just missing individual values.** Observed live: BERT given a
    bare, truncated utterance ("Cessna one seven two alpha bravo" with nothing
    else — audio cut off before the actual instruction) had to pick some
    intent out of 8 classes and guessed `heading_change`. The readback
    ("Say again heading") is safe in isolation (asks for clarification, cedes
    no wrong action) but commits to the guessed intent's phrasing — a
    controller who actually said a garbled landing clearance would hear "say
    again heading" and could reasonably be confused about what was
    unintelligible. When callsign is the *only* thing extracted and every
    other field is None, the supervisor should prefer a generic "say again"
    over trusting the classified intent. No code change yet — flagging for
    the Week 6 supervisor design.
16. **Shortened callsigns (no make word) are ignored — standard ATC phrasing
    misses.** Observed live in Week 5: "One seven two alpha bravo, turn left
    heading two seven zero" (no "Cessna" — normal controller shorthand after
    first contact) -> extract_callsign() returns None -> FOR ME: False ->
    silence. Fail-safe in the right direction, but real ATC uses the short
    form constantly. Do NOT just loosen the MAKES-word gate in callsign.py —
    it exists to stop airline-style callsigns ("Fraction One Zero Three
    Mike") from false-matching, an earned fix from eval failures. Better
    design for Week 6: when open extraction finds nothing, fall back to a
    targeted search for OUR OWN callsign's spoken form ("one seven two alpha
    bravo" appearing verbatim in the text -> it's us). matches() already
    anticipates suffix shortening; this is the extraction-side counterpart.
    **FIXED (Week 6 Day 1):** contains_my_callsign() in callsign.py builds our
    callsign's spoken token sequence and searches for it (full form or any
    suffix >= 3 tokens; tree/fife/niner spoken variants normalized). MAKES
    gate untouched — airline callsigns still rejected, and N172AD's short
    form still doesn't match N172AB. pipeline.py ownership check is now
    two-tier: `matches(extracted, MY) or contains_my_callsign(text, MY)`.
    Verified: the exact live-miss utterance now gets a correct readback.
17. **ArduPilot's own failsafes are currently all disabled — the software
    is the only safety net, and it has no fallback if it crashes.**
    Checked live (Week 7 Day 3) via direct param query against the sim's
    default (post `-w` wipe, pre-`ensure_sim_params()`) state:
    `FS_LONG_ACTN=0`, `FS_SHORT_ACTN=0`, `FS_GCS_ENABL=0`,
    `BATT_FS_LOW_ACT=0`, `BATT_FS_CRT_ACT=0`, `BATT_LOW_VOLT=0`,
    `BATT_CRT_VOLT=0` — every failsafe action and every battery-voltage
    threshold is off. `ensure_sim_params()` does not touch any of these;
    it only sets `ARMING_SKIPCHK`, `RTL_AUTOLAND`, `WP_RADIUS`. Verified
    live: took a plane airborne (TAKEOFF mode, ~50m), `kill -9`'d the
    controlling process, waited 60s with zero controlling software
    running, then reconnected fresh. The plane was still armed, still in
    TAKEOFF mode, still holding altitude, actively maneuvering (heading
    had changed) — TAKEOFF mode's own internal altitude/position hold,
    not any ArduPilot failsafe, which never fired because none are
    configured. In real-hardware terms: "software crashed" currently
    means "plane keeps flying with nobody home," not "plane comes home
    safely." Before flying real hardware, `FS_GCS_ENABL` (act on lost
    telemetry) and sane `BATT_FS_*`/`BATT_*_VOLT` values need to be set
    deliberately — this is a pre-flight checklist item, not optional.
18. **Anomalously long/padded instruction text could misclassify intent —
    a genuine safety-relevant bug, found and fixed in Week 9's adversarial
    audit.** BERT's tokenizer truncates at 64 subword tokens; padding an
    instruction with enough filler pushes the real instruction past that
    window, and BERT classifies whatever's left instead of the actual
    instruction. Verified: a real "cleared for takeoff" was classified as
    frequency_change once buried under ~60+ words of filler — not a safe
    fallback, an actual wrong classification. Rule-based slot extraction
    (runway/heading/altitude/frequency) is unaffected since it always
    scans the full untruncated text. **FIXED:** `MAX_REASONABLE_WORDS = 40`
    sanity gate in bert_parser.py forces intent="unknown" (safe — "say
    again") on anomalously long text, rather than trusting a truncation
    artifact. Deliberately not a BERT retrain (out of scope this week,
    would risk disturbing the Week 4 benchmark).
19. **extract_callsign() picked the wrong callsign on multi-callsign
    utterances.** When a transmission named both our callsign and another
    aircraft's (e.g. a traffic advisory), the "pick the longest candidate"
    heuristic could select the OTHER aircraft's callsign if it happened to
    produce a longer alphanumeric string — even though ours was named
    first (real ATC phraseology addresses the target aircraft first). The
    ownership gate itself was never actually fooled (pipeline.py's
    contains_my_callsign() fallback independently confirms ownership), but
    the logged instruction callsign was factually wrong. **FIXED (Week 9):**
    take the first candidate run instead of the longest.
20. **Numeral-form parsing was still broken in three more extractors.**
    Week 7 fixed extract_heading()/extract_altitude() failing on
    numeral-form ASR output ("270" vs "two seven zero") — their word-only
    tokenization regex can't see digit characters at all. Week 9's
    adversarial audit found the identical gap, never fixed, in
    extract_flight_level(), extract_runway(), and extract_frequency().
    **FIXED:** same numeral-fallback pattern (raw-text regex anchored on
    the relevant keyword) applied to all three.

## Roadmap (remaining)

- ~~**Week 4:** temp=0 fix -> stable LLM baseline -> bert_parser.py -> head-to-head
  benchmark~~ **DONE** — see docs/benchmark.md.
- ~~**Week 5:** Voice — faster-whisper -> parser -> template readback -> Piper TTS~~
  **DONE** — live end to end, <1s response.
- ~~**Week 6:** Supervisor — envelope validation, flight-phase state machine, callsign
  gate, JSONL decision logging. Mission upload from code + heading->waypoint.~~
  **DONE** — see docs/week6_milestone.md for the first fully voice-commanded flight
  (takeoff -> airborne (telemetry-confirmed) -> heading change -> landing clearance
  -> touchdown (telemetry-confirmed), all five steps traced in decisions.jsonl).
- ~~**Week 7:** Integration.~~ **DONE** — main.py single entry point +
  docs/RUNBOOK.md; idempotency tests (duplicate takeoff/landing clearance
  correctly rejected, repeated heading correctly accepted — found and
  fixed a real gap: PHASE_RULES["approach"] still allowed a redundant
  landing_clearance); documented that ArduPilot ships with zero
  failsafes configured (verified live: killed the controlling process
  mid-flight, plane kept flying with no intervention — a real
  hardware-readiness gap, not fixed, flagged for pre-flight checklist);
  built a no-voice reliability harness (scripts/day4_reliability_run.py,
  TTS-synthesized ATC through the real pipeline) and used it to find and
  fix two real bugs — extract_heading()/extract_altitude() couldn't
  parse numeral-form numbers ("270"/"1500" vs "two seven zero"/"one
  thousand five hundred", since Whisper renders both forms
  unpredictably), and a mavlink connection race between arm() and the
  telemetry-polling thread that ate a COMMAND_ACK. Final 5x reliability
  run: 5/5 clean.
- ~~**Week 8:** Scenario library — 4 scenarios + 1 failure demo, repeatable
  via TTS-synthesized ATC.~~ **DONE** — see scenarios/README.md.
  pattern_flight, vectors_and_altitude, straight_in_approach,
  multi_instruction_sequence (exercises Week 7's idempotency rule live),
  and go_around (the failure showcase — timed to call a go-around while
  genuinely on final approach, before touchdown; confirmed via
  decisions.jsonl that phase reads "approach" at the exact moment,
  proving the Week 6 Day 3 phase transition works under real timing
  pressure). Found and fixed two more real gaps along the way:
  bert_parser.py never extracted frequency values at all
  (frequency: None hardcoded, no extract_frequency() existed), and
  "cleared straight-in approach runway X" misclassifies as
  takeoff_clearance (a synthetic-training-data gap, worked around with
  alternate phrasing rather than retraining). scenarios/run_all.py runs
  every scenario N times against a freshly-relaunched SITL each time and
  tabulates pass/fail — a 5x robustness pass is the Day 5 bar.
- ~~**Week 9:** Adversarial suite (similar callsigns, garbled audio, phase-invalid
  instructions) — supervisor must pass 100%.~~ **DONE** — see
  docs/security_notes.md and tests/test_adversarial.py (28 tests, 100%
  pass). One real, safety-relevant bug found and fixed: padding an
  instruction with enough filler text pushed it past BERT's 64-token
  truncation window and caused genuine intent MISCLASSIFICATION (a
  verified "cleared for takeoff" was classified as frequency_change) —
  fixed with a word-count sanity gate forcing intent=unknown on
  anomalously long input, not a BERT retrain. Also found and fixed:
  extract_callsign() picked the LONGEST candidate callsign on
  multi-callsign text instead of the first (real ATC phraseology
  addresses the target aircraft first); numeral-form parsing was still
  broken (same class of gap as Week 7's heading/altitude fix) in
  extract_flight_level/extract_runway/extract_frequency, all three
  fixed. BERT's fixed 8-label classification space is structurally
  immune to free-text prompt injection by design — documented, not
  re-tested every time. scenarios/lib.py::premature_landing_clearance
  added as the one live-SITL timing case (landing clearance immediately
  after takeoff, before telemetry advances phase past "takeoff") —
  confirms the phase gate uses actual current state, not assumed state.
- **Week 10 (now):** Buffer / stretch (CV runway detection descoped to stretch).
- **Weeks 11–12:** Overlay dashboard, record, edit, publish. Production time is sacred.

## Suggested review areas

- flight_api.py: no reconnect logic; set_mode uses deprecated set_mode_send and
  doesn't verify the change via HEARTBEAT; telemetry getters may return stale
  queued messages.
- eval harness: add altitude+runway accuracy and an intent confusion matrix;
  after temp=0, consider mean±std over 3 runs as standard practice for any
  stochastic component.
- tests: mark SITL-dependent tests with @pytest.mark.sitl; add pure unit tests
  for callsign.py and atc_numbers.py (CI-friendly, no SITL).
