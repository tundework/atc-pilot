"""
atc-pilot: single entry point.

Starts, in order: the watcher, the worker (with live supervisor). Run this
instead of juggling two terminals by convention. SITL is a separate manual
step — headless SITL startup is finicky enough that automating it is its
own trap, deliberately out of scope here (see docs/RUNBOOK.md).

Usage: python main.py
"""
import subprocess
import sys
import time
import signal
import os

PROCS = []


def start(name, cmd, cwd=None):
    print(f"Starting {name}...")
    p = subprocess.Popen(cmd, cwd=cwd)
    PROCS.append((name, p))
    return p


def shutdown(*_):
    print("\nShutting down...")
    for name, p in reversed(PROCS):
        print(f"  stopping {name}")
        p.terminate()
    for name, p in reversed(PROCS):
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown)

if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    voice_dir = os.path.join(root, "voice")

    print("=== atc-pilot startup ===")
    print("1. Make sure SITL is already running (see docs/RUNBOOK.md).")
    input("   Press Enter once SITL shows a GPS 3D fix... ")

    start("watcher", [sys.executable, "watch.py"], cwd=voice_dir)
    time.sleep(1)
    start("worker", [sys.executable, "worker.py"], cwd=voice_dir)

    print("\nSystem up. Speak instructions via win_capture.ps1 on Windows.")
    print("Ctrl+C here to stop everything.\n")

    for _, p in PROCS:
        p.wait()
