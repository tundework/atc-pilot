"""A scenario: a scripted ATC exchange with expected supervisor outcomes.
Reuses the exact same pipeline as live/reliability runs — TTS-synthesized
ATC audio fed through real ASR -> parser -> supervisor -> flight."""

from dataclasses import dataclass, field


@dataclass
class ScenarioStep:
    atc_line: str                    # what "ATC" says (synthesized via Piper)
    expected_verdict: str            # "ACCEPT" or "REJECT"
    expected_intent: str = None      # optional: assert the parsed intent
    wait_after_s: float = 20         # how long to let the aircraft respond
    note: str = ""                   # for humans reading the report


@dataclass
class Scenario:
    name: str
    description: str
    steps: list = field(default_factory=list)
    starting_phase: str = "ground"
