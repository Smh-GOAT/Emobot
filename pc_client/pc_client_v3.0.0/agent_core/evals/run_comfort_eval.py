import argparse
import json
import sys
from pathlib import Path


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_case_metadata(cases):
    failures = []
    seen_ids = set()
    for case in cases:
        case_id = case.get("id")
        if not case_id or case_id in seen_ids:
            failures.append((case_id, "missing_or_duplicate_id"))
        seen_ids.add(case_id)
        for key in ("input", "scenario", "must_include_any", "must_not_include", "safety_level"):
            if key not in case:
                failures.append((case_id, f"missing_{key}"))
        if not case.get("must_include_any"):
            failures.append((case_id, "empty_must_include_any"))
    return failures


def validate_responses(cases, responses_path):
    by_id = {case["id"]: case for case in cases}
    failures = []
    for item in load_jsonl(responses_path):
        case = by_id.get(item.get("id"))
        answer = item.get("answer", "")
        if not case:
            failures.append((item.get("id"), "response_without_case"))
            continue
        if not any(token in answer for token in case["must_include_any"]):
            failures.append((case["id"], "missing_required_tone_or_content"))
        blocked = [token for token in case["must_not_include"] if token in answer]
        if blocked:
            failures.append((case["id"], f"blocked_tokens:{blocked}"))
    return failures


def main():
    parser = argparse.ArgumentParser(description="Validate emotional-support golden cases and optional responses.")
    parser.add_argument(
        "--cases",
        default=Path(__file__).with_name("comfort_golden_cases.jsonl"),
        help="Path to comfort_golden_cases.jsonl",
    )
    parser.add_argument("--responses", help="Optional JSONL file with {id, answer}.")
    args = parser.parse_args()

    cases = load_jsonl(args.cases)
    failures = validate_case_metadata(cases)
    if len(cases) < 20:
        failures.append(("case_count", "expected_at_least_20_cases"))
    if args.responses:
        failures.extend(validate_responses(cases, args.responses))

    if failures:
        print(json.dumps(failures, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    print(f"Comfort eval metadata OK: {len(cases)} cases")


if __name__ == "__main__":
    sys.exit(main())
