import json
from pathlib import Path
from evaluator import evaluate

root = Path(__file__).parent / "examples"
cases = json.loads((root / "cases.json").read_text())
runs = [json.loads(line) for line in (root / "runs.jsonl").read_text().splitlines()]
result = evaluate(cases, runs, input_rate="1.00", output_rate="2.00")
assert result["synthetic-baseline"]["pass_rate"] == 0
assert result["synthetic-revised"]["pass_rate"] == 1
print("Synthetic outputs and illustrative rates; no model was called.")
print(json.dumps(result, indent=2))
