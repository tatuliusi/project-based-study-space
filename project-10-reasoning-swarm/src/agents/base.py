from langchain_openai import ChatOpenAI
from src.config import settings
from src.models import Round, AgentTurn


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(model=settings.reasoning_model, api_key=settings.openai_api_key)


def format_prior_rounds(prior_rounds: list[Round]) -> str:
    if not prior_rounds:
        return "No prior rounds."
    lines = []
    for rnd in prior_rounds:
        lines.append(f"=== Round {rnd.round_number} ===")
        for turn in rnd.turns:
            lines.append(f"[{turn.agent.upper()}] (confidence={turn.confidence:.2f}): {turn.content}")
    return "\n".join(lines)


def format_current_turns(turns: list[AgentTurn]) -> str:
    if not turns:
        return "No turns yet."
    lines = []
    for turn in turns:
        lines.append(f"[{turn.agent.upper()}] (confidence={turn.confidence:.2f}): {turn.content}")
    return "\n".join(lines)
