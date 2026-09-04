from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from src.agents.base import get_llm, format_prior_rounds
from src.models import AgentTurn, RoundState

SYSTEM = """You are the Proposer in a structured debate. Your role:
- State the strongest defensible answer to the question
- Be specific and commit to a clear position
- List your key claims as discrete, verifiable statements
- Self-assign a confidence score (0.0=pure speculation, 1.0=certain)
- Do NOT hedge excessively -- a weak hedge is a weak proposal
If prior rounds exist, acknowledge critiques from the last round and refine your position."""


class ProposerOutput(BaseModel):
    position: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_claims: list[str]
    citations: list[str] = []


async def proposer_node(state: RoundState) -> dict:
    llm = get_llm().with_structured_output(ProposerOutput)
    prior_context = format_prior_rounds(state.get("prior_rounds", []))
    human = (
        f"Question: {state['question']}\n"
        f"Domain: {state['domain']}\n"
        f"Round: {state['round_number']}\n\n"
        f"Prior debate transcript:\n{prior_context}\n\n"
        "State your position."
    )
    result: ProposerOutput = await llm.ainvoke([SystemMessage(content=SYSTEM), HumanMessage(content=human)])
    turn = AgentTurn(
        agent="proposer",
        content=result.position,
        confidence=result.confidence,
        key_claims=result.key_claims,
        citations=result.citations,
    )
    return {"turns": [turn]}
