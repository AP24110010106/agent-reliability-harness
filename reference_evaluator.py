
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from reliability_harness import (
    CASE_LOOKUP,
    check_citations,
    check_concepts,
    parse_json,
    read_history,
)

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
REFERENCES = ROOT / "reference_answers.json"


def evaluate():
    with REFERENCES.open("r", encoding="utf-8") as file:
        references = json.load(file)

    history = read_history()
    rows = []

    for run in history:
        if run.mode != "research":
            continue

        reference = references.get(run.case_id)
        if reference is None:
            continue

        finished = (
            run.termination == "finish"
            and bool(run.answer.strip())
        )

        concept_status = "not_assessable"
        citation_status = "not_assessable"
        missing_concepts = []

        if finished:
            case = CASE_LOOKUP[run.case_id]
            missing_concepts = check_concepts(
                case, run.answer
            )
            concept_status = (
                "pass" if not missing_concepts
                else "fail"
            )

            if run.source_ids_json and run.sources_json:
                source_ids = parse_json(
                    run.source_ids_json, []
                )
                sources = parse_json(
                    run.sources_json, {}
                )

                passed, reason = check_citations(
                    run.answer,
                    source_ids,
                    sources,
                )
                citation_status = (
                    "pass" if passed else reason
                )
            else:
                citation_status = "not_recheckable"

        rows.append({
            "case_id": run.case_id,
            "timestamp_utc": run.timestamp_utc,
            "original_grading_version":
                run.grading_version,
            "original_passed": run.passed,
            "original_failure": run.failure,
            "termination": run.termination,
            "answer_available": finished,
            "concept_status": concept_status,
            "missing_concepts": json.dumps(
                missing_concepts
            ),
            "citation_status": citation_status,
            "reference_answer":
                reference["reference_answer"],
            "answer": run.answer,
        })

    REPORTS.mkdir(parents=True, exist_ok=True)

    csv_path = REPORTS / "reference_comparison.csv"

    with csv_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        if rows:
            writer = csv.DictWriter(
                file,
                fieldnames=list(rows[0].keys())
            )
            writer.writeheader()
            writer.writerows(rows)

    finished_rows = [
        row for row in rows
        if row["answer_available"]
    ]

    concept_passes = sum(
        row["concept_status"] == "pass"
        for row in finished_rows
    )

    citation_counts = Counter(
        row["citation_status"]
        for row in finished_rows
    )

    evaluated_ids = {
        row["case_id"] for row in rows
    }

    all_ids = {
        case_id for case_id in references
    }

    missing_ids = sorted(all_ids - evaluated_ids)

    summary = {
        "generated_at_utc":
            datetime.now(timezone.utc).isoformat(),
        "defined_reference_cases": len(references),
        "unique_live_cases": len(evaluated_ids),
        "recorded_attempts": len(rows),
        "answers_available": len(finished_rows),
        "concept_passes": concept_passes,
        "concept_failures":
            len(finished_rows) - concept_passes,
        "citation_statuses": dict(citation_counts),
        "cases_without_recorded_runs": missing_ids,
        "methodology": (
            "Concept coverage is a deterministic "
            "keyword proxy. Citation checks validate "
            "structure and declared source IDs, not "
            "the factual support of source content. "
            "No automatic semantic equivalence or "
            "factual correctness is claimed."
        ),
    }

    json_path = REPORTS / "reference_summary.json"
    json_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nREFERENCE EVALUATION")
    print("Defined cases:", len(references))
    print("Unique live cases:", len(evaluated_ids))
    print("Recorded attempts:", len(rows))
    print("Answers available:", len(finished_rows))
    print("Concept checks passed:", concept_passes)
    print("Citation statuses:", dict(citation_counts))
    print("Unexecuted cases:", ", ".join(missing_ids))
    print("\nReports:")
    print(csv_path)
    print(json_path)


if __name__ == "__main__":
    evaluate()
