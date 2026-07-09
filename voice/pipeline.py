import os
import sys
import time

sys.path.insert(0, "../atc_nlp")   # so we can import the parser

from asr import transcribe
from bert_parser import parse_instruction
from callsign import matches
from readback import generate_readback
from speak import speak, _play

MY_CALLSIGN = "N172AB"

def process_audio(wav_path: str, verbose: bool = True) -> dict:
    """One ATC transmission: audio in -> spoken readback out.
    Returns a full trace dict (this becomes supervisor input in Week 6)."""
    trace = {"file": wav_path}

    t0 = time.perf_counter()
    text = transcribe(wav_path)
    t1 = time.perf_counter()
    trace["transcript"] = text
    trace["t_asr_ms"] = (t1 - t0) * 1000

    instruction = parse_instruction(text)
    t2 = time.perf_counter()
    trace["instruction"] = instruction
    trace["t_parse_ms"] = (t2 - t1) * 1000

    trace["for_me"] = matches(instruction["callsign"], MY_CALLSIGN)

    if trace["for_me"]:
        rb = generate_readback(instruction)
    else:
        rb = None          # not our instruction — stay silent
    trace["readback"] = rb
    t3 = time.perf_counter()

    outfile = None
    if rb:
        outfile = speak(rb, play=False)     # synth only
    t4 = time.perf_counter()
    trace["t_synth_ms"] = (t4 - t3) * 1000
    trace["t_response_ms"] = (t4 - t0) * 1000   # the real latency number

    if outfile:
        _play(outfile)
    t5 = time.perf_counter()
    trace["t_tts_play_ms"] = (t5 - t4) * 1000
    trace["t_total_ms"] = (t5 - t0) * 1000

    if verbose:
        print(f"\n=== {wav_path.split('/')[-1]} ===")
        print(f"  HEARD:    {text}")
        print(f"  PARSED:   {instruction['intent']}"
              f"  cs={instruction['callsign']}"
              f"  hdg={instruction['heading_deg']}"
              f"  alt={instruction['altitude_ft']}"
              f"  rwy={instruction['runway']}")
        print(f"  FOR ME:   {trace['for_me']}")
        print(f"  READBACK: {rb if rb else '(silent — not our callsign)'}")
        print(f"  TIMING:   asr={trace['t_asr_ms']:.0f}ms"
              f"  parse={trace['t_parse_ms']:.0f}ms"
              f"  response={trace['t_response_ms']:.0f}ms"
              f"  (+playback={trace['t_tts_play_ms']:.0f}ms"
              f" total={trace['t_total_ms']:.0f}ms)")
    return trace

if __name__ == "__main__":
    import glob
    # Point at wherever your Day 2 recordings live:
    samples = sorted(glob.glob("/mnt/c/atc_voice_samples/*.wav")) \
        or sorted(glob.glob("samples/*.wav")) \
        or sorted(glob.glob(
            "/mnt/c/Users/babat/OneDrive/Documents/Sound Recordings/*.m4a"))
    if not samples:
        print("No samples found — adjust the glob paths at the bottom of pipeline.py")
        sys.exit(1)

    transcribe(max(samples, key=os.path.getsize))  # wake the ASR GPU on real audio
    parse_instruction("warmup")                     # wake the BERT model too

    for s in samples:
        process_audio(s)
