# BERT is the primary parser as of Week 4 — see docs/benchmark.md.
# Consumers (voice pipeline, supervisor, etc.) should import from here.
# llm_parser remains available directly for comparison/benchmarking.
from bert_parser import parse_instruction

__all__ = ["parse_instruction"]
