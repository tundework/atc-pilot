# atc-pilot

An AI-piloted RC plane that responds to spoken ATC instructions.

## Status
- [x] Week 1: SITL flying, pymavlink connected
- [x] Week 2: flight_api wrapper + pytest
- [x] Week 3: hybrid ATC parser (LLM intent + rule-based extraction), real-data validation
- [x] Week 4: DistilBERT parser, LLM-vs-BERT benchmark, BERT declared primary — see [docs/benchmark.md](docs/benchmark.md)
- [x] Week 5: Voice pipeline (Whisper ASR + Piper TTS), live end to end
- [x] Week 6: Safety supervisor — phase-aware gates, verified flight commands, full voice-to-flight wiring — see [docs/week6_milestone.md](docs/week6_milestone.md)
- [x] Week 7: Integration — main.py entry point, reliability harness, 5/5 clean run
- [x] Week 8: Scenario library — 5 scenarios incl. go-around failure demo — see [scenarios/README.md](scenarios/README.md)
- [x] Week 9: Adversarial suite — 28 tests, 100% pass, one real safety bug found and fixed (BERT truncation misclassification) — see [docs/security_notes.md](docs/security_notes.md)
- [ ] Week 10: Buffer / stretch
- [ ] Weeks 11-12: Video + blog

## Stack
ArduPilot SITL, pymavlink, DistilBERT, Whisper, Piper TTS