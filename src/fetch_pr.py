"""Phase 1 entry point: given a PR URL, fetch and print a structured summary.

No LLM calls here yet — this just proves the GitHub integration works and
gives you a clean, structured view of a PR to build the review-drafting
step on top of in Phase 2.

Usage:
    python -m src.fetch_pr https://github.com/<owner>/<repo>/pull/<number>
"""
import sys

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.syntax import Syntax

from src.github_client import fetch_pr_context

console = Console()


def main() -> None:
    if len(sys.argv) != 2:
        console.print("[red]Usage:[/red] python -m src.fetch_pr <pr_url>")
        sys.exit(1)

    pr_url = sys.argv[1]
    ctx = fetch_pr_context(pr_url)

    # PR titles/bodies are arbitrary user text and routinely contain square
    # brackets (markdown links, "[//]" comment tricks, "[skip ci]", ...).
    # rich would try to parse those as markup tags and blow up, so escape
    # everything that came from the API before handing it to the console.
    title = escape(ctx.title)
    body = escape(ctx.body) if ctx.body else "(no description)"

    console.print(
        Panel(
            f"[bold]{title}[/bold]\n\n{body}",
            title=escape(
                f"{ctx.owner}/{ctx.repo} #{ctx.number}  "
                f"({ctx.head_branch} -> {ctx.base_branch})"
            ),
        )
    )

    console.print(f"\n[bold]{len(ctx.files)} file(s) changed[/bold]\n")

    for f in ctx.files:
        console.print(
            f"[cyan]{escape(f.filename)}[/cyan]  "
            f"[green]+{f.additions}[/green] [red]-{f.deletions}[/red]  ({f.status})"
        )
        if f.patch:
            # Syntax() renders literally, so the patch itself needs no escaping.
            console.print(Syntax(f.patch, "diff", theme="ansi_dark", word_wrap=True))
        else:
            console.print("  [dim](binary or no patch available)[/dim]")
        console.print()


if __name__ == "__main__":
    main()
