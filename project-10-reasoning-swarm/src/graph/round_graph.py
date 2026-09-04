from langgraph.graph import StateGraph, START, END
from src.models import RoundState
from src.agents.proposer import proposer_node
from src.agents.critic import critic_node
from src.agents.devil_advocate import devil_advocate_node
from src.agents.rebuttal import rebuttal_node
from src.agents.round_summary import round_summary_node


def build_round_graph():
    graph = StateGraph(RoundState)
    graph.add_node("proposer", proposer_node)
    graph.add_node("critic", critic_node)
    graph.add_node("devil_advocate", devil_advocate_node)
    graph.add_node("rebuttal", rebuttal_node)
    graph.add_node("round_summary", round_summary_node)

    graph.add_edge(START, "proposer")
    graph.add_edge("proposer", "critic")
    graph.add_edge("critic", "devil_advocate")
    graph.add_edge("devil_advocate", "rebuttal")
    graph.add_edge("rebuttal", "round_summary")
    graph.add_edge("round_summary", END)

    return graph.compile()


round_graph = build_round_graph()
