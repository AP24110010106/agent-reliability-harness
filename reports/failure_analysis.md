# Reliability Failure Analysis

## Evaluation Context

The saved benchmark contains 24 live attempts covering all 20
research cases. Six attempts passed under the operational success
definition, giving an observed success rate of 25.0%.

The operational definition of success is exact: the agent must report
`success=True`, terminate with `finish`, include citations that match
declared source identifiers, and cover every required concept for the
case under the versioned deterministic grader.

The harness also defines five offline edge cases, Q21-Q25, for timeout
handling, source-fetch failure, invalid citations, missing citations,
and iteration-limit exhaustion. These are evaluated separately from
the live research success rate.

## Failure Mode 1: Token-Limit Exhaustion

Observed: 11 of 24 live attempts.

These runs consumed the hard token budget before producing a verified
final answer. The pattern suggests repeated context, large retrieved
evidence payloads, and answer synthesis happening too late in the run.

Proposed fix:
- Reduce redundant retrieval and repeated tool context.
- Summarize large evidence payloads before passing them back to the model.
- Reserve a fixed output budget for final-answer generation.
- Add intermediate budget checks before each new search or fetch.

## Failure Mode 2: Provider Rate Limits

Observed: 5 of 24 live attempts.

Rate-limited attempts are counted as failures in the primary success
rate because the user receives no successful answer. They are also
reported separately so agent-quality failures are not confused with
provider quota exhaustion.

Proposed fix:
- Add quota-aware scheduling for benchmark runs.
- Apply bounded backoff only when the quota window can recover.
- Stop immediately on daily quota exhaustion instead of retrying.
- Preserve provider errors separately from answer-quality failures.

## Failure Mode 3: Iteration-Limit Exhaustion

Observed: 1 of 24 live attempts.

The agent reached its hard step limit before a verified finish. Even
though this appeared once in the saved history, it is operationally
important because it points to inefficient control flow rather than
provider availability.

Proposed fix:
- Improve early-stop decisions after enough evidence has been gathered.
- Detect repeated or low-value searches.
- Prefer answer synthesis over another retrieval step near the limit.
- Track step efficiency per case in future benchmark runs.

## Cost

The saved live attempts used 342,536 input tokens and 29,530 output
tokens. Using Groq `openai/gpt-oss-120b` pricing of $0.15 per 1M input
tokens and $0.60 per 1M output tokens, the estimated model-token cost
is $0.069098 total and $0.011516 per successful run.

This estimate excludes free-tier credits, taxes, retries outside the
harness, and non-token platform charges.

## Limitations

Every research case has been executed at least once, but not every
case has multiple repetitions.

Reference concept matching does not establish factual correctness.

The Q06 historical concept-grading failure is preserved in the
original result. Later regrading found concept coverage acceptable,
but full citation verification was not possible because source
metadata was not preserved for that row.

Preserve Project 1 unchanged. Implement evaluation and reporting
improvements in this harness only.
