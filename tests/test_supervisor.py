import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "supervisor"))
from supervisor import Supervisor


def make_trace(intent, for_me=True, **values):
    instr = {"callsign": "N172AB", "intent": intent, "heading_deg": None,
             "altitude_ft": None, "runway": None, "frequency": None}
    instr.update(values)
    return {"transcript": "test", "for_me": for_me, "instruction": instr}


def test_accepts_valid_heading():
    s = Supervisor()
    s.phase = "airborne"          # phase rules: heading changes require airborne
    d = s.handle(make_trace("heading_change", heading_deg=270))
    assert d["verdict"] == "ACCEPT"

def test_rejects_wrong_callsign():
    d = Supervisor().handle(make_trace("heading_change", for_me=False,
                                       heading_deg=270))
    assert d["verdict"] == "REJECT"
    assert d["checks"][-1]["check"] == "ownership"

def test_rejects_unknown_intent():
    d = Supervisor().handle(make_trace("unknown"))
    assert d["verdict"] == "REJECT"

def test_rejects_missing_value():          # issue #15
    s = Supervisor()
    s.phase = "airborne"          # altitude_change is phase-valid here
    d = s.handle(make_trace("altitude_change"))
    assert d["verdict"] == "REJECT"
    assert d["checks"][-1]["check"] == "values_present"

def test_rejects_altitude_above_envelope():
    s = Supervisor()
    s.phase = "airborne"
    d = s.handle(make_trace("altitude_change", altitude_ft=7000))
    assert d["verdict"] == "REJECT"
    assert d["checks"][-1]["check"] == "envelope"

def test_dry_run_reports_action():
    s = Supervisor()
    s.phase = "airborne"
    d = s.handle(make_trace("heading_change", heading_deg=90))
    assert "DRY-RUN" in d["action"]


# ---------- Day 3: flight-phase state machine ----------

def test_rejects_takeoff_when_airborne():
    s = Supervisor()
    s.phase = "airborne"
    d = s.handle(make_trace("takeoff_clearance", runway="27"))
    assert d["verdict"] == "REJECT"
    assert d["checks"][-1]["check"] == "phase"

def test_rejects_heading_change_on_ground():
    d = Supervisor().handle(make_trace("heading_change", heading_deg=270))
    assert d["verdict"] == "REJECT"          # phase=ground by default

def test_takeoff_clearance_advances_phase():
    s = Supervisor()
    d = s.handle(make_trace("takeoff_clearance", runway="27"))
    assert d["verdict"] == "ACCEPT"
    assert s.phase == "takeoff"

def test_telemetry_advances_to_airborne():
    s = Supervisor()
    s.phase = "takeoff"
    s.update_from_telemetry(45.0)
    assert s.phase == "airborne"

def test_go_around_returns_to_airborne():
    s = Supervisor()
    s.phase = "approach"
    d = s.handle(make_trace("go_around"))
    assert d["verdict"] == "ACCEPT"
    assert s.phase == "airborne"