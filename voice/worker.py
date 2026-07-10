"""voice/worker.py — loads the models once, then tails watch.py's queue file.

Never lists /mnt/c directory contents itself (see watch.py's docstring for
why) — only reads appended lines from a local queue file, which is
unaffected by the caching issue since it never goes stale here.
"""
import glob
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "supervisor"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "flight_api"))

from pipeline import process_audio, transcribe, parse_instruction
from supervisor import Supervisor
from flight_api import FlightAPI

QUEUE_FILE = "/tmp/atc_pipeline_queue.txt"


def handle_recording(wav_path, supervisor):
    # process_audio already speaks the readback internally (see speak()
    # call in pipeline.py) — a controller always reads back, even for
    # instructions the supervisor's gates end up rejecting. The supervisor
    # only gates whether the aircraft ACTS on it, not whether we speak.
    trace = process_audio(wav_path, verbose=True)

    if not trace.get("for_me"):
        return   # pipeline already handled the "stay silent" case

    decision = supervisor.handle(trace)
    print(f"  SUPERVISOR: {decision['verdict']}")
    for c in decision["checks"]:
        mark = "OK " if c["passed"] else "FAIL"
        print(f"    [{mark}] {c['check']}: {c['detail']}")
    if decision.get("action"):
        print(f"  ACTION: {decision['action']}")
    if decision.get("phase_transition"):
        print(f"  PHASE: {decision['phase_transition']}")


if __name__ == "__main__":
    open(QUEUE_FILE, "a").close()

    # Warm up from local disk only — never /mnt/c (see watch.py docstring)
    here = os.path.dirname(os.path.abspath(__file__))
    warmup_candidates = (glob.glob(os.path.join(here, "incoming", "*.wav"))
                         or glob.glob(os.path.join(here, "*.wav")))
    if warmup_candidates:
        transcribe(max(warmup_candidates, key=os.path.getsize))
    parse_instruction("warmup")

    print("Connecting to SITL...")
    fc = FlightAPI()
    fc.connect()
    fc.ensure_sim_params()
    fc.set_mode("MANUAL")          # clear any leftover mode from a prior run
    fc.upload_landing_mission(land_heading_deg=0)
    print("Landing mission uploaded. Aircraft ready on the ground.")

    supervisor = Supervisor(flight_api=fc)

    def telemetry_loop():
        while True:
            try:
                pos = fc.get_position()
                supervisor.update_from_telemetry(pos["alt_m"])
            except Exception as e:
                print(f"  telemetry poll error: {e}")
            time.sleep(1.5)

    threading.Thread(target=telemetry_loop, daemon=True).start()

    print("Worker ready, waiting for recordings from watch.py ... (Ctrl+C to stop)")
    with open(QUEUE_FILE, "r") as q:
        try:
            while True:
                line = q.readline()
                if not line:
                    time.sleep(0.3)
                    continue
                try:
                    handle_recording(line.strip(), supervisor)
                except Exception as e:
                    # One bad file must not kill the worker
                    print(f"ERROR processing {line.strip()}: {e}")
        except KeyboardInterrupt:
            print("\nStopped.")
