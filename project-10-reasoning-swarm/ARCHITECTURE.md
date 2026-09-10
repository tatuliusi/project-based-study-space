# Architecture — Multi-Agent Collaborative Reasoning Swarm

## Why this project is the capstone of the second half

Projects 6–9 each master one hard problem: scheduling, memory, evaluation, tool use. This project combines multi-agent coordination with a principled reasoning protocol. The result demonstrates the most sophisticated LangGraph pattern in the portfolio: composed subgraphs, agent-to-agent communication, and emergent reasoning through structured debate.

## Implementation entry point

The outer debate graph and composed round workflow are organized under `src/`.

## State

```python
class DebateState(TypedDict):
    debate_id: str
    question: str
    domain: str                             # detected topic domain for role tuning
    rounds: Annotated[list[Round], operator.add]
    current_round: int
    max_rounds: int                         # default: 3
    consensus_reached: bool
    final_answer: ConsensusAnswer | None

class Round(BaseModel):
    round_number: int
    turns: list[AgentTurn]
    summary: str
    agreement_score: float                  # 0.0–1.0: how aligned are positions?

class AgentTurn(BaseModel):
    agent: Literal["proposer", "critic", "devil_advocate", "rebuttal", "synthesizer"]
    content: str
    confidence: float                       # agent's self-reported confidence in its position
    key_claims: list[str]                   # structured extraction for consensus computation
    citations: list[str]                    # reasoning chains / evidence cited

class ConsensusAnswer(BaseModel):
    answer: str
    confidence: float
    dissenting_views: list[str]             # minority positions preserved
    key_reasoning: list[str]
    uncertainty_flags: list[str]            # areas where agents still disagreed
```

## The four agents

### Proposer
Constructs the strongest affirmative case for the most defensible answer. Trained to:
- State a clear position upfront
- Cite reasoning chains
- Assign a confidence score based on strength of evidence

### Critic
Analyzes the Proposer's argument for logical gaps, unsupported claims, and alternative interpretations. Does not propose an alternative — only attacks weaknesses. This separation forces Proposer to be more rigorous in rebuttal.

### Devil's Advocate
Argues for the least popular but most logically consistent counterposition. The role exists to prevent groupthink — even when the Proposer is likely correct, the Devil's Advocate forces explicit engagement with the strongest opposing view.

### Synthesizer
Reads all prior turns and produces the consensus. Uses confidence-weighted averaging:
- Weight each agent's position by their stated confidence
- Flag claims where Critic and Devil's Advocate both attacked (high uncertainty)
- Produce `dissenting_views` for minority positions that scored > 0.3 confidence

## Per-round subgraph

```python
round_graph = StateGraph(RoundState)
round_graph.add_node("proposer", proposer_node)
round_graph.add_node("critic", critic_node)
round_graph.add_node("devil_advocate", devil_advocate_node)
round_graph.add_node("rebuttal", rebuttal_node)          # Proposer responds to attacks
round_graph.add_node("round_summary", round_summary_node)

round_graph.add_edge("proposer", "critic")
round_graph.add_edge("critic", "devil_advocate")
round_graph.add_edge("devil_advocate", "rebuttal")
round_graph.add_edge("rebuttal", "round_summary")
```

The per-round graph is compiled independently and called as `round_graph.invoke(round_state)` from the outer graph's `run_round` node. This is LangGraph subgraph composition.

## Consensus detection

After each round, an `agreement_score` is computed:
1. Extract key claims from each agent turn (LLM structured call)
2. Embed all claims (text-embedding-3-small)
3. Compute pairwise cosine similarity between Proposer and Critic claims
4. Mean similarity = agreement_score

If `agreement_score > 0.75`, consensus is reached and the loop exits early. Otherwise, the next round begins with all agents having read the prior round transcript.

## Streaming

The outer graph runs with `.astream_events()`. Each `on_chat_model_stream` event is tagged with the agent name and forwarded over SSE:

```
data: {"agent": "critic", "token": "The", "round": 1}
data: {"agent": "critic", "token": " claim", "round": 1}
...
data: {"event": "round_complete", "round": 1, "agreement_score": 0.62}
data: {"event": "debate_complete", "consensus_confidence": 0.84}
```

Clients see the debate unfold token by token, agent by agent.

## Human challenge

`POST /debates/{id}/challenge` with a `challenge_text` body injects a new round:
- The challenge text is prepended to the question as a constraint
- All agents must engage with the challenge in their next turn
- Max rounds is extended by 1
- This models the pattern of a human stakeholder pushing back on an AI consensus

## Why this beats a single-agent answer

Empirically, debate produces better answers than a single agent on complex questions because:
1. The Critic is optimized to find flaws — it will catch things the Proposer's self-critique misses
2. The Devil's Advocate prevents the first reasonable answer from being accepted uncritically
3. The Synthesizer's confidence weighting means strongly-held positions from multiple agents dominate

The portfolio demonstrates this empirically: the system includes a benchmark script that compares swarm vs. single-agent answers on a test set.

## What an interviewer will ask about this

1. "How does agent-to-agent communication work in LangGraph?" — Each node reads the full `state["rounds"]` history before writing its turn. There is no direct message passing — the shared state is the communication channel.
2. "How do you prevent the agents from all agreeing trivially?" — Role prompts are adversarial by design: Critic is told to find weaknesses regardless of how good the proposal is; Devil's Advocate is penalized (in prompt) for agreeing with the Proposer.
3. "How is the consensus confidence calculated?" — Confidence-weighted average of key-claim embedding similarity across agents, adjusted by `uncertainty_flags` for areas of persistent disagreement.
4. "Could this be used for red-teaming?" — Yes. Swap the Devil's Advocate persona for a red-teamer persona: find ways this answer could be misused, cause harm, or fail in edge cases. The same graph structure works for safety evaluation.
