from faster_whisper import WhisperModel

_model = None


def get_model():
    """Lazy-load once; GPU with CPU fallback."""
    global _model
    if _model is None:
        try:
            _model = WhisperModel("small", device="cuda", compute_type="float16")
        except Exception:
            _model = WhisperModel("small", device="cpu", compute_type="int8")
    return _model


def transcribe(wav_path: str) -> str:
    segments, _ = get_model().transcribe(
        wav_path,
        vad_filter=True,
        beam_size=5,
        language="en",
        condition_on_previous_text=False,
        initial_prompt=("ATC radio. Cessna one seven two alpha bravo, "
                        "niner, runway, heading, flight level, tower."),
    )
    parts = []
    for s in segments:
        if s.no_speech_prob < 0.6:      # drop segments Whisper itself doubts
            parts.append(s.text.strip())
    return " ".join(parts)


if __name__ == "__main__":
    import sys
    print(transcribe(sys.argv[1]))