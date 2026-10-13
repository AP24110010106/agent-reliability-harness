
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "reports" / "run_history.csv"
REPORTS = ROOT / "reports"
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_PROVIDER = "Groq"
DEFAULT_INPUT_RATE = 0.15
DEFAULT_OUTPUT_RATE = 0.60
PRICING_SOURCE_URL = "https://console.groq.com/docs/models"


def to_int(value):
    try:
        return max(0, int(float(value or 0)))
    except (ValueError, TypeError):
        return 0


def is_true(value):
    return str(value).strip().lower() in {
        "true", "1", "yes"
    }


def read_attempts():
    if not HISTORY.exists():
        raise FileNotFoundError(
            f"Benchmark history not found: {HISTORY}"
        )

    with HISTORY.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        return [
            row for row in csv.DictReader(file)
            if row.get("mode") == "research"
        ]


def analyze(input_rate=None, output_rate=None):
    if input_rate is None and output_rate is None:
        input_rate = DEFAULT_INPUT_RATE
        output_rate = DEFAULT_OUTPUT_RATE
        pricing_source = (
            "Default verified Groq pricing for "
            f"{DEFAULT_MODEL}: ${input_rate:.2f}/1M "
            f"input tokens and ${output_rate:.2f}/1M "
            "output tokens."
        )
    else:
        pricing_source = (
            "User-supplied pricing override."
        )

    attempts = read_attempts()

    prices_available = (
        input_rate is not None
        and output_rate is not None
    )

    input_total = 0
    output_total = 0
    success_count = 0
    details = []

    for row in attempts:
        input_tokens = to_int(
            row.get("input_tokens")
        )
        output_tokens = to_int(
            row.get("output_tokens")
        )
        total_tokens = (
            input_tokens + output_tokens
        )

        passed = is_true(row.get("passed"))
        success_count += int(passed)

        input_total += input_tokens
        output_total += output_tokens

        estimated_cost = None

        if prices_available:
            estimated_cost = (
                input_tokens * input_rate
                + output_tokens * output_rate
            ) / 1_000_000

        details.append({
            "case_id": row.get("case_id", ""),
            "timestamp_utc":
                row.get("timestamp_utc", ""),
            "passed": passed,
            "failure": row.get("failure", ""),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost,
        })

    total_tokens = input_total + output_total
    count = len(attempts)

    total_cost = None
    cost_per_success = None

    if prices_available:
        total_cost = sum(
            item["estimated_cost_usd"]
            for item in details
        )

        if success_count:
            cost_per_success = (
                total_cost / success_count
            )

    summary = {
        "generated_at_utc":
            datetime.now(timezone.utc).isoformat(),
        "recorded_live_attempts": count,
        "successful_attempts": success_count,
        "observed_success_rate": (
            success_count / count if count else None
        ),
        "total_input_tokens": input_total,
        "total_output_tokens": output_total,
        "total_tokens": total_tokens,
        "average_tokens_per_attempt": (
            total_tokens / count if count else None
        ),
        "input_usd_per_million_tokens": input_rate,
        "output_usd_per_million_tokens": output_rate,
        "pricing_provider": DEFAULT_PROVIDER,
        "pricing_model": DEFAULT_MODEL,
        "pricing_source_url": PRICING_SOURCE_URL,
        "estimated_total_cost_usd": total_cost,
        "estimated_cost_per_success_usd":
            cost_per_success,
        "cost_method": (
            pricing_source
            + " Estimates use saved input/output token "
            "counts only and do not include free-tier "
            "credits, taxes, retries outside the harness, "
            "or non-token platform charges."
        ),
    }

    REPORTS.mkdir(parents=True, exist_ok=True)

    detail_path = REPORTS / "cost_breakdown.csv"

    with detail_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "case_id",
                "timestamp_utc",
                "passed",
                "failure",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "estimated_cost_usd",
            ],
        )
        writer.writeheader()
        writer.writerows(details)

    summary_path = REPORTS / "cost_summary.json"

    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nTOKEN COST ANALYSIS")
    print("--------------------------")
    print("Attempts:", count)
    print("Successes:", success_count)
    print("Input tokens:", input_total)
    print("Output tokens:", output_total)
    print("Total tokens:", total_tokens)
    print(
        "Average tokens:",
        round(
            summary["average_tokens_per_attempt"]
            or 0, 2
        ),
    )

    if prices_available:
        print(
            "Estimated total USD:",
            f"${total_cost:.6f}"
        )
        print(
            "Estimated USD per success:",
            (
                f"${cost_per_success:.6f}"
                if cost_per_success is not None
                else "N/A"
            ),
        )
    else:
        print(
            "USD cost: N/A "
            "(provider rates not configured)"
        )

    print("\nSaved:")
    print(detail_path)
    print(summary_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze saved benchmark token usage."
    )

    parser.add_argument(
        "--input-rate",
        type=float,
        default=None,
        help="USD per million input tokens",
    )
    parser.add_argument(
        "--output-rate",
        type=float,
        default=None,
        help="USD per million output tokens",
    )

    args = parser.parse_args()

    if (args.input_rate is None) != (
        args.output_rate is None
    ):
        parser.error(
            "Supply both rates or neither."
        )

    for rate in (
        args.input_rate,
        args.output_rate,
    ):
        if rate is not None and rate < 0:
            parser.error(
                "Rates cannot be negative."
            )

    analyze(
        input_rate=args.input_rate,
        output_rate=args.output_rate,
    )
