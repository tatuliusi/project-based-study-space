# Architecture — Production Customer Support System

## Why this is the capstone

Projects 1–4 demonstrate patterns. This one combines them all into something deployable:
- Multi-agent routing (Projects 2, 3)
- Persistent state across sessions (new — Postgres checkpointer)
- Streaming output (new — SSE over FastAPI)
- Human escalation (Project 4 HITL, extended)
- Production deployment concerns

## Implementation entry point

The support workflow and escalation routing are organized under `src/graph/`.

## State

```python
class SupportState(TypedDict):
    conversation_id: str
    user_id: str
    messages: Annotated[list[Message], add_messages]  # LangGraph message reducer
    category: Literal["billing", "technical", "complaint", "unknown"] | None
    escalated: bool
    agent_notes: str                # Internal notes passed between agents
    user_context: UserContext | None  # Loaded from memory at session start
```

## Agents

### Triage Agent
Classifies the incoming message into a category. Uses few-shot examples. If confidence is low or the user is clearly distressed, routes directly to escalation.

### Billing Agent
Specialist in subscription, payment, refund, and invoice questions. Has access to a mock billing API tool.

### Technical Agent
Specialist in product features, bugs, configuration, and integrations. Has access to a documentation search tool (RAG over product docs — reuses Project 1).

### Complaint Agent
Specialist in de-escalation, empathy, and retention. Tuned prompt for tone. Authorized to offer compensation up to a threshold; above that, escalates.

### Human Handoff
Pauses the graph, persists current state, sends a notification payload (webhook, Slack, email). The graph resumes when a human agent submits their response via the `/escalate` endpoint.

## Graph

```
START
  │
  ▼
load_user_context  (fetch prior session summary from Postgres)
  │
  ▼
triage
  │
  ├── "billing"   ──► billing_agent   ──► respond ──► END
  ├── "technical" ──► technical_agent ──► respond ──► END
  ├── "complaint" ──► complaint_agent ──┐
  │                                    ├── [within threshold] ──► respond ──► END
  │                                    └── [above threshold]  ──► human_handoff
  └── "escalate"  ──────────────────────────────────────────────► human_handoff
                                                                       │
                                                                [graph paused]
                                                                       │
                                                               [human responds]
                                                                       │
                                                                       ▼
                                                                    respond ──► END
```

## Persistence: Postgres checkpointer

LangGraph's `PostgresSaver` writes the full graph state after every node execution. This means:
- Conversations survive server restarts
- A conversation can be picked up on a different server instance
- Full audit trail of every state transition

Thread ID = `conversation_id`. Each user message creates a new checkpoint on the same thread.

## Streaming

The FastAPI endpoint runs the graph with `.astream_events()` and forwards `on_chat_model_stream` events to the client via Server-Sent Events. The client receives tokens as they are generated — not the full response after it completes.

## Memory between sessions

After each conversation ends, a `summarize_session` node runs and writes a brief `UserContext` (issue history, tone, account tier) back to Postgres keyed by `user_id`. The next session loads this context before triage, so the agent already knows the user's history.

## What an interviewer will ask about this

1. "How do you handle a server restart mid-conversation?" — Postgres checkpointer, resume by thread ID.
2. "How does streaming work?" — `astream_events`, filter `on_chat_model_stream`, SSE.
3. "How does the human handoff work?" — `interrupt()` in the graph, external trigger resumes via `graph.ainvoke(None, config)`.
4. "How do you scale this?" — Stateless FastAPI workers + shared Postgres. LangGraph state is not in memory.

Know these answers before the interview.
