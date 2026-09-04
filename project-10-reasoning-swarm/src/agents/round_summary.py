from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from src.agents.base import get_llm, format_current_turns
from src.models import RoundState

SYSTEM = """You are a neutral moderator summarizing a debate round.
Summarize in 2-3 sentences:
- What position did the Proposer take?
- What were the strongest attacks from Critic and Devil's Advocate?
- How did the Proposer's rebuttal hold up?
Do not editorialize -- just summarize objectively."""


class RoundSummaryOutput(BaseModel):
    summary: str


async def round_summary_node(state: RoundState) -> dict:
    llm = get_llm().with_structured_output(RoundSummaryOutput)
    current_turns = format_current_turns(state.get("turns", []))
    human = f"Round {state['round_number']} transcript:\n{current_turns}\n\nSummarize this round."
    result: RoundSummaryOutput = await llm.ainvoke([SystemMessage(content=SYSTEM), HumanMessage(content=human)])
    return {"summary": result.summary}
