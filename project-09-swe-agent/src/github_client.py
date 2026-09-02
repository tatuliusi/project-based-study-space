from __future__ import annotations

from github import Github, GithubException
from github.Repository import Repository

from .config import settings
from .models import Issue


def _client() -> Github:
    return Github(settings.github_token)


def fetch_issue(issue_url: str) -> Issue:
    """Parse a GitHub issue URL and return an Issue model."""
    g = _client()
    parts = issue_url.rstrip("/").split("/")
    repo_full_name = f"{parts[-4]}/{parts[-3]}"
    issue_number = int(parts[-1])

    repo = g.get_repo(repo_full_name)
    gh_issue = repo.get_issue(issue_number)
    labels = [label.name for label in gh_issue.labels]

    return Issue(
        number=gh_issue.number,
        title=gh_issue.title,
        body=gh_issue.body or "",
        repo_full_name=repo_full_name,
        url=issue_url,
        labels=labels,
    )


def clone_repo(repo_full_name: str, target_dir: str) -> str:
    """Return the HTTPS clone URL for a repository."""
    g = _client()
    repo = g.get_repo(repo_full_name)
    return repo.clone_url


def create_branch(repo_full_name: str, branch_name: str, base_sha: str) -> None:
    g = _client()
    repo = g.get_repo(repo_full_name)
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)


def get_default_branch_sha(repo_full_name: str) -> str:
    g = _client()
    repo = g.get_repo(repo_full_name)
    branch = repo.get_branch(repo.default_branch)
    return branch.commit.sha


def open_pull_request(
    repo_full_name: str,
    head_branch: str,
    issue: Issue,
    plan_markdown: str,
) -> str:
    g = _client()
    repo = g.get_repo(repo_full_name)
    pr = repo.create_pull(
        title=f"fix: {issue.title}",
        body=plan_markdown,
        head=head_branch,
        base=repo.default_branch,
    )
    return pr.html_url


def commit_files(
    repo_full_name: str,
    branch_name: str,
    files: dict[str, str],
    commit_message: str,
) -> None:
    """Commit one or more file contents to a branch via the GitHub contents API."""
    g = _client()
    repo = g.get_repo(repo_full_name)

    for file_path, content in files.items():
        try:
            existing = repo.get_contents(file_path, ref=branch_name)
            repo.update_file(
                path=file_path,
                message=commit_message,
                content=content,
                sha=existing.sha,
                branch=branch_name,
            )
        except GithubException:
            repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
                branch=branch_name,
            )
