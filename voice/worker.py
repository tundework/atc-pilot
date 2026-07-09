"""voice/worker.py — loads the models once, then tails watch.py's queue file.

Never lists /mnt/c directory contents itself (see watch.py's docstring for
why) — only reads appended lines from a local queue file, which is
unaffected by the caching issue since it never goes stale here.
"""
import glob
import os
import time

from pipeline import process_audio, transcribe, parse_instruction

QUEUE_FILE = "/tmp/atc_pipeline_queue.txt"

if __name__ == "__main__":
    open(QUEUE_FILE, "a").close()

    # Warm up from local disk only — never /mnt/c (see watch.py docstring)
    here = os.path.dirname(os.path.abspath(__file__))
    warmup_candidates = (glob.glob(os.path.join(here, "incoming", "*.wav"))
                         or glob.glob(os.path.join(here, "*.wav")))
    if warmup_candidates:
        transcribe(max(warmup_candidates, key=os.path.getsize))
    parse_instruction("warmup")

    print("Worker ready, waiting for recordings from watch.py ... (Ctrl+C to stop)")
    with open(QUEUE_FILE, "r") as q:
        try:
            while True:
                line = q.readline()
                if not line:
                    time.sleep(0.3)
                    continue
                try:
                    process_audio(line.strip())
                except Exception as e:
                    # One bad file must not kill the worker
                    print(f"ERROR processing {line.strip()}: {e}")
        except KeyboardInterrupt:
            print("\nStopped.")
