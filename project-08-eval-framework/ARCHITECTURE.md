# Architecture — LLM Evaluation & Quality Gate System

## Why this project exists in the progression

Every project so far builds LLM applications. This one asks: how do you know if they're working? Evaluation is a first-class skill for AI engineers — you need to be able to measure quality, detect regressions, and block bad deploys. This project implements that infrastructure from scratch.

## Implementation entry point

The evaluation workflow and quality-gate routing are organized under `src/graph/`.

## State

```python
class EvalRunState(TypedDict):
    run_id: str
    dataset_id: str
    app_config: AppConfig             # which app, which model, which prompt version
    baseline_run_id: str | None       # if set, compare against this
    samples: list[EvalSample]
    sample_results: Annotated[list[SampleResult], operator.add]  # fan-in reducer
    aggregated_scores: dict[str, MetricStats] | None
    regression_report: RegressionReport | None
    final_report: EvalReport | None

class EvalSample(BaseModel):
    id: str
    input: str                        # user query
    expected_output: str | None       # ground truth (optional — some metrics don't need it)
    context: list[str] | None         # retrieved chunks, for RAG metrics

class SampleResult(BaseModel):
    sample_id: str
    actual_output: str
    latency_ms: int
    scores: dict[str, float]          # metric_name → 0.0–1.0
    judge_rationale: dict[str, str]   # metric_name → LLM explanation
```

## Metrics

All metrics return a float in [0.0, 1.0]. Higher is better.

### Deterministic metrics (no LLM needed)
- `exact_match` — strict string equality after normalization
- `token_overlap` — Jaccard similarity between predicted and expected token sets
- `latency_ms` — raw latency (not 0–1; reported separately in ms)

### LLM-as-judge metrics
Each is a separate prompt to the judge model. Structured output (Pydantic) enforces `score: float` + `rationale: str`.

- `correctness` — Is the answer factually correct given the expected output?
- `faithfulness` — Does the answer contain only claims supported by the provided context? (RAG)
- `answer_relevance` — Does the answer actually address the question asked?
- `context_precision` — Are the retrieved context chunks relevant, or is there noise?
- `tone_appropriateness` — Is the response tone appropriate for the stated persona?

### Configuring which metrics run
Each dataset has a `metric_set` field. A RAG dataset includes `faithfulness` and `context_precision`. A general chat dataset skips those.

## LLM-as-judge implementation

```python
JUDGE_PROMPT = """
You are an impartial evaluator. Score the following on {metric_name} (0.0 to 1.0).

Rubric:
{rubric}

Question: {input}
Expected: {expected}
Actual: {actual}
Context: {context}

Respond in JSON: {{"score": float, "rationale": str}}
"""
```

The judge model is always a different model or temperature than the app under test — prevents the model from scoring its own outputs.

## Regression detection

```python
def detect_regression(current: dict[str, MetricStats], baseline: dict[str, MetricStats]) -> RegressionReport:
    regressions = []
    for metric, stats in current.items():
        delta = stats.mean - baseline[metric].mean
        if delta < -REGRESSION_THRESHOLD:   # default: -0.05 (5 point drop)
            regressions.append(Regression(metric=metric, delta=delta, severity=classify(delta)))
    return RegressionReport(regressions=regressions, passed=len(regressions) == 0)
```

The `passed` field drives the CI gate.

## CI/CD integration

GitHub Actions sends a POST to `/webhook/github` after every push. The webhook:
1. Creates an eval run against the registered dataset for that repo/branch
2. Waits for completion (polling or webhook callback)
3. Returns HTTP 200 (pass) or HTTP 422 (fail) — GH Actions reads this as success/failure

```yaml
# .github/workflows/eval.yml
- name: Run LLM eval gate
  run: |
    curl -f -X POST https://eval.internal/webhook/github \
      -H "X-Github-Event: push" \
      -d '{"repo": "myorg/myapp", "sha": "${{ github.sha }}"}'
```

## Dataset versioning

Each `POST /datasets/{id}/samples` creates a new dataset version (semver). Eval runs record which version they ran against. This means you can compare `v1.2` vs `v1.3` of a dataset independently of app changes.

## What an interviewer will ask about this

1. "How does LLM-as-judge work, and what are its failure modes?" — A judge model scores outputs against a rubric. Failure modes: position bias (prefers first option in comparisons), self-preference (model prefers its own style), verbosity bias (prefers longer answers). Mitigations: swap order in comparison prompts, use a different judge model, calibrate against human labels.
2. "How do you measure faithfulness for RAG?" — Decompose the answer into atomic claims, then for each claim ask the judge: is this claim supported by the context? Faithfulness = (supported claims) / (total claims).
3. "What's your pass/fail threshold?" — Configurable per metric per dataset. Default: 5-point regression triggers failure. Absolute floor (e.g., correctness < 0.7) always fails regardless of baseline.
4. "How do you handle non-determinism?" — Run each sample N=3 times, take the mean. Report confidence intervals. If variance is high, flag the sample as unstable.
