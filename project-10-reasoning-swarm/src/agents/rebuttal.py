from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from src.agents.base import get_llm, format_prior_rounds, format_current_turns
from src.models import AgentTurn, RoundState

SYSTEM = """You are the Proposer making your rebuttal. Critic and Devil's Advocate have attacked your position.
Your role:
- Respond directly to the specific weaknesses they identified
- Concede any valid points -- refusing to concede anything weakens your credibility
- Reinforce the parts of your argument they did not successfully attack
- Update your confidence score based on how well you handled the critique"""


class RebuttalOutput(BaseModel):
    rebuttal: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_claims: list[str]
    citations: list[str] = []


async def rebuttal_node(state: RoundState) -> dict:
    llm = get_llm().with_structured_output(RebuttalOutput)
    prior_context = format_prior_rounds(state.get("prior_rounds", []))
    current_turns = format_current_turns(state.get("turns", []))
    human = (
        f"Question: {state['question']}\n"
        f"Domain: {state['domain']}\n"
        f"Round: {state['round_number']}\n\n"
        f"Prior rounds:\n{prior_context}\n\n"
        f"Current round (Proposer position + attacks):\n{current_turns}\n\n"
        "Deliver your rebuttal."
    )
    result: RebuttalOutput = await llm.ainvoke([SystemMessage(content=SYSTEM), HumanMessage(content=human)])
    turn = AgentTurn(
        agent="rebuttal",
        content=result.rebuttal,
        confidence=result.confidence,
        key_claims=result.key_claims,
        citations=result.citations,
    )
    return {"turns": [turn]}
