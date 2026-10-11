"""Offline regression checks for structured answers and reported inference usage."""
import argparse
import json
import math
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


def words(value):
    return set(re.findall(r"\w+", value.lower()))


def check_answer(raw, case):
    try:
        answer = json.loads(raw)
    except (ValueError, TypeError):
        return ["invalid_json"]
    if (not isinstance(answer, dict) or set(answer) != {"answer", "citations", "abstained"}
            or not isinstance(answer["answer"], str)
            or type(answer["abstained"]) is not bool
            or not isinstance(answer["citations"], list)
            or any(not isinstance(c, str) for c in answer["citations"])):
        return ["schema"]
    errors = []
    citations = set(answer["citations"])
    if citations - set(case["allowed_citations"]):
        errors.append("unknown_citation")
    if len(citations) != len(answer["citations"]):
        errors.append("duplicate_citation")
    if case["answerable"]:
        if answer["abstained"]:
            errors.append("unexpected_abstention")
        if not set(case.get("required_citations", [])) <= citations:
            errors.append("missing_citation")
        if any(not words(term) <= words(answer["answer"]) for term in case.get("required_terms", [])):
            errors.append("missing_terms")
        if not answer["answer"].strip():
            errors.append("empty_answer")
    else:
        if not answer["abstained"]:
            errors.append("failed_to_abstain")
        if answer["answer"].strip() or citations:
            errors.append("abstention_contains_answer")
    for term in case.get("forbidden_terms", []):
        if words(term) <= words(answer["answer"]):
            errors.append("forbidden_content")
            break
    return errors


def evaluate(cases, runs, input_rate=Decimal("0"), output_rate=Decimal("0")):
    """Rates are explicitly supplied USD per million tokens, never provider defaults."""
    rates = [Decimal(str(input_rate)), Decimal(str(output_rate))]
    if any(not r.is_finite() or r < 0 for r in rates):
        raise ValueError("rates must be finite and nonnegative")
    lookup = {c["id"]: c for c in cases}
    if not cases or len(lookup) != len(cases):
        raise ValueError("cases must be nonempty and have unique IDs")
    if not runs:
        raise ValueError("runs must not be empty")
    grouped, seen = defaultdict(list), set()
    for run in runs:
        case_id, variant = run["case_id"], run["variant"]
        if case_id not in lookup:
            raise ValueError(f"unknown case: {case_id}")
        if not isinstance(variant, str) or not variant.strip():
            raise ValueError("variant must be a nonempty string")
        key = (variant, case_id)
        if key in seen:
            raise ValueError("duplicate case/variant result")
        seen.add(key)
        for field in ("input_tokens", "output_tokens"):
            if type(run[field]) is not int or run[field] < 0:
                raise ValueError("token counts must be nonnegative integers")
        latency = run["latency_ms"]
        if type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0:
            raise ValueError("latency_ms must be finite and nonnegative")
        errors = check_answer(run["output"], lookup[case_id])
        cost = (run["input_tokens"] * rates[0] + run["output_tokens"] * rates[1]) / 1000000
        grouped[variant].append({"case_id": case_id, "passed": not errors, "errors": errors,
                                 "latency_ms": latency, "estimated_cost_usd": str(cost)})
    report = {}
    for variant, rows in sorted(grouped.items()):
        missing = sorted(lookup.keys() - {r["case_id"] for r in rows})
        latencies = sorted(r["latency_ms"] for r in rows)
        report[variant] = {
            "expected_cases": len(cases), "observed_cases": len(rows), "missing_cases": missing,
            "pass_rate": sum(r["passed"] for r in rows) / len(cases),
            "p95_latency_ms": latencies[math.ceil(0.95 * len(latencies)) - 1],
            "estimated_cost_usd": str(sum((Decimal(r["estimated_cost_usd"]) for r in rows), Decimal(0))),
            "cases": rows}
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("runs", type=Path)
    parser.add_argument("--input-rate", type=Decimal, default=Decimal("0"))
    parser.add_argument("--output-rate", type=Decimal, default=Decimal("0"))
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    args = parser.parse_args()
    if not 0 <= args.min_pass_rate <= 1:
        parser.error("--min-pass-rate must be in [0,1]")
    report = evaluate(json.loads(args.cases.read_text()),
                      [json.loads(s) for s in args.runs.read_text().splitlines() if s.strip()],
                      args.input_rate, args.output_rate)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if all(r["pass_rate"] >= args.min_pass_rate and not r["missing_cases"]
                             for r in report.values()) else 1)
