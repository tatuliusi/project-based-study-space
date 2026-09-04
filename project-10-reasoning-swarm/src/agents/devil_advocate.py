from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from src.agents.base import get_llm, format_prior_rounds, format_current_turns
from src.models import AgentTurn, RoundState

SYSTEM = """You are the Devil's Advocate in a structured debate. Your role:
- Argue for the least popular but most logically consistent counterposition
- Your job is to prevent groupthink, even if the Proposer seems correct
- You MUST disagree with the Proposer -- agreeing is a failure of your role
- Find the strongest possible argument against the current consensus
- The more uncomfortable your argument makes others, the better you are doing your job"""


class DevilAdvocateOutput(BaseModel):
    counterposition: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_claims: list[str]
    citations: list[str] = []


async def devil_advocate_node(state: RoundState) -> dict:
    llm = get_llm().with_structured_output(DevilAdvocateOutput)
    prior_context = format_prior_rounds(state.get("prior_rounds", []))
    current_turns = format_current_turns(state.get("turns", []))
    human = (
        f"Question: {state['question']}\n"
        f"Domain: {state['domain']}\n"
        f"Round: {state['round_number']}\n\n"
        f"Prior rounds:\n{prior_context}\n\n"
        f"Current round so far:\n{current_turns}\n\n"
        "Argue the strongest counterposition."
    )
    result: DevilAdvocateOutput = await llm.ainvoke([SystemMessage(content=SYSTEM), HumanMessage(content=human)])
    turn = AgentTurn(
        agent="devil_advocate",
        content=result.counterposition,
        confidence=result.confidence,
        key_claims=result.key_claims,
        citations=result.citations,
    )
    return {"turns": [turn]}
