"""Week 7 Day 4 — reliability run, no human voice required.

Synthesizes the mission's spoken instructions via Piper TTS (same engine
speak.py uses for readbacks) and drops them into the exact folder
win_capture.ps1 would, as tx_<timestamp>.wav files. watch.py and worker.py
run completely unmodified — they can't tell the difference between a
synthesized instruction and a real one, which is the point: this exercises
the real ASR -> parse -> supervisor -> flight_api path, not a mock of it.

Runs the same mission N times back to back against a freshly-relaunched
SITL each time, and reports pass/fail per run based on decisions.jsonl.

Usage: python scripts/day4_reliability_run.py [n_runs]
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_DIR = os.path.join(ROOT, "voice")
SUPERVISOR_LOG = os.path.join(ROOT, "supervisor", "decisions.jsonl")
WATCH_DIR = "/mnt/c/atc_voice_samples/"
SITL_DIR = os.path.expanduser("~/ardupilot/ArduPlane")

sys.path.insert(0, VOICE_DIR)
os.chdir(VOICE_DIR)   # speak.py loads its Piper model via a relative path
from speak import speak  # noqa: E402

MISSION = [
    "Cessna one seven two alpha bravo, cleared for takeoff runway two seven",
    "Cessna one seven two alpha bravo, turn left heading two seven zero",
    # 400ft (~122m) — must stay inside supervisor.ENVELOPE's alt range
    # ([30, 150]m for this sim); 1500ft (457m) was tried first and got
    # correctly REJECTed by the envelope gate, not a bug.
    "Cessna one seven two alpha bravo, climb and maintain four hundred",
    "Cessna one seven two alpha bravo, cleared to land runway two seven",
]

_counter = 0


def synth_and_queue(text):
    global _counter
    _counter += 1
    stamp = time.strftime("%Y%m%d_%H%M%S") + f"_{_counter:02d}"
    out = os.path.join(WATCH_DIR, f"tx_{stamp}.wav")
    speak(text, outfile=out, play=False)
    print(f"[synth] -> {out} :: {text}")


LOG_DIR = "/tmp/day4_reliability_logs"
os.makedirs(LOG_DIR, exist_ok=True)


def run_cmd(cmd, name, cwd=None):
    # stdout MUST go to a file, not subprocess.PIPE: PIPE has a small fixed
    # OS buffer, and if nothing keeps draining it the child process blocks
    # forever on its own print() once the buffer fills — a classic
    # subprocess deadlock. Observed live: run 1 (little output) worked,
    # run 2's worker silently deadlocked mid-mission because this script
    # stopped reading its stdout right after the readiness check.
    log_path = os.path.join(LOG_DIR, f"{name}.log")
    log_file = open(log_path, "w")
    p = subprocess.Popen(cmd, cwd=cwd, stdout=log_file, stderr=subprocess.STDOUT,
                         text=True, env={**os.environ, "PYTHONUNBUFFERED": "1"})
    p._log_path = log_path
    p._log_file = log_file
    return p


def kill_all():
    subprocess.run(["pkill", "-9", "-f", "sim_vehicle.py"], check=False)
    subprocess.run(["pkill", "-9", "-f", "arduplane"], check=False)
    subprocess.run(["pkill", "-9", "-f", "watch.py"], check=False)
    subprocess.run(["pkill", "-9", "-f", "worker.py"], check=False)
    time.sleep(2)


def wait_for_sitl_port(timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = subprocess.run(["ss", "-tln"], capture_output=True, text=True)
        if ":5760 " in r.stdout:
            return True
        time.sleep(2)
    return False


def launch_sitl():
    subprocess.Popen(
        ["python3", os.path.expanduser(
            "~/ardupilot/Tools/autotest/sim_vehicle.py"), "-w", "--no-mavproxy"],
        cwd=SITL_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    if not wait_for_sitl_port():
        raise RuntimeError("SITL never bound port 5760")
    time.sleep(5)   # let it settle before hammering it with connects


def launch_watcher_and_worker(run_idx):
    watcher = run_cmd([sys.executable, "watch.py"], f"watcher_run{run_idx}", cwd=VOICE_DIR)
    time.sleep(1)
    worker = run_cmd([sys.executable, "worker.py"], f"worker_run{run_idx}", cwd=VOICE_DIR)
    return watcher, worker


def wait_for_worker_ready(worker_proc, timeout=90):
    deadline = time.time() + timeout
    seen = 0
    while time.time() < deadline:
        if worker_proc.poll() is not None:
            return False   # worker died during startup
        with open(worker_proc._log_path) as f:
            content = f.read()
        if len(content) > seen:
            print(content[seen:], end="")
            seen = len(content)
        if "Worker ready" in content:
            return True
        time.sleep(0.5)
    return False


def last_decisions(since_ts):
    events = []
    if not os.path.exists(SUPERVISOR_LOG):
        return events
    with open(SUPERVISOR_LOG) as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("ts", 0) >= since_ts:
                events.append(d)
    return events


def run_one_mission(run_idx):
    print(f"\n=== RUN {run_idx}: relaunching SITL ===")
    kill_all()
    launch_sitl()

    print("=== starting watcher + worker ===")
    watcher, worker = launch_watcher_and_worker(run_idx)
    if not wait_for_worker_ready(worker):
        watcher.terminate(); worker.terminate()
        return {"run": run_idx, "result": "FAIL", "reason": "worker never became ready"}

    t_start = time.time()
    try:
        print("--- step 1: takeoff clearance ---")
        synth_and_queue(MISSION[0])
        time.sleep(20)   # climb to ~50m, telemetry poller flips takeoff->airborne

        print("--- step 2: heading change ---")
        synth_and_queue(MISSION[1])
        time.sleep(8)

        print("--- step 3: altitude change ---")
        synth_and_queue(MISSION[2])
        time.sleep(8)

        print("--- step 4: landing clearance ---")
        synth_and_queue(MISSION[3])
        time.sleep(90)   # RTL + full landing sequence

        events = last_decisions(t_start)
        verdicts = [e for e in events if "verdict" in e]
        phase_events = [e for e in events if e.get("event") == "phase_transition"]

        accepted_intents = {e["instruction"]["intent"] for e in verdicts
                            if e["verdict"] == "ACCEPT"}
        rejected = [e for e in verdicts if e["verdict"] == "REJECT"]
        landed = any("ground" in e.get("detail", "") for e in phase_events)

        expected = {"takeoff_clearance", "heading_change",
                   "altitude_change", "landing_clearance"}
        missing = expected - accepted_intents

        result = "PASS" if (not missing and landed and not rejected) else "FAIL"
        return {
            "run": run_idx,
            "result": result,
            "accepted": sorted(accepted_intents),
            "missing": sorted(missing),
            "unexpected_rejects": [r["instruction"]["intent"] for r in rejected],
            "landed": landed,
            "phase_events": [e["detail"] for e in phase_events],
        }
    finally:
        print("=== stopping watcher + worker ===")
        watcher.terminate()
        worker.terminate()
        try:
            watcher.wait(timeout=5)
        except subprocess.TimeoutExpired:
            watcher.kill()
        try:
            worker.wait(timeout=5)
        except subprocess.TimeoutExpired:
            worker.kill()
        watcher._log_file.close()
        worker._log_file.close()


if __name__ == "__main__":
    n_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    results = []
    for i in range(1, n_runs + 1):
        r = run_one_mission(i)
        results.append(r)
        print(f"\n>>> RUN {i} RESULT: {r}\n")

    print("\n" + "=" * 60)
    print("RELIABILITY RUN SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"  run {r['run']}: {r['result']}"
              + (f"  (missing={r.get('missing')}, rejects={r.get('unexpected_rejects')})"
                 if r["result"] == "FAIL" else ""))
    passed = sum(1 for r in results if r["result"] == "PASS")
    print(f"\n{passed}/{len(results)} passed")

    kill_all()
