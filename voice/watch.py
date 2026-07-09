"""voice/watch.py — lightweight directory watcher, no ML imports.

Deliberately kept free of torch/transformers imports. Testing showed that
once a process in this WSL2 setup loads the BERT model (bert_parser.py's
transformers.AutoModelForSequenceClassification.from_pretrained), that
process's view of /mnt/c gets unreliable — not just directory listings
(glob()/os.listdir() stop seeing new files) but even direct reads of a
brand-new file's content can come back stale/truncated to PyAV, despite
the file being demonstrably complete and valid moments later from a fresh
process. Root cause not fully isolated (looks like a WSL2 DrvFs/9p caching
interaction) — not worth chasing further at the syscall level. The fix is
architectural: this process (never loads the heavy models, so never gets
poisoned) does ALL the /mnt/c interaction — waits for a recording to
finish, then copies it onto local WSL disk with verification — and
worker.py only ever touches that local copy, never /mnt/c directly.
"""
import glob
import os
import shutil
import time
import wave

WATCH = "/mnt/c/atc_voice_samples/"
STAGING = os.path.join(os.path.dirname(os.path.abspath(__file__)), "incoming")
QUEUE_FILE = "/tmp/atc_pipeline_queue.txt"

STABLE_FOR = 1.0    # seconds a file's size must be unchanged before we try it
GIVE_UP_AFTER = 60  # seconds since first sighting before a file is abandoned


def try_copy(src: str, dst: str) -> bool:
    """One attempt: copy src to dst, verify it's a complete parseable wav.

    Two distinct failure modes feed into this, both observed live:
    - ffmpeg creates the file at 0 bytes and flushes in bursts, so a
      mid-recording file can pass the size-stability check (a 0-byte or
      partial file whose size holds steady between flushes).
    - 9p reads can return empty/truncated content for a file whose
      directory entry already shows the full size (a 255KB recording
      copied as 0 bytes).
    A failed attempt is NOT final — the caller re-arms the file and tries
    again on a later poll, because "not valid yet" usually means "ffmpeg is
    still writing."
    """
    try:
        src_size = os.path.getsize(src)
        if src_size == 0:
            return False
        shutil.copy2(src, dst)
        if os.path.getsize(dst) != src_size:
            return False
        with wave.open(dst, "rb") as w:
            return w.getnframes() > 0
    except Exception:
        return False


if __name__ == "__main__":
    os.makedirs(STAGING, exist_ok=True)
    # Track by path only. win_capture.ps1 writes a fresh timestamped
    # filename per recording, so a reused name can't happen in practice —
    # and tracking by (path, mtime) turned out to be actively harmful: mtime
    # as reported over this WSL2 9p mount jitters slightly between polls
    # even when the file is untouched, so the same file could look "new
    # again" on a later poll and get processed twice.
    seen = set(glob.glob(WATCH + "*.wav"))
    open(QUEUE_FILE, "a").close()
    print(f"Ignoring {len(seen)} existing recording(s).")
    print(f"Watching {WATCH} ... (Ctrl+C to stop)")

    candidates = {}   # path -> (last_seen_size, time_of_last_size_change)
    first_seen = {}   # path -> time we first noticed it
    try:
        while True:
            for f in sorted(glob.glob(WATCH + "*.wav")):
                if f in seen:
                    continue
                try:
                    size = os.path.getsize(f)
                except OSError:
                    continue
                now = time.time()
                first_seen.setdefault(f, now)
                prev = candidates.get(f)
                if prev is None or prev[0] != size:
                    # new or still growing — (re)start the stability clock
                    candidates[f] = (size, now)
                elif now - prev[1] > STABLE_FOR:
                    local_copy = os.path.join(STAGING, os.path.basename(f))
                    if try_copy(f, local_copy):
                        seen.add(f)
                        candidates.pop(f, None)
                        first_seen.pop(f, None)
                        print(f"New recording: {f} -> {local_copy}")
                        with open(QUEUE_FILE, "a") as q:
                            q.write(local_copy + "\n")
                    elif now - first_seen[f] > GIVE_UP_AFTER:
                        seen.add(f)
                        candidates.pop(f, None)
                        first_seen.pop(f, None)
                        print(f"WARNING: {f} never became a valid recording "
                              f"within {GIVE_UP_AFTER}s — skipped.")
                    else:
                        # probably still being written — re-arm and retry
                        candidates[f] = (size, now)
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nStopped.")
