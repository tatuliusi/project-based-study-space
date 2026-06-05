import json
import os
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt
from pydantic import BaseModel

from src.graph.state import SupportState, UserContext
from src.tools.billing_api import billing_tools
from src.tools.docs_search import technical_tools


def _llm(temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=temperature)


async def _run_tool_loop(llm_with_tools, system: SystemMessage, messages: list, tools: list) -> AIMessage:
    tool_map = {t.name: t for t in tools}
    history = [system] + list(messages)
    response = await llm_with_tools.ainvoke(history)
    while response.tool_calls:
        history.append(response)
        for call in response.tool_calls:
            result = await tool_map[call["name"]].ainvoke(call["args"])
            history.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
        response = await llm_with_tools.ainvoke(history)
    return response


# --- load_user_context -------------------------------------------------------

async def load_user_context_node(state: SupportState) -> dict:
    from src.db import db_pool

    user_id = state["user_id"]
    ctx = None

    if db_pool:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM user_context WHERE user_id = $1", user_id)
        if row:
            ctx = UserContext(
                user_id=user_id,
                tier=row["tier"],
                issue_history=json.loads(row["issue_history"]),
                tone_notes=row["tone_notes"],
            )

    return {
        "user_context": ctx or UserContext(user_id=user_id),
        "category": None,
        "escalated": False,
        "agent_notes": "",
    }


# --- triage ------------------------------------------------------------------

class TriageOutput(BaseModel):
    category: Literal["billing", "technical", "complaint", "unknown"]
    should_escalate: bool = False
    reasoning: str = ""


_TRIAGE_SYSTEM = """You are a customer support triage agent.

Classify the customer's latest message into one of these categories:
- billing: questions about invoices, payments, subscriptions, refunds
- technical: questions about product features, bugs, configuration, integrations
- complaint: expressions of frustration, dissatisfaction, or requests for compensation
- unknown: cannot determine

Set should_escalate=true if the customer is extremely distressed, using abusive language,
or has explicitly demanded to speak with a human."""


async def triage_node(state: SupportState) -> dict:
    ctx = state.get("user_context")
    context_hint = ""
    if ctx and ctx.issue_history:
        recent = ctx.issue_history[-2:]
        context_hint = f"\n\nPrior session notes: {'; '.join(recent)}"

    result = await _llm().with_structured_output(TriageOutput).ainvoke(
        [
            SystemMessage(content=_TRIAGE_SYSTEM + context_hint),
            *state["messages"],
        ]
    )

    category = "unknown" if result.category == "unknown" else result.category
    escalated = result.should_escalate
    notes = result.reasoning if escalated else ""

    return {"category": category, "escalated": escalated, "agent_notes": notes}


# --- billing_agent -----------------------------------------------------------

_BILLING_SYSTEM = """You are a billing support specialist. Help with invoices, payments, subscriptions, and refunds.
Use the available tools to look up account and invoice details before answering.
Be concise, accurate, and professional."""


async def billing_node(state: SupportState) -> dict:
    ctx = state.get("user_context")
    system = _BILLING_SYSTEM
    if ctx:
        system += f"\n\nUser tier: {ctx.tier}. User ID: {state['user_id']}."

    llm = _llm().bind_tools(billing_tools)
    response = await _run_tool_loop(llm, SystemMessage(content=system), state["messages"], billing_tools)
    return {"messages": [response]}


# --- technical_agent ---------------------------------------------------------

_TECHNICAL_SYSTEM = """You are a technical support specialist. Help with product features, bugs, configuration, and integrations.
Search the documentation before answering. If no relevant docs are found, give your best guidance and offer to escalate."""


async def technical_node(state: SupportState) -> dict:
    llm = _llm().bind_tools(technical_tools)
    response = await _run_tool_loop(llm, SystemMessage(content=_TECHNICAL_SYSTEM), state["messages"], technical_tools)
    return {"messages": [response]}


# --- complaint_agent ---------------------------------------------------------

class ComplaintOutput(BaseModel):
    response: str
    escalate: bool
    compensation_offered: float = 0.0
    escalation_reason: str = ""


_COMPLAINT_SYSTEM = """You are a customer retention specialist. Handle complaints with empathy and professionalism.

Rules:
- Acknowledge the customer's frustration genuinely before offering solutions.
- You may offer compensation (credit, discount) up to $50 without escalating.
- If the issue requires compensation above $50 or the customer is still unsatisfied after your best effort,
  set escalate=true and explain why in escalation_reason.
- Write your customer-facing response in the `response` field."""


async def complaint_node(state: SupportState) -> dict:
    ctx = state.get("user_context")
    system = _COMPLAINT_SYSTEM
    if ctx and ctx.tone_notes:
        system += f"\n\nNote from prior sessions: {ctx.tone_notes}"

    result = await _llm(temperature=0.3).with_structured_output(ComplaintOutput).ainvoke(
        [SystemMessage(content=system), *state["messages"]]
    )

    updates: dict = {"messages": [AIMessage(content=result.response)]}
    if result.escalate:
        updates["escalated"] = True
        updates["agent_notes"] = (
            f"Escalation reason: {result.escalation_reason}. "
            f"Compensation offered: ${result.compensation_offered:.2f}."
        )
    return updates


# --- human_handoff -----------------------------------------------------------

async def human_handoff_node(state: SupportState) -> dict:
    human_response: str = interrupt(
        {
            "type": "escalation_needed",
            "conversation_id": state["conversation_id"],
            "user_id": state["user_id"],
            "agent_notes": state["agent_notes"],
            "last_message": state["messages"][-1].content if state["messages"] else "",
        }
    )
    return {"messages": [AIMessage(content=human_response)]}


# --- summarize_session -------------------------------------------------------

_SUMMARY_SYSTEM = """Summarize this support session in 1-2 sentences for future agent context.
Include: what the issue was, how it was resolved, and any notable tone or account details.
Be brief and factual."""


async def summarize_session_node(state: SupportState) -> dict:
    from src.db import db_pool

    snippet = "\n".join(
        f"{m.type}: {m.content[:300]}" for m in state["messages"][-6:]
    )
    summary_msg = await _llm().ainvoke(
        [
            SystemMessage(content=_SUMMARY_SYSTEM),
            SystemMessage(content=f"Category: {state['category']}\n\nConversation:\n{snippet}"),
        ]
    )
    summary = summary_msg.content

    ctx = state.get("user_context") or UserContext(user_id=state["user_id"])
    new_history = (ctx.issue_history + [summary])[-5:]

    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_context (user_id, tier, issue_history, tone_notes, updated_at)
                VALUES ($1, $2, $3::jsonb, $4, NOW())
                ON CONFLICT (user_id) DO UPDATE
                SET issue_history = $3::jsonb,
                    tone_notes    = $4,
                    updated_at    = NOW()
                """,
                state["user_id"],
                ctx.tier,
                json.dumps(new_history),
                ctx.tone_notes,
            )

    return {}
