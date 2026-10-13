# Agent Reliability Harness

## Overview
A Python evaluation framework for measuring the reliability of a tool-using research agent.

## Features
- 25 evaluation cases: 20 live research prompts and 5 offline edge cases
- Reference-answer comparison
- Citation and concept validation
- Failure classification
- Agent-boundary fault injection
- Token usage and cost analysis
- Automated CSV, JSON and Markdown reports

## Verified Results
- Research coverage: 20/20 cases
- Live attempts: 24
- Successful attempts: 6
- Overall success rate: 25.0%
- Quota-excluded success rate: 31.6%
- Success definition: `success=True`, `finish` termination, valid declared citations, and required concept coverage
- Average steps: 5.33
- Total tokens: 372,066
- Estimated total model-token cost: $0.069098
- Estimated cost per successful run: $0.011516
- Pricing assumption: Groq `openai/gpt-oss-120b` at $0.15/1M input tokens and $0.60/1M output tokens
- Offline tests: 26 passed

## Key Findings
- Token-limit failures: 11
- Rate-limit failures: 5
- Iteration-limit failures: 1
- Historical concept-grading failure: 1

## Run Tests
python -m unittest discover -v

## Generate Reports
python reliability_harness.py --summary-only
python reference_evaluator.py
python cost_analyzer.py
python final_report.py

## Live Evaluation
python reliability_harness.py --mode live --case Q01 --repeats 1

Requires the separate research-agent project and configured API credentials.

## Main Report
reports/final_evaluation.md

## Limitations
Not all research cases have repeated runs.
Concept matching does not prove factual correctness.
Fault injection validates harness handling at the agent boundary.
USD cost estimates use published token rates, not invoice data.

## Project Integrity
The original research agent remains unchanged.
Historical results and baseline snapshots are preserved.
