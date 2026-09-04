import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from src.api.main import app
from src.models import ConsensusAnswer


def _final_state(debate_id: str = "test-id", consensus: bool = True) -> dict:
    return {
        "debate_id": debate_id,
        "question": "Test question?",
        "domain": "general",
        "rounds": [],
        "current_round": 1,
        "max_rounds": 3,
        "consensus_reached": consensus,
        "final_answer": ConsensusAnswer(answer="yes", confidence=0.9) if consensus else None,
    }


@pytest.mark.asyncio
async def test_create_debate_returns_201():
    with (
        patch("src.api.routes.debate_graph") as mock_graph,
        patch("src.api.routes.save_debate", new_callable=AsyncMock),
        patch("src.db.database.SessionLocal") as mock_session,
    ):
        mock_graph.ainvoke = AsyncMock(return_value=_final_state())
        mock_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/debates", json={"question": "Test question?"})

    assert resp.status_code == 201
    data = resp.json()
    assert "debate_id" in data
    assert data["consensus_reached"] is True


@pytest.mark.asyncio
async def test_get_debate_not_found():
    with (
        patch("src.api.routes.load_debate", new_callable=AsyncMock) as mock_load,
        patch("src.db.database.SessionLocal") as mock_session,
    ):
        mock_load.return_value = None
        mock_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/debates/nonexistent-id")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Debate not found"


@pytest.mark.asyncio
async def test_get_consensus_not_found():
    with (
        patch("src.api.routes.load_debate", new_callable=AsyncMock) as mock_load,
        patch("src.db.database.SessionLocal") as mock_session,
    ):
        mock_load.return_value = None
        mock_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/debates/nonexistent-id/consensus")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_challenge_not_found():
    with (
        patch("src.api.routes.load_debate", new_callable=AsyncMock) as mock_load,
        patch("src.db.database.SessionLocal") as mock_session,
    ):
        mock_load.return_value = None
        mock_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/debates/bad-id/challenge", json={"challenge_text": "prove it"})

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_challenge_debate_success():
    db_record = MagicMock()
    db_record.question = "Original question?"
    db_record.domain = "general"

    with (
        patch("src.api.routes.load_debate", new_callable=AsyncMock) as mock_load,
        patch("src.api.routes.save_debate", new_callable=AsyncMock),
        patch("src.api.routes.debate_graph") as mock_graph,
        patch("src.db.database.SessionLocal") as mock_session,
    ):
        mock_load.return_value = db_record
        mock_graph.ainvoke = AsyncMock(return_value=_final_state("existing-id"))
        mock_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/debates/existing-id/challenge",
                json={"challenge_text": "but what about edge case Y?"},
            )

    assert resp.status_code == 200
    assert resp.json()["challenge_processed"] is True
