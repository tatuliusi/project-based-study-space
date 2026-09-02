from __future__ import annotations

import pytest

from src.metrics.deterministic import exact_match, token_overlap


class TestExactMatch:
    def test_identical(self):
        assert exact_match("hello world", "hello world") == 1.0

    def test_case_insensitive(self):
        assert exact_match("Hello World", "hello world") == 1.0

    def test_extra_whitespace(self):
        assert exact_match("  hello   world  ", "hello world") == 1.0

    def test_mismatch(self):
        assert exact_match("hello", "world") == 0.0

    def test_partial_match_is_zero(self):
        assert exact_match("hello world", "hello") == 0.0


class TestTokenOverlap:
    def test_identical(self):
        assert token_overlap("the cat sat", "the cat sat") == 1.0

    def test_no_overlap(self):
        assert token_overlap("dog runs fast", "cat jumps high") == 0.0

    def test_partial_overlap(self):
        score = token_overlap("the cat sat on the mat", "the cat")
        assert 0.0 < score < 1.0

    def test_both_empty(self):
        assert token_overlap("", "") == 1.0

    def test_one_empty(self):
        assert token_overlap("hello", "") == 0.0

    def test_symmetry(self):
        a = "quick brown fox"
        b = "fox jumps lazy"
        assert token_overlap(a, b) == token_overlap(b, a)
