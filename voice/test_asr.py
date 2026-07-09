import glob
from asr import transcribe

wavs = sorted(glob.glob(
    "../atc_nlp/atco2/ATCO2-ASRdataset-v1_beta/DATA/*.wav"))[:5]

for w in wavs:
    print(f"\n=== {w.split('/')[-1]} ===")
    print(f"  {transcribe(w)}")
