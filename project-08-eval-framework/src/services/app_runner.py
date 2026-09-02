from __future__ import annotations

from langchain_openai import ChatOpenAI

from src.models import AppConfig


async def run_app(config: AppConfig, user_input: str, context: list[str] | None) -> str:
    """Call the app under test and return its text output."""
    llm = ChatOpenAI(model=config.model, temperature=0.0)

    system_parts = [f"You are {config.app_id} running prompt version {config.prompt_version}."]
    if context:
        system_parts.append("Use the following context to answer the question:")
        system_parts.append("\n".join(f"- {c}" for c in context))

    messages = [
        {"role": "system", "content": "\n".join(system_parts)},
        {"role": "user", "content": user_input},
    ]

    response = await llm.ainvoke(messages)
    return str(response.content)
