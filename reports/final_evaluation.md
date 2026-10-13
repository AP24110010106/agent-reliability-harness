# Agent Reliability Harness
## Final Evaluation Report

Generated: 2026-10-13 06:26 UTC

### 1. Objective

Evaluate the reliability of an existing tool-using research agent
using a reproducible test harness.

The harness records execution outcomes, termination reasons,
token usage, citations, concept coverage, and failure categories.

The evaluated research agent is a separate project.
Its source code was not modified for this evaluation.

### 2. Benchmark Dataset

- Defined research cases: 20
- Unique research cases executed: 20
- Recorded live attempts: 24
- Draft reference answers: 20
- Saved finished answers available for reference checks: 7

The 24 recorded attempts do not represent repeated execution
of every individual case.

The harness also defines 5 offline edge-case evaluations
for timeout handling, source-fetch failures, invalid citations,
missing citations, and iteration-limit exhaustion. Together,
the suite covers 25 evaluation cases: 20 live research prompts
plus 5 genuine harness-level edge cases.

### 3. Reliability Metrics

| Metric | Result |
|---|---:|
| Total attempts | 24 |
| Successful attempts | 6 |
| Observed success rate | 25.0% |
| Rate-limited attempts | 5 |
| Success rate excluding rate limits | 31.6% |
| Average agent steps | 5.33 |
| Total input tokens | 342,536 |
| Total output tokens | 29,530 |
| Total tokens | 372,066 |
| Average tokens per attempt | 15,502.75 |
| Estimated total model cost | $0.069098 |
| Estimated cost per success | $0.011516 |

Exact operational success definition: a live attempt is counted
as successful only when the research agent reports `success=True`,
terminates with `finish`, includes citations that match declared
source identifiers, and covers every required concept for that
case under the versioned deterministic grader. The observed
success rate is successful live attempts divided by all recorded
live research attempts: 6/24 = 25.0%.

The quota-excluded rate removes rate-limited attempts from
the denominator. It is a secondary diagnostic metric,
not a replacement for the overall success rate.

Cost uses saved input and output token counts multiplied by
the stated model-token rates. Pricing assumption:
Groq openai/gpt-oss-120b
at $0.15/1M input
tokens and $0.60/1M
output tokens, as documented by the provider model table:
https://console.groq.com/docs/models.
The estimate excludes free-tier credits, taxes, non-token
charges, and retries outside the saved harness history.

### 4. Failure Analysis

| Failure category | Attempts |
|---|---:|
| token_limit | 11 |
| rate_limit | 5 |
| iteration_limit | 1 |
| missing_expected_content | 1 |

Top three failure modes:

| Rank | Failure mode | Attempts |
|---:|---|---:|
| 1 | token_limit | 11 |
| 2 | rate_limit | 5 |
| 3 | iteration_limit | 1 |

**1. Token-budget exhaustion.** The most common failure was
the agent consuming its hard token budget before returning a
verified final answer. This points to oversized retrieved
evidence, repeated context, and late synthesis.

**2. Provider rate limits.** Rate-limited runs reflect external
quota exhaustion on the configured model provider. They are
counted as failures in the primary success rate because an
operational user still receives no successful answer.

**3. Iteration-limit exhaustion.** The agent sometimes exhausted
its maximum step budget before a verified finish. This suggests
redundant search/fetch cycles and weak early-stop decisions.

An earlier Q06 attempt was marked as missing expected content.
Later regrading found its concept coverage acceptable, but
its citation metadata was insufficient for full retrospective
verification. The original historical result is preserved.

### 5. Reference Evaluation

- Finished answers assessed: 7
- Concept checks passed: 7
- Citation verification outcomes: {"not_recheckable": 1, "pass": 6}

Concept matching is a deterministic proxy for coverage.
It does not prove factual correctness or semantic equivalence.

Citation validation checks citation structure and declared
source identifiers. It does not independently establish
whether a source supports every factual claim.

### 6. Edge-Case and Fault-Injection Testing

The offline test suite and Q21-Q25 edge cases include
agent-boundary tests for:

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

Q21-Q25 are deterministic offline edge cases. They are not
mixed into the live research success rate, but they do count
toward the 20+ evaluation-case requirement because each case
has a concrete expected failure behavior and pass/fail outcome.

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
6. USD costs are estimates from published token rates, not
   proof of actual invoice totals.
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
