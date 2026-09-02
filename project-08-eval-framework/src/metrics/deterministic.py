from __future__ import annotations

import re


def _normalize(text: str) -> str:
    text = re.sub(r"[^\w\s]", "", text)
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


def f1_score(predicted: str, expected: str) -> float:
    pred_tokens = _normalize(predicted).split()
    exp_tokens = _normalize(expected).split()
    if not pred_tokens and not exp_tokens:
        return 1.0
    if not pred_tokens or not exp_tokens:
        return 0.0
    pred_set = set(pred_tokens)
    exp_set = set(exp_tokens)
    common = pred_set & exp_set
    precision = len(common) / len(pred_set)
    recall = len(common) / len(exp_set)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


DETERMINISTIC_METRICS = {
    "exact_match": exact_match,
    "token_overlap": token_overlap,
    "f1": f1_score,
}
