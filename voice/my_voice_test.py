"""Day 5 gate: my-voice table — transcript vs. parsed intent, 5 rows.

Run after recording samples on the Windows side (either win_capture.ps1's
/mnt/c/atc_voice_samples/sample_*.wav, or Windows Voice Recorder's
OneDrive\\Documents\\Sound Recordings\\*.m4a — faster-whisper decodes both).
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "atc_nlp"))
os.chdir(os.path.join(HERE, "..", "atc_nlp"))

import asr  # noqa: E402
import bert_parser  # noqa: E402

SAMPLE_DIRS = [
    "/mnt/c/atc_voice_samples",
    "/mnt/c/Users/babat/OneDrive/Documents/Sound Recordings",
]

wavs = []
for d in SAMPLE_DIRS:
    wavs += glob.glob(os.path.join(d, "sample_*.wav"))
    wavs += glob.glob(os.path.join(d, "*.m4a"))
wavs = sorted(wavs)
if not wavs:
    print(f"No samples found in {SAMPLE_DIRS}.")
    sys.exit(1)

rows = []
for w in wavs:
    text = asr.transcribe(w)
    parsed = bert_parser.parse_instruction(text)
    rows.append((os.path.basename(w), text, parsed["intent"], parsed))

print(f"{'file':<14} {'intent':<20} transcript")
print("-" * 90)
for fname, text, intent, parsed in rows:
    print(f"{fname:<14} {intent:<20} {text}")

print()
for fname, text, intent, parsed in rows:
    print(f"{fname}: {parsed}")
