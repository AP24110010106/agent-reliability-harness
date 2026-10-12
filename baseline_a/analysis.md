# Agent Reliability Evaluation

## Success Definition

A live run passes when the agent reports success, terminates with `finish`, passes citation checks, and satisfies the required concept checks.

This is a deterministic evaluation proxy, not independent proof of factual accuracy.

## Cumulative Results

- Unique live cases: 9
- Total live attempts: 13
- Successful attempts: 3
- Overall success rate: 23.1%
- Rate-limited attempts: 5
- Quota-excluded success rate: 37.5%
- Average steps: 4.6923076923076925
- Average tool calls: 3
- Average tokens: 12861.23076923077
- Total tokens: 167196
- Estimated cost per successful run: None

## Failure Categories

- missing_expected_content: 1
- token_limit: 4
- rate_limit: 5

## Top Three Failure Categories

1. **rate_limit** — 5 attempts
2. **token_limit** — 4 attempts
3. **missing_expected_content** — 1 attempts

## Recommended Fixes

1. Investigate token exhaustion across research, evidence extraction, and verification.
2. Add rate-limit-aware scheduling and controlled retries outside the benchmark.
3. Improve evaluation reference answers and review false negatives.

## Methodological Limitations

- Rate-limited attempts remain failures in the overall observed success rate.
- The quota-excluded rate is a diagnostic measure, not the primary reliability rate.
- Retries are separate attempts, not additional unique evaluation cases.
- Historical rate limits are reclassified for analysis without changing original rows.
- Historical grading versions are mixed and should be compared separately.
- Q21-Q25 are simulated placeholders, not genuine fault-injection tests.
- Provider pricing has not been configured.
- Cases use expected concepts, not fully verified reference answers.