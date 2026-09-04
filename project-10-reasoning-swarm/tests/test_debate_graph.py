import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.models import AgentTurn, Round, ConsensusAnswer


def _make_turns() -> list[AgentTurn]:
    return [
        AgentTurn(agent="proposer", content="p", confidence=0.9, key_claims=["A"]),
        AgentTurn(agent="critic", content="c", confidence=0.7, key_claims=["B"]),
        AgentTurn(agent="devil_advocate", content="d", confidence=0.6, key_claims=["C"]),
        AgentTurn(agent="rebuttal", content="r", confidence=0.85, key_claims=["A refined"]),
    ]


def _synth_llm_mock(answer: str, confidence: float):
    output = MagicMock()
    output.answer = answer
    output.confidence = confidence
    output.dissenting_views = []
    output.key_reasoning = ["reasoning chain"]
    output.uncertainty_flags = []

    chain = AsyncMock()
    chain.ainvoke = AsyncMock(return_value=output)

    llm = MagicMock()
    llm.with_structured_output = MagicMock(return_value=chain)
    return llm


@pytest.mark.asyncio
async def test_debate_exits_early_on_consensus():
    with (
        patch("src.graph.debate_graph.round_graph") as mock_rg,
        patch("src.graph.debate_graph.compute_agreement_score", new_callable=AsyncMock) as mock_score,
        patch("src.agents.synthesizer.get_llm", return_value=_synth_llm_mock("A is true", 0.9)),
    ):
        mock_rg.ainvoke = AsyncMock(return_value={"turns": _make_turns(), "summary": "good round"})
        mock_score.return_value = 0.85

        from src.graph.debate_graph import build_debate_graph

        graph = build_debate_graph()
        result = await graph.ainvoke({
            "debate_id": "test-id",
            "question": "Is A true?",
            "domain": "test",
            "rounds": [],
            "current_round": 0,
            "max_rounds": 3,
            "consensus_reached": False,
            "final_answer": None,
        })

    assert result["consensus_reached"] is True
    assert result["current_round"] == 1
    assert result["final_answer"] is not None
    assert result["final_answer"].answer == "A is true"


@pytest.mark.asyncio
async def test_debate_runs_max_rounds_without_consensus():
    call_count = 0

    async def mock_score(rnd):
        return 0.3

    async def mock_round_invoke(state):
        nonlocal call_count
        call_count += 1
        return {"turns": _make_turns(), "summary": f"round {call_count}"}

    with (
        patch("src.graph.debate_graph.round_graph") as mock_rg,
        patch("src.graph.debate_graph.compute_agreement_score", side_effect=mock_score),
        patch("src.agents.synthesizer.get_llm", return_value=_synth_llm_mock("best guess", 0.5)),
    ):
        mock_rg.ainvoke = mock_round_invoke

        from src.graph.debate_graph import build_debate_graph

        graph = build_debate_graph()
        result = await graph.ainvoke({
            "debate_id": "test-id",
            "question": "Hard question?",
            "domain": "philosophy",
            "rounds": [],
            "current_round": 0,
            "max_rounds": 2,
            "consensus_reached": False,
            "final_answer": None,
        })

    assert result["current_round"] == 2
    assert result["consensus_reached"] is False
    assert call_count == 2
    assert result["final_answer"] is not None


@pytest.mark.asyncio
async def test_debate_debate_id_preserved():
    with (
        patch("src.graph.debate_graph.round_graph") as mock_rg,
        patch("src.graph.debate_graph.compute_agreement_score", new_callable=AsyncMock) as mock_score,
        patch("src.agents.synthesizer.get_llm", return_value=_synth_llm_mock("answer", 0.8)),
    ):
        mock_rg.ainvoke = AsyncMock(return_value={"turns": _make_turns(), "summary": "ok"})
        mock_score.return_value = 0.9

        from src.graph.debate_graph import build_debate_graph

        graph = build_debate_graph()
        result = await graph.ainvoke({
            "debate_id": "fixed-id-123",
            "question": "Q?",
            "domain": "general",
            "rounds": [],
            "current_round": 0,
            "max_rounds": 3,
            "consensus_reached": False,
            "final_answer": None,
        })

    assert result["debate_id"] == "fixed-id-123"
