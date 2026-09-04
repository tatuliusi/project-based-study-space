import pytest
from pydantic import ValidationError
from src.models import AgentTurn, Round, ConsensusAnswer


def test_agent_turn_valid():
    turn = AgentTurn(agent="proposer", content="test", confidence=0.8, key_claims=["claim1"])
    assert turn.agent == "proposer"
    assert turn.confidence == 0.8
    assert turn.key_claims == ["claim1"]


def test_agent_turn_confidence_too_high():
    with pytest.raises(ValidationError):
        AgentTurn(agent="proposer", content="x", confidence=1.5)


def test_agent_turn_confidence_negative():
    with pytest.raises(ValidationError):
        AgentTurn(agent="proposer", content="x", confidence=-0.1)


def test_agent_turn_invalid_role():
    with pytest.raises(ValidationError):
        AgentTurn(agent="unknown_role", content="x", confidence=0.5)


def test_round_defaults():
    rnd = Round(round_number=1)
    assert rnd.turns == []
    assert rnd.summary == ""
    assert rnd.agreement_score == 0.0


def test_round_with_turns():
    turn = AgentTurn(agent="critic", content="weak argument", confidence=0.7)
    rnd = Round(round_number=2, turns=[turn], summary="critic challenged proposer", agreement_score=0.4)
    assert len(rnd.turns) == 1
    assert rnd.agreement_score == 0.4


def test_consensus_answer_defaults():
    ca = ConsensusAnswer(answer="The answer is X", confidence=0.9)
    assert ca.dissenting_views == []
    assert ca.key_reasoning == []
    assert ca.uncertainty_flags == []


def test_consensus_answer_full():
    ca = ConsensusAnswer(
        answer="X is true",
        confidence=0.85,
        dissenting_views=["some disagree"],
        key_reasoning=["because evidence Y"],
        uncertainty_flags=["edge case Z"],
    )
    assert ca.confidence == 0.85
    assert len(ca.dissenting_views) == 1
    assert len(ca.uncertainty_flags) == 1
