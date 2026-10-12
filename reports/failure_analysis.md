# Reliability Failure Analysis

## Evaluation Context

The saved benchmark contains 13 live attempts covering 9 unique research cases. Three attempts passed under their original grading rules, giving an observed success rate of 23.1%.

Five attempts were rate-limited. Excluding those attempts gives a diagnostic success rate of 37.5%, but this is not the primary observed reliability rate.

## Failure Mode 1: Provider Rate Limits

Observed: 5 of 13 attempts.

All five rate-limit failures occurred on Q14. They represent repeated attempts of the same question, not independent test cases.

Proposed fix:
- Add quota-aware scheduling.
- Apply bounded exponential backoff.
- Avoid retrying when the daily quota is exhausted.
- Record provider errors separately from answer-quality failures.

## Failure Mode 2: Token-Limit Exhaustion

Observed: 4 of 13 attempts.

These runs terminated before producing final answers.

Proposed fix:
- Reduce redundant retrieval.
- Summarize large tool outputs.
- Reserve tokens for final-answer generation.
- Compare completion rates before and after optimization.

## Failure Mode 3: Grading False Negatives

Observed: Q06 originally failed the expected-content check.

Under grading version v4, Q06 passes the concept check. Its citations cannot be fully rechecked because source metadata was not preserved.

Proposed fix:
- Use reviewed reference answers.
- Support grammatical variations in concept matching.
- Version the grader.
- Require human review where citation evidence is unavailable.

## Limitations

The evaluation contains only 9 unique live cases in the persisted history, despite 20 planned research cases.

Q21-Q25 remain simulated placeholders rather than genuine fault-injection experiments.

Reference concept matching does not establish factual correctness.

Token pricing is not configured, so cost per successful run is not yet available.

## Fix-First Recommendation

Prioritize reducing token exhaustion and improving completion reliability while scheduling further benchmark runs around provider quota limits.

Preserve Project 1 unchanged. Implement evaluation and reporting improvements in Project 2.
