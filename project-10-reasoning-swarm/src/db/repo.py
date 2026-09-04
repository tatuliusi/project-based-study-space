import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.db.orm import DebateRecord, RoundRecord, AgentTurnRecord
from src.models import DebateState


async def save_debate(session: AsyncSession, state: DebateState) -> None:
    debate = DebateRecord(
        id=state["debate_id"],
        question=state["question"],
        domain=state["domain"],
        max_rounds=state["max_rounds"],
        consensus_reached=state["consensus_reached"],
    )
    if state["final_answer"]:
        debate.final_answer = state["final_answer"].answer
        debate.final_confidence = state["final_answer"].confidence
    session.add(debate)
    await session.flush()

    for rnd in state["rounds"]:
        round_rec = RoundRecord(
            debate_id=state["debate_id"],
            round_number=rnd.round_number,
            summary=rnd.summary,
            agreement_score=rnd.agreement_score,
        )
        session.add(round_rec)
        await session.flush()

        for turn in rnd.turns:
            turn_rec = AgentTurnRecord(
                round_id=round_rec.id,
                agent=turn.agent,
                content=turn.content,
                confidence=turn.confidence,
                key_claims=json.dumps(turn.key_claims),
                citations=json.dumps(turn.citations),
            )
            session.add(turn_rec)

    await session.commit()


async def load_debate(session: AsyncSession, debate_id: str) -> DebateRecord | None:
    result = await session.execute(
        select(DebateRecord)
        .options(selectinload(DebateRecord.rounds).selectinload(RoundRecord.turns))
        .where(DebateRecord.id == debate_id)
    )
    return result.scalar_one_or_none()
