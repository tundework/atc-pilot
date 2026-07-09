import wave
from piper import PiperVoice

voice = PiperVoice.load("en_US-lessac-medium.onnx")
with wave.open("readback_test.wav", "wb") as f:
    voice.synthesize_wav(
        "Left heading two seven zero, Cessna one seven two alpha bravo.", f)
print("Wrote readback_test.wav")