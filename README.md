# LLM Output Evaluator

**Turn saved model responses into a repeatable regression gate.**

[![CI](https://github.com/siva-fy/llm-output-evaluator/actions/workflows/ci.yml/badge.svg)](https://github.com/siva-fy/llm-output-evaluator/actions/workflows/ci.yml)

An offline evaluation harness for structured answers: JSON shape, allowed and
required citations, required terms, abstention, forbidden content, missing test
cases, latency and estimated token cost. Compare named prompt/model variants
without tying evaluation to an inference provider.

## Quick start

Python 3.11+, no third-party packages or API keys.

~~~bash
git clone https://github.com/siva-fy/llm-output-evaluator.git
cd llm-output-evaluator
python3 demo.py
python3 -m unittest discover -s tests -v
~~~

**The included outputs and timings are synthetic. No model was called.**
The deliberately broken baseline fails three cases; the revised fixture passes
all three. Those numbers verify the checks and are not model benchmark results.

## Run a regression gate

~~~bash
python3 evaluator.py examples/cases.json examples/runs.jsonl \
  --input-rate 1.00 --output-rate 2.00 --min-pass-rate 1.0
~~~

This example deliberately returns **exit code 1**, because one variant fails.
The rates are illustrative USD per million tokens, not current provider prices.
Without rate arguments, estimated cost is zero. The demo command evaluates the
same fixtures and exits successfully after asserting the expected failures.

~~~mermaid
flowchart LR
  A[Test cases] --> C[Deterministic evaluator]
  B[Recorded outputs and usage] --> C
  C --> D[Per-case findings]
  C --> E[Per-variant pass rate]
  C --> F[Reported latency and cost estimate]
  E --> G[CI threshold]
~~~

## Input contract

Cases are a JSON array with unique IDs. Each declares `answerable`,
`allowed_citations`, optional `required_citations`, `required_terms` and
`forbidden_terms`. Runs are JSONL records:

~~~json
{
  "variant": "prompt-v2",
  "case_id": "replay",
  "output": "{\"answer\":\"Use idempotency in a transaction.\",\"citations\":[\"replay#1\"],\"abstained\":false}",
  "input_tokens": 120,
  "output_tokens": 40,
  "latency_ms": 230
}
~~~

The answer object must contain exactly `answer` (string), `citations` (string
array), and `abstained` (boolean). An unanswerable case must produce an empty
answer and no citations. Missing cases lower the pass rate and always fail the
CLI gate. Duplicate variant/case pairs and unknown case IDs are rejected.

P95 uses the nearest-rank definition over observed timings. Token counts and
latencies are supplied by the caller, not measured by this tool. Costs use
decimal arithmetic. Required/forbidden terms use case-insensitive word-set
containment, not semantic similarity or phrase order.

## What this does not prove

A valid citation ID does not prove that a source supports the answer. Passing
keyword checks does not prove factual correctness. The synthetic canary check
detects a known forbidden string; it is not a prompt-injection defense or a
general safety evaluation. Case definitions are trusted local configuration.

Next steps: add an inference recorder, collect representative held-out cases,
add claim-to-source entailment checks, and inspect regressions with a human
reviewer before changing a live application.

## Verification

Tests cover schema errors, unknown citations, missing cases, abstention, canary
strings, duplicate runs, invalid telemetry, exact decimal cost and p95 behavior.
CI runs tests and the demo on Python 3.11–3.13.
[Actual demo output](examples/demo-output.txt).

Original AI-assisted portfolio project.
[Provenance](PROVENANCE.md) · [MIT license](LICENSE)
