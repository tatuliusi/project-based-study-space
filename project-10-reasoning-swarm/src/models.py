import operator
from typing import Annotated, Literal
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class AgentTurn(BaseModel):
    agent: Literal["proposer", "critic", "devil_advocate", "rebuttal", "synthesizer"]
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_claims: list[str] = []
    citations: list[str] = []


class Round(BaseModel):
    round_number: int
    turns: list[AgentTurn] = []
    summary: str = ""
    agreement_score: float = 0.0


class ConsensusAnswer(BaseModel):
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    dissenting_views: list[str] = []
    key_reasoning: list[str] = []
    uncertainty_flags: list[str] = []


class DebateState(TypedDict):
    debate_id: str
    question: str
    domain: str
    rounds: Annotated[list[Round], operator.add]
    current_round: int
    max_rounds: int
    consensus_reached: bool
    final_answer: ConsensusAnswer | None


class RoundState(TypedDict):
    debate_id: str
    question: str
    domain: str
    round_number: int
    prior_rounds: list[Round]
    turns: Annotated[list[AgentTurn], operator.add]
    summary: str
    agreement_score: float
