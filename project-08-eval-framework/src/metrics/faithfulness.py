from __future__ import annotations

import json
import re

from langchain_openai import ChatOpenAI

from src.config import settings


class AtomicClaims(object):
    def __init__(self, claims: list[str]) -> None:
        self.claims = claims


_DECOMPOSE_PROMPT = """\
Decompose the following answer into a list of atomic factual claims.
Each claim must be a single sentence asserting exactly one fact.
Respond with JSON: {{"claims": ["claim 1", "claim 2", ...]}}

Answer: {answer}
"""

_VERIFY_PROMPT = """\
Given the context below, is the following claim supported by the context?
Answer only "yes" or "no".

Context:
{context}

Claim: {claim}
"""


async def compute_faithfulness(
    answer: str,
    context: list[str],
) -> tuple[float, str]:
    if not context or not answer:
        return 1.0, "no context to check"

    llm = ChatOpenAI(model=settings.judge_model, temperature=0.0)

    decompose_response = await llm.ainvoke(
        _DECOMPOSE_PROMPT.format(answer=answer)
    )
    claims = _parse_claims(str(decompose_response.content))

    if not claims:
        return 1.0, "no atomic claims extracted"

    context_str = "\n".join(context)
    supported = 0
    for claim in claims:
        verdict = await llm.ainvoke(
            _VERIFY_PROMPT.format(context=context_str, claim=claim)
        )
        if "yes" in str(verdict.content).lower():
            supported += 1

    score = supported / len(claims)
    rationale = f"{supported}/{len(claims)} claims supported by context"
    return score, rationale


def _parse_claims(raw: str) -> list[str]:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group())
        return [str(c) for c in data.get("claims", [])]
    except Exception:
        return []
