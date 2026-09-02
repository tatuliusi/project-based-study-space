from __future__ import annotations

import pytest

from src.github_client import _client, fetch_issue, open_pull_request
from src.models import Issue, ImplementationPlan, PlanStep


def _make_issue(number: int = 1, title: str = "Fix bug") -> Issue:
    return Issue(
        number=number,
        title=title,
        body="The bug is in divide()",
        repo_full_name="acme/calculator",
        url=f"https://github.com/acme/calculator/issues/{number}",
        labels=["bug"],
    )


def test_fetch_issue_url_parsing(monkeypatch):
    captured = {}

    class FakeIssue:
        number = 42
        title = "Fix something"
        body = "body text"
        labels = []
        html_url = "https://github.com/acme/calc/issues/42"

    class FakeRepo:
        def get_issue(self, n):
            captured["number"] = n
            return FakeIssue()

    class FakeGithub:
        def get_repo(self, name):
            captured["repo"] = name
            return FakeRepo()

    monkeypatch.setattr("src.github_client.Github", lambda token: FakeGithub())
    result = fetch_issue("https://github.com/acme/calc/issues/42")
    assert captured["repo"] == "acme/calc"
    assert captured["number"] == 42
    assert result.number == 42
    assert result.title == "Fix something"


def test_fetch_issue_extracts_labels(monkeypatch):
    class FakeLabel:
        name = "bug"

    class FakeIssue:
        number = 1
        title = "t"
        body = "b"
        labels = [FakeLabel()]
        html_url = ""

    class FakeRepo:
        def get_issue(self, n):
            return FakeIssue()

    class FakeGithub:
        def get_repo(self, name):
            return FakeRepo()

    monkeypatch.setattr("src.github_client.Github", lambda token: FakeGithub())
    result = fetch_issue("https://github.com/a/b/issues/1")
    assert "bug" in result.labels


def test_open_pull_request_returns_url(monkeypatch):
    class FakePR:
        html_url = "https://github.com/acme/calc/pull/5"

    class FakeRepo:
        default_branch = "main"

        def create_pull(self, **kwargs):
            return FakePR()

    class FakeGithub:
        def get_repo(self, name):
            return FakeRepo()

    monkeypatch.setattr("src.github_client.Github", lambda token: FakeGithub())
    issue = _make_issue()
    plan = ImplementationPlan(
        steps=[PlanStep(step_number=1, description="d", file_path="f.py", action="modify", rationale="r")],
        affected_files=["f.py"],
        test_strategy="run tests",
        estimated_complexity="small",
    )
    url = open_pull_request("acme/calculator", "agent/fix-issue-1", issue, "## Plan\n1. step")
    assert url == "https://github.com/acme/calc/pull/5"
