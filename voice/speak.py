import wave
import subprocess
import shutil
from piper import PiperVoice

_voice = PiperVoice.load("en_US-lessac-medium.onnx")


def _play(outfile: str):
    # Try Linux-side audio first
    if shutil.which("aplay"):
        r = subprocess.run(["aplay", "-q", outfile], check=False,
                           capture_output=True)
        if r.returncode == 0:
            return
    # Fallback: play via Windows (always works from WSL)
    subprocess.run([
        "powershell.exe", "-c",
        f"(New-Object Media.SoundPlayer '\\\\wsl.localhost\\Ubuntu-22.04\\home\\babat\\atc-pilot\\voice\\{outfile}').PlaySync()"
    ], check=False)


def speak(text: str, outfile: str = "readback.wav", play: bool = True):
    with wave.open(outfile, "wb") as f:
        _voice.synthesize_wav(text, f)
    if play:
        _play(outfile)
    return outfile