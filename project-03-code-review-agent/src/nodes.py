import re

from langchain_openai import ChatOpenAI

from src.github_client import fetch_pr_diff, fetch_pr_files, parse_pr_ref
from src.schemas import AgentFindings, CodeReview, FileSummary, Finding
from src.state import ReviewState

_MAX_PATCH_CHARS = 3000
_MAX_FILES = 25
_TRUNCATION_NOTICE = "\n[truncated]"

_SECURITY_SYSTEM = """You are a security-focused code reviewer. Analyze the PR diff for security vulnerabilities.

Look specifically for:
- SQL injection (string interpolation into queries)
- XSS (unescaped user input rendered to HTML)
- Path traversal (unsanitized file paths from user input)
- Hardcoded credentials, API keys, or secrets
- Unsafe deserialization
- Missing authentication or authorization checks
- Command injection (shell calls with user input)
- Insecure random number generation for security-sensitive use
- Sensitive data exposed in logs or responses
- Dependency version pins that reference known-vulnerable versions

Return only findings you are confident about from what is visible in the diff. If a line number is visible in the diff hunk header, include it.
"""

_LOGIC_SYSTEM = """You are a logic-focused code reviewer. Analyze the PR diff for correctness bugs.

Look specifically for:
- Null/None dereferences on unchecked values
- Off-by-one errors in loops or slices
- Race conditions in concurrent code
- Unhandled exceptions or missing error propagation
- Incorrect conditional logic (wrong operator, inverted condition)
- Integer overflow or underflow
- Infinite loops or missing termination conditions
- Incorrect algorithm implementation
- Missing edge cases (empty list, zero, negative numbers)
- Incorrect use of library APIs (wrong argument order, wrong method)

Return only findings you are confident about from what is visible in the diff.
"""

_STYLE_SYSTEM = """You are a style-focused code reviewer. Analyze the PR diff for code quality issues.

Look specifically for:
- Naming convention violations (inconsistent with surrounding code)
- Functions that do too many things or are excessively long
- Deep nesting that reduces readability
- Copy-pasted duplicated logic that should be extracted
- Missing type annotations on public functions
- Unclear or single-letter variable names in non-trivial contexts
- Missing docstrings on public classes or functions
- Dead code (unreachable branches, unused variables, commented-out blocks)
- Magic numbers that should be named constants

Return only findings you are confident about from what is visible in the diff.
"""

_WORKER_HUMAN = """Review the following pull request diff and return your findings.

PR: {pr_url}

Changed files ({file_count} files):

{files_block}
"""

_SUPERVISOR_SYSTEM = """You are a senior engineer synthesizing a code review from specialist agent findings.

Your job:
1. Set a verdict: "request_changes" if any critical or major findings exist, "comment" if only minor/info, "approve" if no findings.
2. Write a 2-4 sentence summary covering the overall quality and the most important concerns.
3. Select the top priority_issues across all categories (max 10), ranked by severity. Include only the most impactful ones — do not duplicate findings.
"""

_SUPERVISOR_HUMAN = """PR: {pr_url}

SECURITY FINDINGS:
{security}

LOGIC FINDINGS:
{logic}

STYLE FINDINGS:
{style}

Synthesize these into a final CodeReview.
"""


def _format_files(file_summaries: list[FileSummary]) -> str:
    blocks = []
    for f in file_summaries:
        patch = f.patch[:_MAX_PATCH_CHARS]
        if len(f.patch) > _MAX_PATCH_CHARS:
            patch += _TRUNCATION_NOTICE
        blocks.append(f"### {f.filename} ({f.status})\n```diff\n{patch}\n```")
    return "\n\n".join(blocks)


def _format_findings(findings: list[Finding]) -> str:
    if not findings:
        return "None"
    lines = []
    for f in findings:
        loc = f"{f.file}:{f.line}" if f.line else f.file
        lines.append(f"- [{f.severity.upper()}] {loc}: {f.description}\n  Suggestion: {f.suggestion}")
    return "\n".join(lines)


def fetch_pr_diff_node(state: ReviewState) -> dict:
    owner, repo, number = parse_pr_ref(state["pr_url"])
    raw_diff = fetch_pr_diff(owner, repo, number)
    return {"diff": raw_diff}


def parse_diff_node(state: ReviewState) -> dict:
    files_data = []

    # Try to use the GitHub files API result embedded in state (via diff text),
    # but we parse the unified diff directly since that's what we fetched.
    diff = state["diff"]
    sections = re.split(r"(?=diff --git )", diff.strip())

    for section in sections[:_MAX_FILES]:
        if not section.strip():
            continue

        header = re.match(r"diff --git a/(.+?) b/(.+?)\n", section)
        if not header:
            continue
        filename = header.group(2)

        if "new file mode" in section:
            status = "added"
        elif "deleted file mode" in section:
            status = "removed"
        else:
            status = "modified"

        hunk_match = re.search(r"(@@.+)", section, re.DOTALL)
        patch = hunk_match.group(0) if hunk_match else ""

        files_data.append(FileSummary(filename=filename, status=status, patch=patch))

    return {"file_summaries": files_data}


def _run_worker(state: ReviewState, system_prompt: str, findings_key: str) -> dict:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(AgentFindings)

    files_block = _format_files(state.get("file_summaries", []))
    human = _WORKER_HUMAN.format(
        pr_url=state["pr_url"],
        file_count=len(state.get("file_summaries", [])),
        files_block=files_block,
    )

    result: AgentFindings = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": human},
    ])

    return {findings_key: result.findings}


def security_agent(state: ReviewState) -> dict:
    return _run_worker(state, _SECURITY_SYSTEM, "security_findings")


def logic_agent(state: ReviewState) -> dict:
    return _run_worker(state, _LOGIC_SYSTEM, "logic_findings")


def style_agent(state: ReviewState) -> dict:
    return _run_worker(state, _STYLE_SYSTEM, "style_findings")


def generate_review(state: ReviewState) -> dict:
    llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(CodeReview)

    human = _SUPERVISOR_HUMAN.format(
        pr_url=state["pr_url"],
        security=_format_findings(state.get("security_findings", [])),
        logic=_format_findings(state.get("logic_findings", [])),
        style=_format_findings(state.get("style_findings", [])),
    )

    result: CodeReview = llm.invoke([
        {"role": "system", "content": _SUPERVISOR_SYSTEM},
        {"role": "user", "content": human},
    ])

    return {"final_review": result}
