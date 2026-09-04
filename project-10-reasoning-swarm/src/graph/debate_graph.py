import uuid
from langgraph.graph import StateGraph, START, END
from src.models import DebateState, Round, RoundState
from src.consensus import compute_agreement_score
from src.agents.synthesizer import synthesizer_node
from src.config import settings
from src.graph.round_graph import round_graph


async def initialize_debate(state: DebateState) -> dict:
    return {
        "debate_id": state.get("debate_id") or str(uuid.uuid4()),
        "current_round": 0,
        "consensus_reached": False,
        "rounds": [],
        "final_answer": None,
    }


async def run_round(state: DebateState) -> dict:
    round_number = state["current_round"] + 1
    round_input: RoundState = {
        "debate_id": state["debate_id"],
        "question": state["question"],
        "domain": state["domain"],
        "round_number": round_number,
        "prior_rounds": list(state["rounds"]),
        "turns": [],
        "summary": "",
        "agreement_score": 0.0,
    }

    round_result = await round_graph.ainvoke(round_input)
    rnd = Round(
        round_number=round_number,
        turns=round_result["turns"],
        summary=round_result.get("summary", ""),
        agreement_score=0.0,
    )
    rnd.agreement_score = await compute_agreement_score(rnd)

    consensus = rnd.agreement_score >= settings.consensus_threshold
    return {
        "rounds": [rnd],
        "current_round": round_number,
        "consensus_reached": consensus,
    }


def should_continue(state: DebateState) -> str:
    if state["consensus_reached"] or state["current_round"] >= state["max_rounds"]:
        return "synthesize"
    return "run_round"


def build_debate_graph():
    graph = StateGraph(DebateState)
    graph.add_node("initialize", initialize_debate)
    graph.add_node("run_round", run_round)
    graph.add_node("synthesize", synthesizer_node)

    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "run_round")
    graph.add_conditional_edges(
        "run_round",
        should_continue,
        {"run_round": "run_round", "synthesize": "synthesize"},
    )
    graph.add_edge("synthesize", END)

    return graph.compile()


debate_graph = build_debate_graph()
