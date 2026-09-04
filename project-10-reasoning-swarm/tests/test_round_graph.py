import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models import RoundState


def _llm_mock_for(agent: str, content: str, confidence: float, claims: list[str]):
    output = MagicMock()
    output.position = content
    output.critique = content
    output.counterposition = content
    output.rebuttal = content
    output.confidence = confidence
    output.key_claims = claims
    output.citations = []
    output.summary = f"summary for {agent}"

    chain = AsyncMock()
    chain.ainvoke = AsyncMock(return_value=output)

    llm = MagicMock()
    llm.with_structured_output = MagicMock(return_value=chain)
    return llm


@pytest.mark.asyncio
async def test_round_graph_produces_four_turns():
    with (
        patch("src.agents.proposer.get_llm", return_value=_llm_mock_for("proposer", "position X", 0.8, ["X"])),
        patch("src.agents.critic.get_llm", return_value=_llm_mock_for("critic", "X has gap", 0.6, ["gap"])),
        patch("src.agents.devil_advocate.get_llm", return_value=_llm_mock_for("da", "counter X", 0.5, ["counter"])),
        patch("src.agents.rebuttal.get_llm", return_value=_llm_mock_for("rebuttal", "X holds", 0.75, ["refined X"])),
        patch("src.agents.round_summary.get_llm", return_value=_llm_mock_for("summary", "", 0.0, [])),
    ):
        from src.graph.round_graph import build_round_graph

        rg = build_round_graph()
        state: RoundState = {
            "debate_id": "test-debate",
            "question": "Is X true?",
            "domain": "philosophy",
            "round_number": 1,
            "prior_rounds": [],
            "turns": [],
            "summary": "",
            "agreement_score": 0.0,
        }
        result = await rg.ainvoke(state)

    assert len(result["turns"]) == 4
    agents = [t.agent for t in result["turns"]]
    assert agents == ["proposer", "critic", "devil_advocate", "rebuttal"]


@pytest.mark.asyncio
async def test_round_graph_propagates_prior_rounds():
    from src.models import Round, AgentTurn

    prior_turn = AgentTurn(agent="proposer", content="old position", confidence=0.7, key_claims=["old"])
    prior_round = Round(round_number=1, turns=[prior_turn])

    with (
        patch("src.agents.proposer.get_llm", return_value=_llm_mock_for("proposer", "refined", 0.85, ["refined X"])),
        patch("src.agents.critic.get_llm", return_value=_llm_mock_for("critic", "still gaps", 0.55, ["gap2"])),
        patch("src.agents.devil_advocate.get_llm", return_value=_llm_mock_for("da", "new counter", 0.45, ["nc"])),
        patch("src.agents.rebuttal.get_llm", return_value=_llm_mock_for("rebuttal", "holds refined", 0.8, ["hr"])),
        patch("src.agents.round_summary.get_llm", return_value=_llm_mock_for("summary", "", 0.0, [])),
    ):
        from src.graph.round_graph import build_round_graph

        rg = build_round_graph()
        state: RoundState = {
            "debate_id": "test-debate",
            "question": "Is X true?",
            "domain": "philosophy",
            "round_number": 2,
            "prior_rounds": [prior_round],
            "turns": [],
            "summary": "",
            "agreement_score": 0.0,
        }
        result = await rg.ainvoke(state)

    assert result["turns"][0].content == "refined"
    assert result["turns"][0].confidence == 0.85
