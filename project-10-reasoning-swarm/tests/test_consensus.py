import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from src.models import AgentTurn, Round
from src.consensus import compute_agreement_score


def _unit_vec(seed: int, dim: int = 10) -> list[float]:
    rng = np.random.default_rng(seed)
    v = rng.random(dim)
    return (v / np.linalg.norm(v)).tolist()


def _mock_embedding_response(embeddings: list[list[float]]) -> MagicMock:
    response = MagicMock()
    response.data = [MagicMock(embedding=e) for e in embeddings]
    return response


@pytest.mark.asyncio
async def test_no_proposer_claims_returns_default():
    rnd = Round(round_number=1, turns=[])
    score = await compute_agreement_score(rnd)
    assert score == 0.5


@pytest.mark.asyncio
async def test_no_critic_claims_returns_default():
    turn = AgentTurn(agent="proposer", content="p", confidence=0.8, key_claims=["claim A"])
    rnd = Round(round_number=1, turns=[turn])
    score = await compute_agreement_score(rnd)
    assert score == 0.5


@pytest.mark.asyncio
async def test_identical_claims_score_near_one():
    proposer = AgentTurn(agent="proposer", content="p", confidence=0.8, key_claims=["X is true"])
    critic = AgentTurn(agent="critic", content="c", confidence=0.6, key_claims=["X is true"])
    rnd = Round(round_number=1, turns=[proposer, critic])

    emb = _unit_vec(42)
    mock_resp = _mock_embedding_response([emb, emb])

    with patch("src.consensus.AsyncOpenAI") as MockClient:
        instance = AsyncMock()
        instance.embeddings.create = AsyncMock(return_value=mock_resp)
        MockClient.return_value = instance

        score = await compute_agreement_score(rnd)

    assert abs(score - 1.0) < 1e-6


@pytest.mark.asyncio
async def test_orthogonal_claims_score_near_zero():
    proposer = AgentTurn(agent="proposer", content="p", confidence=0.8, key_claims=["claim A"])
    critic = AgentTurn(agent="critic", content="c", confidence=0.6, key_claims=["claim B"])
    rnd = Round(round_number=1, turns=[proposer, critic])

    e1 = [1.0, 0.0, 0.0]
    e2 = [0.0, 1.0, 0.0]
    mock_resp = _mock_embedding_response([e1, e2])

    with patch("src.consensus.AsyncOpenAI") as MockClient:
        instance = AsyncMock()
        instance.embeddings.create = AsyncMock(return_value=mock_resp)
        MockClient.return_value = instance

        score = await compute_agreement_score(rnd)

    assert abs(score) < 1e-6


@pytest.mark.asyncio
async def test_score_within_bounds():
    proposer = AgentTurn(agent="proposer", content="p", confidence=0.8, key_claims=["A", "B"])
    critic = AgentTurn(agent="critic", content="c", confidence=0.6, key_claims=["C"])
    rnd = Round(round_number=1, turns=[proposer, critic])

    embs = [_unit_vec(i) for i in range(3)]
    mock_resp = _mock_embedding_response(embs)

    with patch("src.consensus.AsyncOpenAI") as MockClient:
        instance = AsyncMock()
        instance.embeddings.create = AsyncMock(return_value=mock_resp)
        MockClient.return_value = instance

        score = await compute_agreement_score(rnd)

    assert 0.0 <= score <= 1.0
