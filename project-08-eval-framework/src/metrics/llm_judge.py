from __future__ import annotations

import json
import re

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config import settings


class JudgeOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    rationale: str


RUBRICS: dict[str, str] = {
    "correctness": (
        "Is the actual output factually correct given the expected output? "
        "1.0 = fully correct, 0.5 = partially correct, 0.0 = incorrect."
    ),
    "faithfulness": (
        "Does the actual output contain only claims supported by the provided context? "
        "1.0 = fully grounded, 0.0 = hallucinated or contradicts context."
    ),
    "answer_relevance": (
        "Does the actual output directly address the question? "
        "1.0 = fully addresses the question, 0.0 = completely off-topic."
    ),
    "context_precision": (
        "Are the retrieved context chunks relevant to the question? "
        "1.0 = all chunks are relevant, 0.0 = all chunks are noise."
    ),
    "tone_appropriateness": (
        "Is the tone of the actual output appropriate and professional? "
        "1.0 = perfectly appropriate, 0.0 = inappropriate or unprofessional."
    ),
}

_JUDGE_TEMPLATE = """\
You are an impartial evaluator. Score the following on {metric_name} (0.0 to 1.0).

Rubric:
{rubric}

Question: {input}
Expected: {expected}
Actual: {actual}
Context: {context}

Respond in JSON: {{"score": <float 0.0-1.0>, "rationale": "<one sentence>"}}
"""


def _build_judge() -> ChatOpenAI:
    return ChatOpenAI(model=settings.judge_model, temperature=0.0)


def _parse_judge_output(raw: str) -> JudgeOutput:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return JudgeOutput(score=0.0, rationale="parse error")
    try:
        data = json.loads(match.group())
        return JudgeOutput(**data)
    except Exception:
        return JudgeOutput(score=0.0, rationale="parse error")


async def judge(
    metric_name: str,
    input_text: str,
    actual: str,
    expected: str | None = None,
    context: list[str] | None = None,
) -> JudgeOutput:
    if metric_name == "faithfulness" and context:
        from src.metrics.faithfulness import compute_faithfulness
        score, rationale = await compute_faithfulness(actual, context)
        return JudgeOutput(score=score, rationale=rationale)

    rubric = RUBRICS.get(metric_name, "Score quality on a 0.0-1.0 scale.")
    prompt = _JUDGE_TEMPLATE.format(
        metric_name=metric_name,
        rubric=rubric,
        input=input_text,
        expected=expected or "N/A",
        actual=actual,
        context="\n".join(context) if context else "N/A",
    )
    llm = _build_judge()
    response = await llm.ainvoke(prompt)
    return _parse_judge_output(str(response.content))


LLM_METRICS = set(RUBRICS.keys())
