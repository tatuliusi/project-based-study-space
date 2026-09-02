from __future__ import annotations

import re


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def exact_match(predicted: str, expected: str) -> float:
    return 1.0 if _normalize(predicted) == _normalize(expected) else 0.0


def token_overlap(predicted: str, expected: str) -> float:
    pred_tokens = set(_normalize(predicted).split())
    exp_tokens = set(_normalize(expected).split())
    if not pred_tokens and not exp_tokens:
        return 1.0
    if not pred_tokens or not exp_tokens:
        return 0.0
    intersection = pred_tokens & exp_tokens
    union = pred_tokens | exp_tokens
    return len(intersection) / len(union)


DETERMINISTIC_METRICS = {
    "exact_match": exact_match,
    "token_overlap": token_overlap,
}
