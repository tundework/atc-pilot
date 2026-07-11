"""Run one named scenario against a freshly-connected SITL.

Usage: python run_one.py <scenario_name>
Assumes SITL is already up (same runbook as Week 7's reliability run).
"""
import os
import sys
import threading
import time

# Captured before any import below runs — run_scenario's own import chdirs
# into voice/ (so speak.py's relative model path resolves), which would
# corrupt any os.path.abspath(__file__) call made after that point.
HERE = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, HERE)
from run_scenario import run_scenario
import lib

sys.path.insert(0, os.path.join(HERE, "..", "flight_api"))
sys.path.insert(0, os.path.join(HERE, "..", "supervisor"))
from flight_api import FlightAPI
from supervisor import Supervisor

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <scenario_name>")
        print(f"Available: {[n for n in dir(lib) if not n.startswith('_') and n != 'Scenario' and n != 'ScenarioStep' and n != 'MY_CS']}")
        sys.exit(1)

    scenario = getattr(lib, sys.argv[1])

    print("Connecting to SITL...")
    fc = FlightAPI()
    fc.connect()
    fc.ensure_sim_params()
    fc.set_mode("MANUAL")
    fc.upload_landing_mission(land_heading_deg=0)
    print("Landing mission uploaded. Aircraft ready on the ground.")

    supervisor = Supervisor(flight_api=fc)

    # Telemetry poller, same pattern as voice/worker.py (and the same
    # port-separation fix from Week 7 Day 5): without this, phase never
    # advances past "takeoff"/"approach" via the altimeter, only via
    # clearance-driven transitions, so any scenario step relying on the
    # physics-driven takeoff->airborne or approach->ground flip (e.g. a
    # landing_clearance while nominally still "takeoff") gets incorrectly
    # rejected by the phase gate. Confirmed live: this exact miss happened
    # on the first scenario run before this poller was added.
    telemetry_fc = FlightAPI(connection_string="tcp:127.0.0.1:5763")
    telemetry_fc.connect()

    def telemetry_loop():
        while True:
            try:
                pos = telemetry_fc.get_position()
                supervisor.update_from_telemetry(pos["alt_m"])
            except Exception as e:
                print(f"  telemetry poll error: {e}")
            time.sleep(1.5)

    threading.Thread(target=telemetry_loop, daemon=True).start()

    out_dir = os.path.join(HERE, "out", scenario.name)
    passed = run_scenario(scenario, fc, supervisor, out_dir)
    sys.exit(0 if passed else 1)
