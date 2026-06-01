import os
import re

import requests


_MAX_PATCH_CHARS = 3000
_MAX_FILES = 25


def parse_pr_ref(pr_ref: str) -> tuple[str, str, int]:
    """Parse 'owner/repo/123' or a full GitHub PR URL into (owner, repo, number)."""
    url_match = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_ref)
    if url_match:
        return url_match.group(1), url_match.group(2), int(url_match.group(3))

    parts = pr_ref.strip("/").split("/")
    if len(parts) == 3:
        return parts[0], parts[1], int(parts[2])

    raise ValueError(f"Cannot parse PR reference: {pr_ref!r}. Use 'owner/repo/123' or a GitHub PR URL.")


def fetch_pr_diff(owner: str, repo: str, pull_number: int) -> str:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3.diff"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def fetch_pr_files(owner: str, repo: str, pull_number: int) -> list[dict]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files"
    response = requests.get(url, headers=headers, params={"per_page": _MAX_FILES}, timeout=30)
    response.raise_for_status()
    return response.json()
