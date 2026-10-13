
import argparse
import csv
import json
import re
import statistics
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

REPORTS = Path("reports")
HISTORY = REPORTS / "run_history.csv"
REGRADES = REPORTS / "regrades.csv"

# USD per million tokens.
# Verified Groq model table for openai/gpt-oss-120b:
# https://console.groq.com/docs/models
INPUT_RATE = 0.15
OUTPUT_RATE = 0.60

GRADING_VERSION = "v4"


@dataclass
class TestCase:
    id: str
    category: str
    question: str
    expected_terms: list[str]
    mode: str = "research"
    expected_failure: str = "none"


@dataclass
class TestResult:
    timestamp_utc: str
    case_id: str
    category: str
    mode: str
    repetition: int
    passed: bool
    failure: str
    termination: str
    steps: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None
    seconds: float
    answer: str
    error: str
    source_ids_json: str = ""
    sources_json: str = ""
    grading_version: str = GRADING_VERSION


CASES = [
    TestCase("Q01", "science",
             "What causes coral bleaching?",
             ["coral", "temperature", "algae"]),
    TestCase("Q02", "science",
             "What causes ocean tides?",
             ["moon", "gravity"]),
    TestCase("Q03", "science",
             "Explain the greenhouse effect.",
             ["greenhouse", "heat"]),
    TestCase("Q04", "science",
             "What causes earthquakes?",
             ["tectonic", "fault"]),
    TestCase("Q05", "science",
             "What is antibiotic resistance?",
             ["bacteria", "antibiotic"]),
    TestCase("Q06", "science",
             "How do vaccines work?",
             ["immune", "response"]),
    TestCase("Q07", "science",
             "How do solar photovoltaic cells work?",
             ["sunlight", "electricity"]),
    TestCase("Q08", "technology",
             "What is multifactor authentication?",
             ["authentication", "factor"]),
    TestCase("Q09", "technology",
             "What does DNS do?",
             ["domain", "address"]),
    TestCase("Q10", "science",
             "What is the difference between weather and climate?",
             ["weather", "climate"]),
    TestCase("Q11", "comparison",
             "Compare solar and wind electricity generation.",
             ["solar", "wind"]),
    TestCase("Q12", "comparison",
             "Compare HTTP and HTTPS.",
             ["http", "https"]),
    TestCase("Q13", "comparison",
             "Compare supervised and unsupervised learning.",
             ["supervised", "unsupervised"]),
    TestCase("Q14", "comparison",
             "Compare RAM and SSD storage.",
             ["ram", "ssd"]),
    TestCase("Q15", "comparison",
             "Compare IPv4 and IPv6.",
             ["ipv4", "ipv6"]),
    TestCase("Q16", "ambiguous",
             "What is the best programming language?",
             ["depends"]),
    TestCase("Q17", "ambiguous",
             "Is AI always accurate?",
             ["no"]),
    TestCase("Q18", "ambiguous",
             "Which database is fastest?",
             ["depends"]),
    TestCase("Q19", "ambiguous",
             "Can renewable energy power everything?",
             ["energy"]),
    TestCase("Q20", "ambiguous",
             "Is cloud computing always cheaper?",
             ["depends"]),
    TestCase("Q21", "edge_case",
             "Agent search tool raises a timeout before evidence is available.",
             [], "simulated_failure", "timeout"),
    TestCase("Q22", "edge_case",
             "Agent receives an HTTP 500 from a source fetch.",
             [], "simulated_failure", "tool_limit"),
    TestCase("Q23", "edge_case",
             "Agent cites a source identifier that was not returned.",
             [], "simulated_failure", "undeclared_citation"),
    TestCase("Q24", "edge_case",
             "Agent returns an answer with no citations.",
             [], "simulated_failure", "missing_citations"),
    TestCase("Q25", "edge_case",
             "Agent stops after reaching the hard iteration limit.",
             [], "simulated_failure", "iteration_limit"),
]

CASE_LOOKUP = {case.id: case for case in CASES}

CONCEPT_ALTERNATIVES = {
    "response": [
        "response", "responses", "respond",
        "react", "reaction"
    ],
    "electricity": [
        "electricity", "electric", "electrical"
    ],
    "authentication": [
        "authentication", "authenticate"
    ],
    "factor": [
        "factor", "factors", "credential",
        "credentials", "verification method"
    ],
    "address": [
        "address", "addresses"
    ],
    "depends": [
        "depends", "depending", "varies",
        "dependent on", "there is no single",
        "no universal"
    ],
    "no": [
        "no", "not always", "not necessarily",
        "cannot guarantee", "can be inaccurate"
    ],
    "temperature": [
        "temperature", "temperatures",
        "warming", "heat stress"
    ],
    "tectonic": [
        "tectonic", "plate movement",
        "earth's plates"
    ],
    "fault": [
        "fault", "faults",
        "fracture", "fractures"
    ],
    "gravity": [
        "gravity", "gravitational"
    ],
}


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def json_safe(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        default=str
    )


def parse_json(value, fallback):
    if not value:
        return fallback

    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return fallback


def run_agent(question):
    # Import the verified Project 1 agent.
    # No changes are made to Project 1.
    from agent.loop import run_agent as research_agent
    return research_agent(question)


def normalize_output(raw):
    if not isinstance(raw, dict):
        raise TypeError(
            "Expected run_agent to return a dictionary."
        )

    return {
        "success": bool(raw.get("success", False)),
        "termination": str(
            raw.get("termination") or "unknown"
        ),
        "answer": str(raw.get("answer") or ""),
        "steps": int(raw.get("iterations") or 0),
        "tool_calls": int(raw.get("tool_calls") or 0),
        "input_tokens": int(
            raw.get("input_tokens") or 0
        ),
        "output_tokens": int(
            raw.get("output_tokens") or 0
        ),
        "source_ids": raw.get("source_ids") or [],
        "sources": raw.get("sources") or {},
        "error": str(raw.get("error") or ""),
    }


def is_rate_limit_error(message):
    text = str(message).lower()

    return any(marker in text for marker in [
        "rate_limit_exceeded",
        "rate limit reached",
        "rate limit exceeded",
        "too many requests",
        "tokens per day",
        "tokens per minute",
        "requests per minute",
        "status code: 429",
        "error code: 429",
        "http 429",
    ])


def classify_failure(output):
    error = output.get("error", "")
    termination = output.get(
        "termination", ""
    ).lower()

    if is_rate_limit_error(error):
        return "rate_limit"

    if "token" in termination:
        return "token_limit"

    if "iteration" in termination:
        return "iteration_limit"

    if "tool" in termination:
        return "tool_limit"

    if "timeout" in termination:
        return "timeout"

    if "model" in termination:
        return "model_error"

    if error:
        return "runtime_error"

    return "agent_failure"


def contains_phrase(text, phrase):
    pattern = (
        r"(?<!\w)"
        + re.escape(phrase.lower())
        + r"(?!\w)"
    )

    return bool(
        re.search(pattern, text.lower())
    )


def check_concepts(case, answer):
    missing = []

    for concept in case.expected_terms:
        alternatives = CONCEPT_ALTERNATIVES.get(
            concept.lower(),
            [concept]
        )

        if not any(
            contains_phrase(answer, alternative)
            for alternative in alternatives
        ):
            missing.append(concept)

    return missing


def known_source_ids(sources):
    if isinstance(sources, dict):
        return {
            str(key)
            for key in sources.keys()
        }

    if isinstance(sources, list):
        identifiers = set()

        for item in sources:
            if isinstance(item, dict):
                for field in ("id", "source_id"):
                    if item.get(field) is not None:
                        identifiers.add(
                            str(item[field])
                        )

        return identifiers

    return set()


def check_citations(answer, source_ids, sources):
    cited = set(
        re.findall(r"\[(S\d+)\]", answer)
    )

    if not cited:
        return False, "missing_citations"

    if not isinstance(source_ids, list):
        return False, "invalid_source_ids"

    declared = {
        str(item)
        for item in source_ids
    }

    if not declared:
        return False, "missing_declared_sources"

    if not cited.issubset(declared):
        return False, "undeclared_citation"

    available = known_source_ids(sources)

    if not available:
        return False, "source_validation_unavailable"

    if not cited.issubset(available):
        return False, "invalid_citation"

    return True, "none"


def grade(case, output):
    if case.mode == "simulated_failure":
        if output["success"]:
            citation_ok, citation_failure = check_citations(
                output["answer"],
                output["source_ids"],
                output["sources"]
            )
            observed = (
                "none" if citation_ok else citation_failure
            )
        else:
            observed = classify_failure(output)

        return (
            observed == case.expected_failure,
            observed
        )

    if not output["success"]:
        return False, classify_failure(output)

    if output["termination"].lower() != "finish":
        return False, "unexpected_termination"

    citation_ok, citation_failure = check_citations(
        output["answer"],
        output["source_ids"],
        output["sources"]
    )

    if not citation_ok:
        return False, citation_failure

    missing = check_concepts(
        case,
        output["answer"]
    )

    if missing:
        return False, "missing_expected_content"

    return True, "none"


def calculate_cost(input_tokens, output_tokens):
    if INPUT_RATE == 0 and OUTPUT_RATE == 0:
        return None

    return (
        input_tokens * INPUT_RATE
        + output_tokens * OUTPUT_RATE
    ) / 1_000_000


def simulated_failure(case):
    scenarios = {
        "Q21": {
            "success": False,
            "termination": "timeout",
            "answer": "",
            "error": "Search request timed out.",
        },
        "Q22": {
            "success": False,
            "termination": "tool_error",
            "answer": "",
            "error": "HTTP 500 while fetching source.",
        },
        "Q23": {
            "success": True,
            "termination": "finish",
            "answer": (
                "RAM is volatile memory while SSD storage "
                "is persistent [S9]."
            ),
            "source_ids": ["S1"],
            "sources": {
                "S1": {
                    "url": "https://example.com/ram-ssd"
                }
            },
        },
        "Q24": {
            "success": True,
            "termination": "finish",
            "answer": (
                "RAM is volatile memory while SSD storage "
                "is persistent."
            ),
            "source_ids": ["S1"],
            "sources": {
                "S1": {
                    "url": "https://example.com/ram-ssd"
                }
            },
        },
        "Q25": {
            "success": False,
            "termination": "iteration_limit",
            "answer": "",
            "error": (
                "The agent reached its hard iteration limit "
                "before a verified finish was accepted."
            ),
        },
    }

    scenario = scenarios[case.id]

    return {
        "success": scenario.get("success", False),
        "termination": scenario.get(
            "termination", "unknown"
        ),
        "answer": scenario.get("answer", ""),
        "steps": 8 if case.id == "Q25" else 1,
        "tool_calls": 1,
        "input_tokens": 0,
        "output_tokens": 0,
        "source_ids": scenario.get("source_ids", []),
        "sources": scenario.get("sources", {}),
        "error": scenario.get("error", ""),
    }


def execute(case, repetition):
    start = time.perf_counter()

    try:
        if case.mode == "simulated_failure":
            output = simulated_failure(case)
        else:
            output = normalize_output(
                run_agent(case.question)
            )

        passed, failure = grade(case, output)

    except Exception as exc:
        message = str(exc)

        output = {
            "termination": "exception",
            "answer": "",
            "steps": 0,
            "tool_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "source_ids": [],
            "sources": {},
            "error": message,
        }

        passed = False
        failure = (
            "rate_limit"
            if is_rate_limit_error(message)
            else "runtime_error"
        )

    elapsed = round(
        time.perf_counter() - start,
        3
    )

    input_tokens = output["input_tokens"]
    output_tokens = output["output_tokens"]

    return TestResult(
        timestamp_utc=now_utc(),
        case_id=case.id,
        category=case.category,
        mode=case.mode,
        repetition=repetition,
        passed=passed,
        failure=failure,
        termination=output["termination"],
        steps=output["steps"],
        tool_calls=output["tool_calls"],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        estimated_cost_usd=calculate_cost(
            input_tokens,
            output_tokens
        ),
        seconds=elapsed,
        answer=output["answer"],
        error=output["error"],
        source_ids_json=json_safe(
            output["source_ids"]
        ),
        sources_json=json_safe(
            output["sources"]
        ),
        grading_version=GRADING_VERSION,
    )


def append_csv(path, rows):
    if not rows:
        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    exists = (
        path.exists()
        and path.stat().st_size > 0
    )

    fieldnames = list(rows[0].keys())

    if exists:
        with path.open(
            "r",
            newline="",
            encoding="utf-8"
        ) as file:
            reader = csv.DictReader(file)
            old_fields = reader.fieldnames or []
            old_rows = list(reader)

        if old_fields != fieldnames:
            merged_fields = list(dict.fromkeys(
                old_fields + fieldnames
            ))

            with path.open(
                "w",
                newline="",
                encoding="utf-8"
            ) as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=merged_fields
                )
                writer.writeheader()
                writer.writerows(old_rows)

            fieldnames = merged_fields

    with path.open(
        "a",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        if not exists:
            writer.writeheader()

        writer.writerows(rows)


def read_csv(path):
    if not path.exists():
        return []

    with path.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:
        return list(csv.DictReader(file))


def read_history():
    results = []

    for row in read_csv(HISTORY):
        results.append(TestResult(
            timestamp_utc=row["timestamp_utc"],
            case_id=row["case_id"],
            category=row["category"],
            mode=row["mode"],
            repetition=int(row["repetition"]),
            passed=row["passed"].lower() == "true",
            failure=row["failure"],
            termination=row["termination"],
            steps=int(row["steps"]),
            tool_calls=int(row["tool_calls"]),
            input_tokens=int(row["input_tokens"]),
            output_tokens=int(row["output_tokens"]),
            total_tokens=int(row["total_tokens"]),
            estimated_cost_usd=(
                float(row["estimated_cost_usd"])
                if row.get("estimated_cost_usd")
                else None
            ),
            seconds=float(row["seconds"]),
            answer=row["answer"],
            error=row["error"],
            source_ids_json=row.get(
                "source_ids_json", ""
            ),
            sources_json=row.get(
                "sources_json", ""
            ),
            grading_version=row.get(
                "grading_version"
            ) or "v1",
        ))

    return results


def effective_failure(result):
    """
    Reclassify historical HTTP 429 errors
    for analysis without rewriting original rows.
    """
    if is_rate_limit_error(result.error):
        return "rate_limit"

    return result.failure


def create_summary(results):
    live = [
        result for result in results
        if result.mode == "research"
    ]

    successful = [
        result for result in live
        if result.passed
    ]

    quota_blocked = [
        result for result in live
        if effective_failure(result) == "rate_limit"
    ]

    eligible = [
        result for result in live
        if effective_failure(result) != "rate_limit"
    ]

    eligible_successes = [
        result for result in eligible
        if result.passed
    ]

    failures = Counter(
        effective_failure(result)
        for result in live
        if not result.passed
    )

    costs = [
        (
            result.estimated_cost_usd
            if result.estimated_cost_usd is not None
            else calculate_cost(
                result.input_tokens,
                result.output_tokens
            )
        )
        for result in live
    ]

    total_cost = (
        sum(costs)
        if live and all(
            cost is not None
            for cost in costs
        )
        else None
    )

    attempts_per_case = dict(Counter(
        result.case_id for result in live
    ))

    failure_priority = {
        "token_limit": 0,
        "rate_limit": 1,
        "iteration_limit": 2,
    }

    top_three_failures = sorted(
        failures.items(),
        key=lambda item: (
            -item[1],
            failure_priority.get(item[0], 99),
            item[0],
        )
    )[:3]

    return {
        "total_recorded_runs": len(results),
        "unique_live_cases": len({
            result.case_id for result in live
        }),
        "live_runs": len(live),
        "live_successes": len(successful),
        "overall_success_rate": (
            len(successful) / len(live)
            if live else None
        ),
        "rate_limited_runs": len(quota_blocked),
        "quota_excluded_runs": len(eligible),
        "quota_excluded_successes": len(
            eligible_successes
        ),
        "quota_excluded_success_rate": (
            len(eligible_successes) / len(eligible)
            if eligible else None
        ),
        "average_steps": (
            statistics.mean(
                result.steps for result in live
            ) if live else None
        ),
        "average_tool_calls": (
            statistics.mean(
                result.tool_calls for result in live
            ) if live else None
        ),
        "average_tokens": (
            statistics.mean(
                result.total_tokens for result in live
            ) if live else None
        ),
        "total_tokens": sum(
            result.total_tokens for result in live
        ),
        "total_estimated_cost_usd": total_cost,
        "cost_per_success_usd": (
            total_cost / len(successful)
            if total_cost is not None and successful
            else None
        ),
        "failure_categories": dict(failures),
        "top_three_failures": top_three_failures,
        "attempts_per_case": attempts_per_case,
        "simulated_checks": sum(
            result.mode == "simulated_failure"
            for result in results
        ),
    }


def format_rate(value):
    if value is None:
        return "Not measured"

    return f"{value:.1%}"


def save_reports(results, summary):
    REPORTS.mkdir(
        parents=True,
        exist_ok=True
    )

    if results:
        with (REPORTS / "results.csv").open(
            "w",
            newline="",
            encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(
                    asdict(results[0]).keys()
                )
            )
            writer.writeheader()
            writer.writerows(
                asdict(result)
                for result in results
            )

    (REPORTS / "summary.json").write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    lines = [
        "# Agent Reliability Evaluation",
        "",
        "## Success Definition",
        "",
        "A live run passes when the agent reports "
        "success, terminates with `finish`, "
        "passes citation checks, and satisfies "
        "the required concept checks.",
        "",
        "This is a deterministic evaluation proxy, "
        "not independent proof of factual accuracy.",
        "",
        "## Cumulative Results",
        "",
        f"- Unique live cases: "
        f"{summary['unique_live_cases']}",
        f"- Total live attempts: "
        f"{summary['live_runs']}",
        f"- Successful attempts: "
        f"{summary['live_successes']}",
        f"- Overall success rate: "
        f"{format_rate(summary['overall_success_rate'])}",
        f"- Rate-limited attempts: "
        f"{summary['rate_limited_runs']}",
        f"- Quota-excluded success rate: "
        f"{format_rate(summary['quota_excluded_success_rate'])}",
        f"- Average steps: "
        f"{summary['average_steps']}",
        f"- Average tool calls: "
        f"{summary['average_tool_calls']}",
        f"- Average tokens: "
        f"{summary['average_tokens']}",
        f"- Total tokens: "
        f"{summary['total_tokens']}",
        f"- Estimated cost per successful run: "
        f"{summary['cost_per_success_usd']}",
        "",
        "## Failure Categories",
        "",
    ]

    for name, count in summary["failure_categories"].items():
        lines.append(f"- {name}: {count}")

    lines.extend([
        "",
        "## Top Three Failure Categories",
        "",
    ])

    for index, (name, count) in enumerate(
        summary["top_three_failures"], 1
    ):
        lines.append(
            f"{index}. **{name}** — {count} attempts"
        )

    lines.extend([
        "",
        "## Recommended Fixes",
        "",
        "1. Investigate token exhaustion across "
        "research, evidence extraction, and verification.",
        "2. Add rate-limit-aware scheduling and "
        "controlled retries outside the benchmark.",
        "3. Improve evaluation reference answers "
        "and review false negatives.",
        "",
        "## Methodological Limitations",
        "",
        "- Rate-limited attempts remain failures "
        "in the overall observed success rate.",
        "- The quota-excluded rate is a diagnostic "
        "measure, not the primary reliability rate.",
        "- Retries are separate attempts, not "
        "additional unique evaluation cases.",
        "- Historical rate limits are reclassified "
        "for analysis without changing original rows.",
        "- Historical grading versions are mixed "
        "and should be compared separately.",
        "- Q21-Q25 are offline fault-injection "
        "cases that validate harness behavior at "
        "the agent boundary.",
        "- Provider pricing has not been configured.",
        "- Cases use expected concepts, not fully "
        "verified reference answers.",
    ])

    (REPORTS / "analysis.md").write_text(
        "\n".join(lines),
        encoding="utf-8"
    )


def regrade(case_id):
    case_id = case_id.upper()
    case = CASE_LOOKUP.get(case_id)

    if case is None:
        raise ValueError("Unknown case ID.")

    matching = [
        result for result in read_history()
        if result.case_id == case_id
        and result.mode == "research"
    ]

    if not matching:
        print(f"No saved run found for {case_id}.")
        return

    records = []

    for original in matching:
        missing = check_concepts(
            case,
            original.answer
        )

        concept_passed = not missing

        if (
            original.source_ids_json
            and original.sources_json
        ):
            citation_passed, citation_status = (
                check_citations(
                    original.answer,
                    parse_json(
                        original.source_ids_json, []
                    ),
                    parse_json(
                        original.sources_json, {}
                    )
                )
            )
        else:
            citation_passed = False
            citation_status = "not_recheckable"

        if original.termination != "finish":
            revised_status = "agent_did_not_finish"
        elif not concept_passed:
            revised_status = "concept_check_failed"
        elif not citation_passed:
            revised_status = "needs_source_review"
        else:
            revised_status = "passed_v4"

        record = {
            "regraded_at_utc": now_utc(),
            "original_timestamp_utc":
                original.timestamp_utc,
            "case_id": original.case_id,
            "repetition": original.repetition,
            "original_passed": original.passed,
            "original_failure": original.failure,
            "original_grading_version":
                original.grading_version,
            "new_grading_version": GRADING_VERSION,
            "concept_passed": concept_passed,
            "missing_concepts": json_safe(missing),
            "citation_status": citation_status,
            "revised_status": revised_status,
        }

        records.append(record)

        # Corrected f-string syntax.
        concept_status = (
            "PASS" if concept_passed else "FAIL"
        )

        print(
            f"{case_id}: "
            f"original={original.failure}, "
            f"concepts={concept_status}, "
            f"citations={citation_status}, "
            f"revised={revised_status}"
        )

    append_csv(REGRADES, records)
    print(f"Reassessment saved: {REGRADES}")


def print_summary(summary):
    print("\nCUMULATIVE RESULTS")

    print(
        "Unique live cases:",
        summary["unique_live_cases"]
    )
    print(
        "Total live attempts:",
        summary["live_runs"]
    )
    print(
        "Live successes:",
        summary["live_successes"]
    )
    print(
        "Overall success rate:",
        format_rate(summary["overall_success_rate"])
    )
    print(
        "Rate-limited attempts:",
        summary["rate_limited_runs"]
    )
    print(
        "Quota-excluded success rate:",
        format_rate(
            summary["quota_excluded_success_rate"]
        )
    )
    print(
        "Average steps:",
        summary["average_steps"]
    )
    print(
        "Average tokens:",
        summary["average_tokens"]
    )
    print(
        "Cost per success:",
        summary["cost_per_success_usd"]
    )
    print(
        "Top failures:",
        summary["top_three_failures"]
    )


def main():
    parser = argparse.ArgumentParser(
        description="Agent Reliability Harness"
    )

    parser.add_argument(
        "--mode",
        choices=["all", "live", "faults"],
        default="faults"
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1
    )
    parser.add_argument(
        "--case",
        type=str,
        default=None
    )
    parser.add_argument(
        "--summary-only",
        action="store_true"
    )
    parser.add_argument(
        "--regrade",
        type=str,
        default=None
    )

    args = parser.parse_args()

    if args.regrade:
        regrade(args.regrade)
        return

    if args.summary_only:
        history = read_history()

        if not history:
            print("No saved history found.")
            return

        summary = create_summary(history)
        save_reports(history, summary)
        print_summary(summary)
        return

    if args.repeats < 1:
        parser.error(
            "--repeats must be at least 1"
        )

    if args.mode == "live":
        selected = [
            case for case in CASES
            if case.mode == "research"
        ]
    elif args.mode == "faults":
        selected = [
            case for case in CASES
            if case.mode == "simulated_failure"
        ]
    else:
        selected = CASES

    if args.case:
        selected = [
            case for case in selected
            if case.id.upper() == args.case.upper()
        ]

    if not selected:
        parser.error(
            "No cases match your selection."
        )

    print("\nAGENT RELIABILITY HARNESS")
    print(f"Cases: {len(selected)}")
    print(f"Repeats: {args.repeats}")
    print(
        "Total new executions:",
        len(selected) * args.repeats
    )
    print()

    for case in selected:
        for repetition in range(
            1, args.repeats + 1
        ):
            result = execute(case, repetition)

            # Save every run immediately.
            append_csv(
                HISTORY,
                [asdict(result)]
            )

            status = (
                "PASS" if result.passed else "FAIL"
            )

            print(
                f"{case.id} | run {repetition} | "
                f"{status} | {result.termination} | "
                f"{result.total_tokens} tokens"
            )

            if result.error:
                print("  Error:", result.error)

            if not result.passed:
                print("  Failure:", result.failure)

            if result.failure == "rate_limit":
                print(
                    "\nProvider quota reached. "
                    "Stopping remaining evaluations "
                    "to avoid repeated quota failures."
                )

                history = read_history()
                summary = create_summary(history)
                save_reports(history, summary)
                print_summary(summary)
                return

    history = read_history()
    summary = create_summary(history)
    save_reports(history, summary)

    print_summary(summary)

    print(
        "\nReports saved inside "
        "the reports folder."
    )


if __name__ == "__main__":
    main()
