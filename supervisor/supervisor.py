import json
import time
import os

# ---------- Envelope: the hard limits ----------
# Sim values today. For hardware these tighten (400ft AGL legal ceiling,
# geofence = field boundary). Loaded from one place so that swap is one edit.
ENVELOPE = {
    "alt_min_m": 30,
    "alt_max_m": 150,
    "heading_min": 0,
    "heading_max": 360,
    "max_heading_delta": 180,     # reject absurd turn requests
    "geofence_radius_m": 2000,    # from home; checked when position known
}

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "decisions.jsonl")

# ---------- Phase model ----------
# Which intents are acceptable in which phase. Anything absent = rejected.
PHASE_RULES = {
    "ground":   {"takeoff_clearance", "hold", "frequency_change"},
    "takeoff":  {"altitude_change", "frequency_change"},
    "airborne": {"heading_change", "altitude_change", "landing_clearance",
                 "hold", "frequency_change"},
    "approach": {"go_around", "landing_clearance", "heading_change",
                 "altitude_change", "frequency_change"},
}

# Executing an instruction can move us to a new phase:
PHASE_TRANSITIONS = {
    ("ground", "takeoff_clearance"): "takeoff",
    ("airborne", "landing_clearance"): "approach",
    ("approach", "go_around"): "airborne",
}


class Supervisor:
    """Gatekeeper between parsed instructions and the aircraft.
    Proposes nothing, permits or denies everything."""

    def __init__(self, flight_api=None):
        self.fc = flight_api          # None = validation-only (dry run) mode
        self.phase = "ground"         # Day 3 wires the full state machine

    # ---------- The one public entry point ----------
    def handle(self, trace: dict) -> dict:
        """Takes the pipeline trace (instruction + metadata),
        returns a decision record. Executes only if all gates pass."""
        instr = trace["instruction"]
        decision = {
            "ts": time.time(),
            "transcript": trace.get("transcript"),
            "instruction": instr,
            "phase": self.phase,
            "checks": [],
            "verdict": None,
            "action": None,
        }

        ok = True
        for check in (self._check_ownership, self._check_intent_known,
                      self._check_phase, self._check_values_present,
                      self._check_envelope):
            name, passed, detail = check(trace)
            decision["checks"].append(
                {"check": name, "passed": passed, "detail": detail})
            if not passed:
                ok = False
                break                  # first failure wins; no partial credit

        decision["verdict"] = "ACCEPT" if ok else "REJECT"
        if ok:
            decision["action"] = self._execute(instr)
            new_phase = PHASE_TRANSITIONS.get((self.phase, instr["intent"]))
            if new_phase:
                decision["phase_transition"] = f"{self.phase} -> {new_phase}"
                self.phase = new_phase

        self._log(decision)
        return decision

    # ---------- Gates ----------
    def _check_ownership(self, trace):
        return ("ownership", bool(trace.get("for_me")),
                "instruction addressed to us" if trace.get("for_me")
                else "not our callsign")

    def _check_intent_known(self, trace):
        intent = trace["instruction"]["intent"]
        return ("intent_known", intent != "unknown", f"intent={intent}")

    def _check_phase(self, trace):
        intent = trace["instruction"]["intent"]
        allowed = PHASE_RULES.get(self.phase, set())
        return ("phase", intent in allowed,
                f"intent={intent} in phase={self.phase} "
                f"({'allowed' if intent in allowed else 'not allowed'})")

    def _check_values_present(self, trace):
        """Issue #15: an intent whose required value is missing is suspect —
        the instruction was probably truncated. Never guess."""
        instr = trace["instruction"]
        required = {
            "heading_change": "heading_deg",
            "altitude_change": "altitude_ft",
            "frequency_change": "frequency",
        }
        field = required.get(instr["intent"])
        if field is None:
            return ("values_present", True, "no value required")
        present = instr.get(field) is not None
        return ("values_present", present,
                f"{field}={'present' if present else 'MISSING'}")

    def _check_envelope(self, trace):
        instr = trace["instruction"]
        if instr["intent"] == "altitude_change":
            alt_m = instr["altitude_ft"] * 0.3048
            if not (ENVELOPE["alt_min_m"] <= alt_m <= ENVELOPE["alt_max_m"]):
                return ("envelope", False,
                        f"altitude {alt_m:.0f}m outside "
                        f"[{ENVELOPE['alt_min_m']}, {ENVELOPE['alt_max_m']}]m")
        if instr["intent"] == "heading_change":
            h = instr["heading_deg"]
            if not (ENVELOPE["heading_min"] <= h <= ENVELOPE["heading_max"]):
                return ("envelope", False, f"heading {h} invalid")
        return ("envelope", True, "within limits")

    def update_from_telemetry(self, alt_m: float):
        """Called periodically with live altitude. Physics-driven transitions.
        Clearance-driven and physics-driven transitions are never
        interchangeable: ATC saying 'cleared to land' puts you on approach;
        only the altimeter actually puts you on the ground."""
        if self.phase == "takeoff" and alt_m > 30:
            self._log({"ts": time.time(), "event": "phase_transition",
                       "detail": f"takeoff -> airborne at {alt_m:.0f}m"})
            self.phase = "airborne"
        elif self.phase == "approach" and alt_m < 5:
            self._log({"ts": time.time(), "event": "phase_transition",
                       "detail": f"approach -> ground at {alt_m:.0f}m"})
            self.phase = "ground"

    # ---------- Execution (only reached after all gates pass) ----------
    def _execute(self, instr) -> str:
        if self.fc is None:
            return f"DRY-RUN: would execute {instr['intent']}"
        intent = instr["intent"]
        if intent == "takeoff_clearance":
            self.fc.takeoff(50)
            return "takeoff commanded, target 50m"
        if intent == "altitude_change":
            alt_m = instr["altitude_ft"] * 0.3048
            self.fc.goto_altitude(alt_m)
            return f"altitude change to {alt_m:.0f}m commanded"
        if intent == "heading_change":
            self.fc.fly_heading(instr["heading_deg"])   # Day 4 builds this
            return f"heading {instr['heading_deg']} commanded"
        if intent == "landing_clearance":
            self.fc.rtl()
            return "RTL/land commanded"
        if intent == "go_around":
            self.fc.goto_altitude(80)
            return "go-around: climb to 80m commanded"
        if intent == "hold":
            self.fc.loiter()
            return "loiter commanded"
        if intent == "frequency_change":
            return f"frequency {instr['frequency']} acknowledged (no flight action)"
        return "no action mapped"

    # ---------- Audit trail ----------
    def _log(self, decision):
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(decision) + "\n")
            