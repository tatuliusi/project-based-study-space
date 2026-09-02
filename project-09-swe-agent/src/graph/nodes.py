from __future__ import annotations

import json
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from ..config import settings
from ..github_client import fetch_issue
from ..models import ImplementationPlan, Patch, PlanStep, TestRun
from ..repo_map import build_repo_map, repo_map_to_context
from ..tools import apply_patch, run_tests, set_sandbox
from ..sandbox import Sandbox
from .state import SWEState

_llm = ChatOpenAI(model="gpt-4o", temperature=0)
_llm_structured_plan = _llm.with_structured_output(ImplementationPlan)


def _system(text: str) -> dict[str, str]:
    return {"role": "system", "content": text}


def _human(text: str) -> dict[str, str]:
    return {"role": "user", "content": text}


def analyze_issue(state: SWEState) -> dict[str, Any]:
    issue = fetch_issue(state["issue_url"])
    return {"issue": issue}


def explore_repo(state: SWEState) -> dict[str, Any]:
    repo_path = state.get("repo_path", ".")

    def summarizer(content: str) -> str:
        resp = _llm.invoke([
            _system("Summarize this Python module in one sentence. Be specific about what it does."),
            _human(content),
        ])
        return resp.content

    repo_map = build_repo_map(repo_path, summarizer=summarizer)
    return {"repo_map": repo_map}


def create_plan(state: SWEState) -> dict[str, Any]:
    issue = state["issue"]
    repo_map = state.get("repo_map", {})
    context = repo_map_to_context(repo_map)

    prompt = (
        f"GitHub issue #{issue.number}: {issue.title}\n\n"
        f"{issue.body}\n\n"
        f"Repository structure:\n{context}\n\n"
        "Create an implementation plan to resolve this issue."
    )

    plan: ImplementationPlan = _llm_structured_plan.invoke([
        _system(
            "You are a senior software engineer. Given a GitHub issue and repository structure, "
            "produce a structured implementation plan."
        ),
        _human(prompt),
    ])
    return {"plan": plan}


def implement(state: SWEState) -> dict[str, Any]:
    issue = state["issue"]
    plan = state["plan"]
    repo_path = state.get("repo_path", ".")
    patches: list[Patch] = list(state.get("patches", []))
    iteration = state.get("iteration", 0)

    for step in plan.steps:
        file_context = ""
        from pathlib import Path
        target = Path(repo_path) / step.file_path
        if target.exists():
            file_context = target.read_text(encoding="utf-8", errors="replace")[:4000]

        prompt = (
            f"Issue: {issue.title}\n{issue.body}\n\n"
            f"Step {step.step_number}: {step.description}\n"
            f"File: {step.file_path} (action: {step.action})\n"
            f"Rationale: {step.rationale}\n\n"
            f"Current file content:\n```\n{file_context}\n```\n\n"
            "Produce a unified diff that implements this step. Output ONLY the diff, no explanation."
        )
        resp = _llm.invoke([
            _system("You produce unified diffs. Output only the diff block, no markdown fences."),
            _human(prompt),
        ])
        diff = resp.content.strip()
        if diff:
            result = apply_patch.invoke({"path": str(target), "unified_diff": diff})
            patches.append(
                Patch(
                    iteration=iteration,
                    file_path=step.file_path,
                    unified_diff=diff,
                    description=step.description,
                )
            )

    return {"patches": patches}


def run_tests_node(state: SWEState) -> dict[str, Any]:
    iteration = state.get("iteration", 0)
    test_run = run_tests.invoke({"test_path": "tests/", "iteration": iteration})
    test_results = list(state.get("test_results", []))
    test_results.append(test_run)
    return {"test_results": test_results, "iteration": iteration + 1}


def analyze_failures(state: SWEState) -> dict[str, Any]:
    test_results = state.get("test_results", [])
    if not test_results:
        return {}
    last = test_results[-1]
    patches = state.get("patches", [])
    patch_history = "\n---\n".join(
        f"Iteration {p.iteration}: {p.file_path}\n{p.unified_diff}" for p in patches[-3:]
    )
    resp = _llm.invoke([
        _system(
            "You are a debugging expert. Analyze test failures and identify which recent patch caused them. "
            "Reply in plain text with the root cause and the file that needs fixing."
        ),
        _human(
            f"Test output:\n{last.raw_output[:3000]}\n\n"
            f"Recent patches:\n{patch_history}"
        ),
    ])
    return {"error": resp.content}


def patch_node(state: SWEState) -> dict[str, Any]:
    error_analysis = state.get("error", "")
    patches = list(state.get("patches", []))
    iteration = state.get("iteration", 0)
    repo_path = state.get("repo_path", ".")
    test_results = state.get("test_results", [])
    last_output = test_results[-1].raw_output[:3000] if test_results else ""

    resp = _llm.invoke([
        _system("You produce unified diffs to fix failing tests. Output only the diff block."),
        _human(
            f"Error analysis:\n{error_analysis}\n\n"
            f"Test output:\n{last_output}\n\n"
            "Produce a unified diff to fix the root cause. State the file path on the first comment line."
        ),
    ])
    diff = resp.content.strip()
    if diff:
        file_hint = _extract_file_hint(diff, patches)
        result = apply_patch.invoke({"path": file_hint, "unified_diff": diff})
        patches.append(
            Patch(
                iteration=iteration,
                file_path=file_hint,
                unified_diff=diff,
                description="Iterative fix based on test failures",
            )
        )
    return {"patches": patches}


def _extract_file_hint(diff: str, patches: list[Patch]) -> str:
    for line in diff.splitlines():
        if line.startswith("--- ") or line.startswith("+++ "):
            parts = line.split()
            if len(parts) > 1 and parts[1] != "/dev/null":
                return parts[1].lstrip("ab/")
    if patches:
        return patches[-1].file_path
    return "unknown.py"


def human_approval(state: SWEState) -> dict[str, Any]:
    patches = state.get("patches", [])
    full_diff = "\n\n".join(f"# {p.file_path}\n{p.unified_diff}" for p in patches)
    interrupt({"task_id": state["task_id"], "diff": full_diff})
    return {}


def open_pr(state: SWEState) -> dict[str, Any]:
    from ..github_client import (
        commit_files,
        create_branch,
        get_default_branch_sha,
        open_pull_request,
    )
    from pathlib import Path

    issue = state["issue"]
    plan = state["plan"]
    repo_path = state.get("repo_path", ".")

    branch_name = f"agent/fix-issue-{issue.number}"
    base_sha = get_default_branch_sha(issue.repo_full_name)
    create_branch(issue.repo_full_name, branch_name, base_sha)

    affected = {p.file_path for p in state.get("patches", [])}
    files: dict[str, str] = {}
    for rel in affected:
        target = Path(repo_path) / rel
        if target.exists():
            files[rel] = target.read_text(encoding="utf-8")

    commit_files(
        issue.repo_full_name,
        branch_name,
        files,
        f"fix: implement changes for issue #{issue.number}",
    )

    plan_md = _plan_to_markdown(plan, issue)
    pr_url = open_pull_request(issue.repo_full_name, branch_name, issue, plan_md)
    return {"pr_url": pr_url}


def _plan_to_markdown(plan: ImplementationPlan, issue: "Issue") -> str:
    lines = [
        f"## Fix for #{issue.number}: {issue.title}",
        "",
        f"**Complexity:** {plan.estimated_complexity}",
        f"**Test strategy:** {plan.test_strategy}",
        "",
        "### Steps",
    ]
    for step in plan.steps:
        lines.append(f"{step.step_number}. **{step.file_path}** ({step.action}) -- {step.description}")
    lines.append("")
    lines.append("*Generated by autonomous SWE agent.*")
    return "\n".join(lines)


def should_iterate(state: SWEState) -> str:
    test_results = state.get("test_results", [])
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", settings.max_iterations)

    if not test_results:
        return "iterate"
    last = test_results[-1]
    if last.exit_code == 0 and last.failed == 0:
        return "approve"
    if iteration >= max_iterations:
        return "approve"
    return "iterate"
