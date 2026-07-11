"""Run a single Scenario end-to-end: synth each ATC line, feed through the
real pipeline, verify supervisor verdicts, log everything for review."""
import sys, os, json, time

VOICE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "voice")
sys.path.insert(0, VOICE_DIR)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "supervisor"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "flight_api"))
os.chdir(VOICE_DIR)   # speak.py loads its Piper model via a relative path,
                      # and pipeline.py's own atc_nlp import is also CWD-relative

from speak import speak            # Piper synth, reused as "ATC" voice
from pipeline import process_audio


def run_scenario(scenario, fc, supervisor, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    results = []
    supervisor.phase = scenario.starting_phase

    print(f"\n=== SCENARIO: {scenario.name} ===")
    print(scenario.description)

    for i, step in enumerate(scenario.steps):
        wav = os.path.join(out_dir, f"step_{i}_atc.wav")
        speak(step.atc_line, outfile=wav, play=False)   # ATC "says" it

        trace = process_audio(wav, verbose=False)
        decision = supervisor.handle(trace)

        ok_verdict = decision["verdict"] == step.expected_verdict
        ok_intent = (step.expected_intent is None or
                    trace["instruction"]["intent"] == step.expected_intent)
        passed = ok_verdict and ok_intent

        result = {
            "step": i, "atc_line": step.atc_line,
            "expected": step.expected_verdict, "got": decision["verdict"],
            "intent": trace["instruction"]["intent"], "passed": passed,
        }
        results.append(result)
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] '{step.atc_line}' -> {decision['verdict']}"
              f" (expected {step.expected_verdict})")

        time.sleep(step.wait_after_s)

    all_passed = all(r["passed"] for r in results)
    with open(os.path.join(out_dir, "results.json"), "w") as f:
        json.dump({"scenario": scenario.name, "passed": all_passed,
                   "steps": results}, f, indent=2)
    print(f"=== {scenario.name}: {'PASS' if all_passed else 'FAIL'} ===\n")
    return all_passed
