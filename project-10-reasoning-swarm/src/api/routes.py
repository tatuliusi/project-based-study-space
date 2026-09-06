import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_session
from src.db.repo import save_debate, load_debate, list_debates
from src.graph.debate_graph import debate_graph
from src.models import DebateState
from src.api.sse import stream_debate

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


class DebateRequest(BaseModel):
    question: str
    domain: str = "general"
    max_rounds: int = 3

    @field_validator("question")
    @classmethod
    def question_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be empty")
        return v.strip()


class ChallengeRequest(BaseModel):
    challenge_text: str


@router.get("/debates")
async def get_debates(
    limit: int = 20, offset: int = 0, session: AsyncSession = Depends(get_session)
):
    records = await list_debates(session, limit=limit, offset=offset)
    return records


@router.post("/debates", status_code=201)
async def create_debate(req: DebateRequest, session: AsyncSession = Depends(get_session)):
    debate_id = str(uuid.uuid4())
    initial_state: DebateState = {
        "debate_id": debate_id,
        "question": req.question,
        "domain": req.domain,
        "rounds": [],
        "current_round": 0,
        "max_rounds": req.max_rounds,
        "consensus_reached": False,
        "final_answer": None,
    }
    final_state = await debate_graph.ainvoke(initial_state)
    await save_debate(session, final_state)
    final = final_state.get("final_answer")
    return {
        "debate_id": debate_id,
        "domain": req.domain,
        "rounds_completed": final_state["current_round"],
        "consensus_reached": final_state["consensus_reached"],
        "consensus_confidence": final.confidence if final else None,
    }


@router.get("/debates/{debate_id}/stream")
async def stream_debate_endpoint(
    debate_id: str, question: str, domain: str = "general", max_rounds: int = 3
):
    return StreamingResponse(
        stream_debate(debate_id, question, domain, max_rounds),
        media_type="text/event-stream",
    )


@router.get("/debates/{debate_id}")
async def get_debate(debate_id: str, session: AsyncSession = Depends(get_session)):
    record = await load_debate(session, debate_id)
    if not record:
        raise HTTPException(status_code=404, detail="Debate not found")
    return record


@router.get("/debates/{debate_id}/consensus")
async def get_consensus(debate_id: str, session: AsyncSession = Depends(get_session)):
    record = await load_debate(session, debate_id)
    if not record:
        raise HTTPException(status_code=404, detail="Debate not found")
    return {"answer": record.final_answer, "confidence": record.final_confidence}


@router.post("/debates/{debate_id}/challenge")
async def challenge_debate(
    debate_id: str, req: ChallengeRequest, session: AsyncSession = Depends(get_session)
):
    record = await load_debate(session, debate_id)
    if not record:
        raise HTTPException(status_code=404, detail="Debate not found")

    amended_question = f"{record.question}\n\nHuman challenge: {req.challenge_text}"
    challenge_state: DebateState = {
        "debate_id": debate_id,
        "question": amended_question,
        "domain": record.domain,
        "rounds": [],
        "current_round": 0,
        "max_rounds": 1,
        "consensus_reached": False,
        "final_answer": None,
    }
    final_state = await debate_graph.ainvoke(challenge_state)
    await save_debate(session, final_state)
    return {"debate_id": debate_id, "challenge_processed": True}
