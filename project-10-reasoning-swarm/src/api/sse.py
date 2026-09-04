import json
from src.graph.debate_graph import debate_graph
from src.models import DebateState


async def stream_debate(debate_id: str, question: str, domain: str, max_rounds: int):
    initial_state: DebateState = {
        "debate_id": debate_id,
        "question": question,
        "domain": domain,
        "rounds": [],
        "current_round": 0,
        "max_rounds": max_rounds,
        "consensus_reached": False,
        "final_answer": None,
    }

    current_agent: str | None = None
    current_round = 0

    async for event in debate_graph.astream_events(initial_state, version="v1"):
        kind = event.get("event")

        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                payload = json.dumps({"agent": current_agent, "token": chunk.content, "round": current_round})
                yield f"data: {payload}\n\n"

        elif kind == "on_chain_start":
            name = event.get("name", "")
            if name in ("proposer", "critic", "devil_advocate", "rebuttal", "synthesizer"):
                current_agent = name

        elif kind == "on_chain_end":
            name = event.get("name", "")
            if name == "run_round":
                output = event.get("data", {}).get("output", {})
                current_round = output.get("current_round", current_round)
                rounds_out = output.get("rounds", [])
                agreement = rounds_out[-1].agreement_score if rounds_out else 0.0
                payload = json.dumps({"event": "round_complete", "round": current_round, "agreement_score": agreement})
                yield f"data: {payload}\n\n"

            elif name == "synthesize":
                output = event.get("data", {}).get("output", {})
                final = output.get("final_answer")
                confidence = final.confidence if final and hasattr(final, "confidence") else 0.0
                payload = json.dumps({"event": "debate_complete", "consensus_confidence": confidence})
                yield f"data: {payload}\n\n"
