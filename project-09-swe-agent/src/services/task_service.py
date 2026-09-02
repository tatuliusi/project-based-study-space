from __future__ import annotations

import asyncio
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from ..config import settings
from ..graph import SWEState, swe_graph
from ..sandbox import Sandbox
from ..tools.runner import set_sandbox
from .postgres_service import get_task, insert_task, update_task


async def submit_task(issue_url: str) -> str:
    task_id = str(uuid.uuid4())
    await insert_task(task_id, issue_url)
    asyncio.create_task(_run_task(task_id, issue_url))
    return task_id


async def approve_task(task_id: str) -> dict[str, Any]:
    task = await get_task(task_id)
    if not task:
        return {"error": "task not found"}
    if task["status"] != "awaiting_approval":
        return {"error": f"task is {task['status']}, not awaiting_approval"}

    await update_task(task_id, status="approved")
    asyncio.create_task(_resume_task(task_id))
    return {"status": "approved"}


async def _run_task(task_id: str, issue_url: str) -> None:
    await update_task(task_id, status="running", current_step="analyze_issue")

    with tempfile.TemporaryDirectory() as tmpdir:
        initial_state: SWEState = {
            "task_id": task_id,
            "issue_url": issue_url,
            "repo_path": tmpdir,
            "patches": [],
            "test_results": [],
            "iteration": 0,
            "max_iterations": settings.max_iterations,
            "approved": False,
            "pr_url": None,
            "error": None,
        }

        with Sandbox(tmpdir) as sandbox:
            set_sandbox(sandbox)
            try:
                async for event in swe_graph.astream(initial_state):
                    node_name = next(iter(event))
                    node_output = event[node_name]

                    if node_name == "__interrupt__":
                        await update_task(
                            task_id,
                            status="awaiting_approval",
                            current_step="human_approval",
                            state_json=_serialize_interrupt(node_output),
                        )
                        return

                    await update_task(task_id, current_step=node_name)
                    if "pr_url" in node_output and node_output["pr_url"]:
                        await update_task(task_id, pr_url=node_output["pr_url"], status="done")

            except Exception as exc:
                await update_task(task_id, status="failed", error=str(exc))


async def _resume_task(task_id: str) -> None:
    pass


def _serialize_interrupt(interrupt_data: Any) -> dict[str, Any]:
    if isinstance(interrupt_data, dict):
        return interrupt_data
    if hasattr(interrupt_data, "__iter__"):
        for item in interrupt_data:
            if isinstance(item, dict):
                return item
    return {}
