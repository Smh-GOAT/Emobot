import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_core.actions import VALID_ACTION_NAMES, normalize_response


def load_cases(path):
    text = Path(path).read_text()
    if str(path).endswith(".jsonl"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(text)


def evaluate_response(raw_response, max_actions):
    normalized, warnings = normalize_response(raw_response)
    actions = normalized["actions"]
    return {
        "ok": len(actions) <= max_actions and all(action in VALID_ACTION_NAMES for action in actions),
        "normalized": normalized,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate saved LLM JSON responses against Phase 0 action rules.")
    parser.add_argument(
        "--cases",
        default=Path(__file__).with_name("golden_cases.jsonl"),
        help="Path to golden_cases.jsonl",
    )
    parser.add_argument(
        "--responses",
        help="Optional JSONL file with {input, response}. If omitted, only validates case metadata.",
    )
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if len(cases) < 20:
        raise SystemExit("Expected at least 20 golden cases.")

    failures = []
    if args.responses:
        by_input = {case["input"]: case for case in cases}
        for line in Path(args.responses).read_text().splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            case = by_input.get(item["input"])
            if not case:
                failures.append((item["input"], "response_without_case"))
                continue
            result = evaluate_response(item["response"], case.get("max_actions", 8))
            if not result["ok"]:
                failures.append((item["input"], result))

    if failures:
        print(json.dumps(failures, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print(f"Phase 0 prompt eval metadata OK: {len(cases)} cases")


if __name__ == "__main__":
    main()
