"""Week 8 Day 5 — robustness pass: run every scenario N times back to back
against a freshly-relaunched SITL each time, and tabulate pass/fail.

Reuses the exact orchestration pattern proven in Week 7's reliability
script: subprocess stdout goes to files, not pipes (a pipe's small fixed
OS buffer caused a real silent deadlock there once a worker produced
enough output — see scripts/day4_reliability_run.py's history).

Usage: python run_all.py [n_repeats]   (default 5)
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FLIGHT_API_DIR = os.path.join(ROOT, "flight_api")
SUPERVISOR_DIR = os.path.join(ROOT, "supervisor")
SUPERVISOR_LOG = os.path.join(SUPERVISOR_DIR, "decisions.jsonl")
SITL_DIR = os.path.expanduser("~/ardupilot/ArduPlane")
LOG_DIR = "/tmp/scenario_run_all_logs"

sys.path.insert(0, HERE)
import lib  # noqa: E402

SCENARIOS = [
    lib.pattern_flight,
    lib.vectors_and_altitude,
    lib.straight_in_approach,
    lib.multi_instruction_sequence,
    lib.go_around_scenario,
]


def kill_all():
    subprocess.run(["pkill", "-9", "-f", "sim_vehicle.py"], check=False)
    subprocess.run(["pkill", "-9", "-f", "arduplane"], check=False)
    time.sleep(2)


def wait_for_sitl_port(timeout=90):
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
    time.sleep(5)


def run_one_scenario_subprocess(scenario_name, run_idx, repeat_idx):
    """run_one.py in its own process (own model load, own connections) —
    matches Week 7's proven pattern rather than trying to share one
    long-lived process across many scenario runs."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"{scenario_name}_rep{repeat_idx}.log")
    with open(log_path, "w") as log_file:
        p = subprocess.Popen(
            [sys.executable, "run_one.py", scenario_name],
            cwd=HERE, stdout=log_file, stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        p.wait(timeout=600)
    return p.returncode == 0


def run_repeat(repeat_idx, n_total):
    results = {}
    for scenario in SCENARIOS:
        print(f"\n=== [{repeat_idx}] relaunching SITL for {scenario.name} ===")
        kill_all()
        launch_sitl()
        t0 = time.time()
        try:
            passed = run_one_scenario_subprocess(scenario.name, repeat_idx, repeat_idx)
        except subprocess.TimeoutExpired:
            passed = False
            print(f"  TIMEOUT running {scenario.name}")
        elapsed = time.time() - t0
        results[scenario.name] = passed
        print(f"  [{scenario.name}] {'PASS' if passed else 'FAIL'} ({elapsed:.0f}s)")
    return results


if __name__ == "__main__":
    n_repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    all_results = []
    for r in range(1, n_repeats + 1):
        all_results.append(run_repeat(r, n_repeats))

    print("\n" + "=" * 70)
    print("ROBUSTNESS PASS SUMMARY")
    print("=" * 70)
    header = "repeat".ljust(8) + "".join(s.name.ljust(24) for s in SCENARIOS)
    print(header)
    for i, res in enumerate(all_results, 1):
        row = str(i).ljust(8)
        for s in SCENARIOS:
            row += ("PASS" if res[s.name] else "FAIL").ljust(24)
        print(row)

    print("\nPer-scenario totals:")
    for s in SCENARIOS:
        passed = sum(1 for res in all_results if res[s.name])
        print(f"  {s.name}: {passed}/{n_repeats}")

    kill_all()
