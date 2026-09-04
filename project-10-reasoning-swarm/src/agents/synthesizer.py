from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from src.agents.base import get_llm, format_prior_rounds
from src.models import ConsensusAnswer, DebateState

SYSTEM = """You are the Synthesizer. You read the full debate transcript and produce the final consensus answer.
Rules:
- Weight each position by the agent's stated confidence
- If Critic and Devil's Advocate both successfully attacked a claim, flag it in uncertainty_flags
- Include minority positions in dissenting_views if their confidence was > 0.3
- The consensus answer should be the strongest defensible position after all attacks
- Your confidence score = weighted average of surviving claims"""


class SynthesizerOutput(BaseModel):
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    dissenting_views: list[str] = []
    key_reasoning: list[str] = []
    uncertainty_flags: list[str] = []


async def synthesizer_node(state: DebateState) -> dict:
    llm = get_llm().with_structured_output(SynthesizerOutput)
    transcript = format_prior_rounds(state["rounds"])
    human = f"Question: {state['question']}\n\nFull debate transcript:\n{transcript}\n\nSynthesize the final answer."
    result: SynthesizerOutput = await llm.ainvoke([SystemMessage(content=SYSTEM), HumanMessage(content=human)])
    consensus = ConsensusAnswer(
        answer=result.answer,
        confidence=result.confidence,
        dissenting_views=result.dissenting_views,
        key_reasoning=result.key_reasoning,
        uncertainty_flags=result.uncertainty_flags,
    )
    return {"final_answer": consensus}
