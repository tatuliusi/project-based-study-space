from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from src.agents.base import get_llm, format_prior_rounds, format_current_turns
from src.models import AgentTurn, RoundState

SYSTEM = """You are the Critic in a structured debate. Your role:
- Analyze the Proposer's argument for logical gaps, unsupported claims, and alternative interpretations
- Do NOT propose your own alternative answer -- only attack weaknesses
- Be specific: identify exact claims that are unsupported or overstated
- Assign confidence to your critique (how certain are you that the Proposer is wrong?)
- A stronger critique earns a higher confidence score"""


class CriticOutput(BaseModel):
    critique: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_claims: list[str]
    citations: list[str] = []


async def critic_node(state: RoundState) -> dict:
    llm = get_llm().with_structured_output(CriticOutput)
    prior_context = format_prior_rounds(state.get("prior_rounds", []))
    current_turns = format_current_turns(state.get("turns", []))
    human = (
        f"Question: {state['question']}\n"
        f"Domain: {state['domain']}\n"
        f"Round: {state['round_number']}\n\n"
        f"Prior rounds:\n{prior_context}\n\n"
        f"Current round so far:\n{current_turns}\n\n"
        "Critique the Proposer's position."
    )
    result: CriticOutput = await llm.ainvoke([SystemMessage(content=SYSTEM), HumanMessage(content=human)])
    turn = AgentTurn(
        agent="critic",
        content=result.critique,
        confidence=result.confidence,
        key_claims=result.key_claims,
        citations=result.citations,
    )
    return {"turns": [turn]}
