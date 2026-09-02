from __future__ import annotations

import pytest

from src.models import AppConfig, EvalSample


@pytest.fixture
def app_config() -> AppConfig:
    return AppConfig(app_id="test-app", model="gpt-4o-mini", prompt_version="v1")


@pytest.fixture
def basic_sample() -> EvalSample:
    return EvalSample(
        input="What is the capital of France?",
        expected_output="Paris",
        context=["France is a country in Western Europe. Its capital is Paris."],
    )


@pytest.fixture
def sample_no_context() -> EvalSample:
    return EvalSample(
        input="Summarize the document.",
        expected_output="The document discusses AI safety.",
    )
