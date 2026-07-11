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

    # Separate connection for telemetry polling — sharing fc's single
    # mavutil connection across threads let the poller's recv_match race
    # arm()'s recv_match(type="COMMAND_ACK") on the same socket. pymavlink
    # dispatches whichever message arrives to whichever thread happens to
    # call recv_match next, regardless of the type filter each thread
    # asked for; the poller's GLOBAL_POSITION_INT read could silently
    # consume the ACK arm() was waiting for. Observed live: a 5-run
    # reliability test failed once with "Arming REFUSED (ack=none)" — no
    # ack arrived at all, not a real pre-arm-check rejection. SITL accepts
    # multiple simultaneous clients over TCP without issue (only the
    # earlier port-contention bug involved MAVProxy fighting over the same
    # port as a direct FlightAPI connection); a second independent
    # connection here is safe.
    telemetry_fc = FlightAPI(connection_string=fc.connection_string)
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

    print("Worker ready, waiting for recordings from watch.py ... (Ctrl+C to stop)")
    with open(QUEUE_FILE, "r") as q:
        # Seek to end: the queue file is never truncated across runs (by
        # design — watch.py only appends), so opening at position 0 would
        # silently replay every recording ever queued, from every past
        # session, on every worker restart. Observed live: a fresh start
        # replayed an entire prior flight (RTL and landing) with no mic
        # input. Only lines appended AFTER this process starts are ours.
        q.seek(0, os.SEEK_END)
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
