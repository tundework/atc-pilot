# Week 6 milestone: first fully voice-commanded flight

2026-07-10. Spoken ATC instructions, captured on the Windows side via
`win_capture.ps1`, transcribed and parsed in WSL2, gated by the phase-aware
`Supervisor`, and executed live against ArduPilot SITL through `FlightAPI` —
no manual flight-control input anywhere in the loop.

## The proof: `supervisor/decisions.jsonl`

```
ACCEPT   ground    takeoff_clearance         (15:13:13, spoken command)
PHASE    takeoff -> airborne at 46m          (~8s later, telemetry-driven, not clearance-driven)
ACCEPT   airborne  heading_change            (15:14:11, spoken command)
ACCEPT   airborne  landing_clearance         (15:14:48, spoken command -> RTL)
PHASE    approach -> ground at 3m            (~66s later, telemetry-driven touchdown)
```

Every verdict is traceable to named gates (`ownership`, `intent_known`,
`phase`, `values_present`, `envelope`) logged alongside it. The two `PHASE`
lines are the load-bearing detail: the aircraft declared itself airborne and,
later, on the ground based on the **altimeter**, not because ATC said so —
clearance-driven and physics-driven phase transitions are deliberately kept
separate (see `supervisor.py`'s `update_from_telemetry`).

## A correct non-event, not a bug

A second recording that session ("turn left heading to seven zero") was
transcribed with **no callsign at all**, not even a shortened form, and the
pipeline stayed silent rather than guess it was addressed to us. This is the
Week 3 fail-safe design (never let the model invent a callsign) doing exactly
its job — it cost that run a captured phase-gate-*reject* shot (a heading
change spoken during the `takeoff` phase, before crossing 30m, should be
rejected), which is worth re-capturing deliberately given how fast this
airframe climbs (0->46m in ~8s in SITL).

## What this closes

Week 6 roadmap, all five days:

| Day | Delivered |
|---|---|
| 1 | Flight-level altitudes, runways, short-form callsigns — 3 extraction gaps closed |
| 2-3 | Supervisor core — 4 gates, JSONL audit trail, flight-phase state machine |
| 4 | Verified `FlightAPI` calls, real turns (`goto_waypoint` fix via `MAV_CMD_DO_REPOSITION`), real landings, a Null Island GPS-race bug found and fixed |
| 5 | Full voice-to-flight wiring — proven live, this document |

Weeks 1-6 built every component; Weeks 7-12 turn it into a demonstrable,
filmable, shippable thing.
