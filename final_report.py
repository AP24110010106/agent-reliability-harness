
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"


def load_json(filename):
    path = REPORTS / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Missing report: {path}. Generate it first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    benchmark = load_json("summary.json")
    reference = load_json("reference_summary.json")
    cost = load_json("cost_summary.json")

    from reliability_harness import read_history

    attempts = [
        run for run in read_history()
        if run.mode == "research"
    ]

    successes = sum(bool(run.passed) for run in attempts)
    failures = Counter(
        run.failure for run in attempts
        if not run.passed
    )

    # Normalize historical 429 classifications for analysis.
    for run in attempts:
        if (
            not run.passed
            and run.failure != "rate_limit"
            and (
                "429" in (run.error or "")
                or "rate_limit" in (run.error or "").lower()
            )
        ):
            failures[run.failure] -= 1
            failures["rate_limit"] += 1

    failures = {
        name: count
        for name, count in failures.items()
        if count > 0
    }

    unique_cases = len({
        run.case_id for run in attempts
    })

    total = len(attempts)
    rate_limited = failures.get("rate_limit", 0)
    non_quota = total - rate_limited

    success_rate = (
        100 * successes / total if total else 0
    )
    quota_excluded = (
        100 * successes / non_quota
        if non_quota else 0
    )

    avg_steps = (
        sum(run.steps for run in attempts) / total
        if total else 0
    )

    failure_rows = "\n".join(
        f"| {name} | {count} |"
        for name, count in sorted(
            failures.items(),
            key=lambda item: (-item[1], item[0])
        )
    )

    usd_total = cost.get(
        "estimated_total_cost_usd"
    )
    usd_per_success = cost.get(
        "estimated_cost_per_success_usd"
    )

    def money(value):
        return (
            "Not available — pricing not configured"
            if value is None
            else f"${value:.6f}"
        )

    report = f"""# Agent Reliability Harness
## Final Evaluation Report

Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

### 1. Objective

Evaluate the reliability of an existing tool-using research agent
using a reproducible test harness.

The harness records execution outcomes, termination reasons,
token usage, citations, concept coverage, and failure categories.

The evaluated research agent is a separate project.
Its source code was not modified for this evaluation.

### 2. Benchmark Dataset

- Defined research cases: 20
- Unique research cases executed: {unique_cases}
- Recorded live attempts: {total}
- Draft reference answers: {reference.get('defined_reference_cases', 'N/A')}
- Saved finished answers available for reference checks: {reference.get('answers_available', 'N/A')}

The 24 recorded attempts do not represent repeated execution
of every individual case.

### 3. Reliability Metrics

| Metric | Result |
|---|---:|
| Total attempts | {total} |
| Successful attempts | {successes} |
| Observed success rate | {success_rate:.1f}% |
| Rate-limited attempts | {rate_limited} |
| Success rate excluding rate limits | {quota_excluded:.1f}% |
| Average agent steps | {avg_steps:.2f} |
| Total input tokens | {cost.get('total_input_tokens', 'N/A'):,} |
| Total output tokens | {cost.get('total_output_tokens', 'N/A'):,} |
| Total tokens | {cost.get('total_tokens', 'N/A'):,} |
| Average tokens per attempt | {cost.get('average_tokens_per_attempt', 0):,.2f} |
| Estimated total model cost | {money(usd_total)} |
| Estimated cost per success | {money(usd_per_success)} |

Success rate is the number of originally recorded passing
attempts divided by all recorded live research attempts.

The quota-excluded rate removes rate-limited attempts from
the denominator. It is a secondary diagnostic metric,
not a replacement for the overall success rate.

USD costs require verified input and output token rates.
Token counts are measured; actual provider billing is not
established by this report.

### 4. Failure Analysis

| Failure category | Attempts |
|---|---:|
{failure_rows}

The largest observed failure category is token-budget exhaustion.
Rate limiting is the second major reliability constraint.

An earlier Q06 attempt was marked as missing expected content.
Later regrading found its concept coverage acceptable, but
its citation metadata was insufficient for full retrospective
verification. The original historical result is preserved.

### 5. Reference Evaluation

- Finished answers assessed: {reference.get('answers_available', 'N/A')}
- Concept checks passed: {reference.get('concept_passes', 'N/A')}
- Citation verification outcomes: {json.dumps(reference.get('citation_statuses', {}))}

Concept matching is a deterministic proxy for coverage.
It does not prove factual correctness or semantic equivalence.

Citation validation checks citation structure and declared
source identifiers. It does not independently establish
whether a source supports every factual claim.

### 6. Fault-Injection Testing

The offline test suite includes agent-boundary tests for:

- HTTP 429 rate-limit exceptions
- Network timeout exceptions
- Malformed agent responses
- Token-budget exhaustion
- Iteration-limit exhaustion
- Missing citations
- Undeclared citations
- Missing expected content
- Successful agent responses

These tests use mocks at the research-agent boundary.
They validate the harness's handling of these conditions,
not the internal recovery behavior of the research agent.

Q21-Q25 in the existing harness are placeholder simulated
cases and are not treated as genuine fault-injection
benchmark executions.

### 7. Fix-First Recommendations

**Priority 1 — Token-budget exhaustion**

Reduce unnecessary tool calls, repeated context, and
oversized tool outputs. Introduce intermediate budget
checks and earlier answer synthesis in a future agent version.

**Priority 2 — Rate-limit resilience**

Introduce provider-aware scheduling, bounded backoff,
and resumable benchmark execution.

**Priority 3 — Iteration efficiency**

Improve termination decisions and reduce redundant
search/fetch cycles.

These are recommendations. They have not been implemented
in the original research agent.

### 8. Reproducibility

Run offline tests:

    python -m unittest discover -v

Rebuild saved-history summaries:

    python reliability_harness.py --summary-only
    python reference_evaluator.py
    python cost_analyzer.py

Run a single live case:

    python reliability_harness.py --mode live --case Q01

Live execution requires the separately installed research
agent and valid provider credentials.

### 9. Limitations

1. Every research case has been executed at least once,
   but not every case has multiple repetitions.
2. Reference answers are drafts, not independently
   adjudicated gold-standard answers.
3. Keyword grading can produce false positives and
   false negatives.
4. Citation metadata is unavailable for one finished
   historical answer.
5. API quotas affected the observed success rate.
6. USD costs remain unavailable until verified pricing
   is supplied.
7. Mocked boundary faults do not establish full
   end-to-end fault recovery.

### 10. Conclusion

The harness successfully records, classifies, and reports
research-agent execution outcomes across all 20 defined
research cases.

The benchmark identifies token-budget exhaustion as the
most frequent observed failure and provides a reproducible
basis for future agent improvements.

The historical measurements are retained without
fabricating successes or overwriting baseline results.
"""

    destination = REPORTS / "final_evaluation.md"
    destination.write_text(
        report,
        encoding="utf-8"
    )

    print("FINAL REPORT GENERATED")
    print("Location:", destination)
    print("Research coverage:", f"{unique_cases}/20")
    print("Live attempts:", total)
    print("Success rate:", f"{success_rate:.1f}%")
    print("Failure categories:", failures)


if __name__ == "__main__":
    main()
