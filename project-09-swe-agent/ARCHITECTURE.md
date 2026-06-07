# Architecture — Autonomous SWE Agent

## Why this project exists in the progression

This is the most tool-intensive project in the portfolio. Everything before this used tools for data retrieval (search, DB queries). This agent uses tools to *act* on external systems — read and write code, execute programs, interact with GitHub. It also has the longest planning horizon of any project here.

## State

```python
class SWEState(TypedDict):
    task_id: str
    issue_url: str
    issue: Issue                            # parsed from GitHub
    repo_map: dict[str, FileInfo]           # path → size, language, summary
    plan: ImplementationPlan | None
    patches: list[Patch]                    # accumulated across iterations
    test_results: list[TestRun]             # history of test runs
    iteration: int
    max_iterations: int                     # default: 5
    approved: bool
    pr_url: str | None

class ImplementationPlan(BaseModel):
    steps: list[PlanStep]
    affected_files: list[str]
    test_strategy: str
    estimated_complexity: Literal["trivial", "small", "medium", "large"]

class PlanStep(BaseModel):
    step_number: int
    description: str
    file_path: str
    action: Literal["create", "modify", "delete"]
    rationale: str

class TestRun(BaseModel):
    iteration: int
    exit_code: int
    passed: int
    failed: int
    errors: list[str]
    duration_ms: int
```

## Tool set

The agent has access to these tools:

```python
@tool
def read_file(path: str) -> str: ...

@tool
def list_directory(path: str) -> list[str]: ...

@tool
def search_code(pattern: str, file_glob: str = "**/*.py") -> list[SearchResult]: ...

@tool
def apply_patch(path: str, unified_diff: str) -> PatchResult: ...

@tool
def run_tests(test_path: str = "tests/") -> TestRun: ...

@tool
def run_command(cmd: str) -> CommandResult: ...  # whitelist-filtered
```

All `run_tests` and `run_command` calls execute inside a Docker container, not on the host.

## Docker sandboxing

```python
class Sandbox:
    def __init__(self, repo_path: str):
        self.container = docker_client.containers.run(
            image="python:3.11-slim",
            command="sleep infinity",
            volumes={repo_path: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=50000,     # 50% of one core
            network_mode="none", # no outbound network
            detach=True,
        )

    def exec(self, cmd: str, timeout: int = 60) -> tuple[int, str]:
        result = self.container.exec_run(cmd, demux=True)
        return result.exit_code, result.output
```

Key constraints: no network, memory cap, CPU cap, 60-second timeout per command. The volume mount means file system changes from `apply_patch` are visible inside the sandbox immediately.

## explore_repo node

Rather than reading every file, the agent builds a lightweight repo map:
1. `list_directory` recursively (depth limit: 3)
2. For Python files: extract top-level class and function names with ast.parse
3. For files > 5KB: summarize with a short LLM call ("what does this module do?")
4. Focus on files mentioned in the issue or in the same module path

The result is a `repo_map` dict that fits in ~2K tokens — efficient context for the planner.

## Implementation loop

```python
while state["iteration"] < state["max_iterations"]:
    test_run = run_tests()

    if test_run.exit_code == 0 and test_run.failed == 0:
        break  # tests pass, proceed to approval

    failures = analyze_failures(test_run)  # LLM: which patch caused this?
    patch = generate_patch(failures)       # LLM: targeted fix
    apply_patch(patch)
    state["iteration"] += 1
```

The `analyze_failures` call is key: it looks at the test output, the patch history, and the test source code to pinpoint which recent change broke which test. This avoids regressing previously fixed tests.

## Human approval gate

After tests pass, the graph hits `interrupt()`. The agent posts the final diff to the task record in Postgres. The human reviews `GET /tasks/{id}/diff` and calls `POST /tasks/{id}/approve` to resume.

This prevents the agent from blindly opening PRs on real repos without review.

## PR creation

```python
repo = github.get_repo(issue.repo_full_name)
branch = repo.create_git_ref(f"refs/heads/agent/fix-issue-{issue.number}", sha=base_sha)
repo.create_file(...)  # or use PyGithub commit API
pr = repo.create_pull(
    title=f"fix: {issue.title}",
    body=plan_as_markdown,
    head=f"agent/fix-issue-{issue.number}",
    base="main",
)
```

The PR body is the formatted implementation plan — reviewers immediately see what the agent intended to do and why.

## What an interviewer will ask about this

1. "How do you prevent the agent from running malicious code?" — Docker sandbox with `network_mode=none`, memory/CPU caps, command whitelist, 60s timeout. The agent can only modify files in the cloned repo volume.
2. "How does the agent avoid infinite loops?" — Hard cap of `max_iterations=5`. After that, the graph goes to human approval regardless of test status, with a note that tests did not pass.
3. "How do you handle large codebases?" — Repo map with depth limit and file summarization keeps context under ~2K tokens. The agent searches rather than reads everything. Files > 10KB are summarized, not read in full.
4. "Why not just use the GitHub Copilot API?" — This is a demonstration of the engineering. The value is understanding the architecture: tool use, sandboxing, planning, iteration loops — not outsourcing to a black box.
