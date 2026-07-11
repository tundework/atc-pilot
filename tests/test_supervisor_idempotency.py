"""Week 7 Day 2 — defined behavior for repeated instructions.

Real ATC repeats things; real pilots mishear and ask again. The supervisor
needs explicit, tested behavior for repeats, not accidental behavior:
re-affirming a value (heading) you're already flying is harmless and
should be accepted again, but re-issuing a clearance that already moved
the phase forward is redundant and should be rejected — same pattern the
phase gate already uses for a duplicate takeoff_clearance.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "supervisor"))
from supervisor import Supervisor


def make_trace(intent, for_me=True, **values):
    instr = {"callsign": "N172AB", "intent": intent, "heading_deg": None,
             "altitude_ft": None, "runway": None, "frequency": None}
    instr.update(values)
    return {"transcript": "test", "for_me": for_me, "instruction": instr}


def test_duplicate_takeoff_clearance_second_rejected():
    """Already covered by the phase gate — verify explicitly, name it."""
    s = Supervisor()
    d1 = s.handle(make_trace("takeoff_clearance", runway="27"))
    d2 = s.handle(make_trace("takeoff_clearance", runway="27"))
    assert d1["verdict"] == "ACCEPT"
    assert d2["verdict"] == "REJECT"
    assert d2["checks"][-1]["check"] == "phase"


def test_duplicate_heading_same_value_accepted_both():
    """A controller re-confirming a heading you're already flying should
    NOT be rejected — that's a legitimate, harmless repeat."""
    s = Supervisor()
    s.phase = "airborne"
    d1 = s.handle(make_trace("heading_change", heading_deg=270))
    d2 = s.handle(make_trace("heading_change", heading_deg=270))
    assert d1["verdict"] == "ACCEPT"
    assert d2["verdict"] == "ACCEPT"   # re-affirming is fine, not spam


def test_landing_clearance_after_landing_clearance_rejected():
    s = Supervisor()
    s.phase = "airborne"
    d1 = s.handle(make_trace("landing_clearance"))
    assert d1["verdict"] == "ACCEPT"
    assert s.phase == "approach"
    d2 = s.handle(make_trace("landing_clearance"))
    assert d2["verdict"] == "REJECT"   # already committed to approach
    assert d2["checks"][-1]["check"] == "phase"
