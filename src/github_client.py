"""Thin wrapper around PyGithub for fetching PR diffs in a structured form."""
import re
from dataclasses import dataclass, field
from typing import List

from github import Github

from src.config import get_settings

PR_URL_RE = re.compile(
    r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
)


@dataclass
class FileChange:
    filename: str
    status: str  # "added", "modified", "removed", "renamed"
    additions: int
    deletions: int
    patch: str  # unified diff hunk for this file, empty for binary files


@dataclass
class PullRequestContext:
    owner: str
    repo: str
    number: int
    title: str
    body: str
    base_branch: str
    head_branch: str
    files: List[FileChange] = field(default_factory=list)


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Extract (owner, repo, pr_number) from a github.com PR URL."""
    match = PR_URL_RE.search(url)
    if not match:
        raise ValueError(
            f"Could not parse a PR URL from: {url!r}. "
            "Expected format: https://github.com/<owner>/<repo>/pull/<number>"
        )
    return match["owner"], match["repo"], int(match["number"])


def fetch_pr_context(pr_url: str) -> PullRequestContext:
    """Fetch a PR's metadata and per-file diffs from the GitHub API."""
    settings = get_settings()
    owner, repo_name, number = parse_pr_url(pr_url)

    client = Github(settings.github_token)
    repo = client.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(number)

    files = [
        FileChange(
            filename=f.filename,
            status=f.status,
            additions=f.additions,
            deletions=f.deletions,
            patch=f.patch or "",
        )
        for f in pr.get_files()
    ]

    return PullRequestContext(
        owner=owner,
        repo=repo_name,
        number=number,
        title=pr.title,
        body=pr.body or "",
        base_branch=pr.base.ref,
        head_branch=pr.head.ref,
        files=files,
    )


def post_review_comment(pr_url: str, body: str, dry_run: bool = True) -> None:
    """Post a general PR comment. Defaults to dry-run (prints instead of posting)
    until Phase 2 review quality is trusted."""
    if dry_run:
        print("--- DRY RUN: would post the following comment ---")
        print(body)
        print("--- end dry run ---")
        return

    settings = get_settings()
    owner, repo_name, number = parse_pr_url(pr_url)
    client = Github(settings.github_token)
    repo = client.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(number)
    pr.create_issue_comment(body)
