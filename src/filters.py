"""Decide which files in a PR are worth reviewing.

Dependency lockfiles, build output, vendored code and binaries make up a huge
share of the diff bytes in real PRs and are worthless to review: they're
machine-generated, nobody reads them, and they crowd out the actual source
changes in the model's context window. Filtering them is the cheapest quality
win in the whole pipeline.
"""
import re
from typing import Iterable, List, Tuple

# Machine-generated files: never worth reviewing line-by-line.
SKIP_FILENAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "Gemfile.lock",
    "composer.lock",
    "go.sum",
    "Cargo.lock",
}

SKIP_PATH_PATTERNS = [
    re.compile(p)
    for p in (
        # Prose. A code reviewer has nothing useful to say about a changelog,
        # and on one real PR these files consumed a whole request batch - about
        # 11% of a daily token budget spent reviewing markdown.
        r"\.(md|mdx|rst|txt)$",
        r"(^|/)docs?/",
        r"(^|/)\.github/",
        r"(^|/)CHANGELOG",
        r"(^|/)node_modules/",
        r"(^|/)vendor/",
        r"(^|/)dist/",
        r"(^|/)build/",
        r"(^|/)\.next/",
        r"(^|/)coverage/",
        r"(^|/)__snapshots__/",
        r"(^|/)migrations?/.*\.sql$",  # usually generated; review the model change instead
        r"\.min\.(js|css)$",
        r"\.map$",
        r"\.(png|jpe?g|gif|svg|ico|webp|pdf|zip|gz|woff2?|ttf|eot|mp4)$",
        r"\.(snap|lock)$",
    )
]

# Very large diffs on a single file are usually generated or a bulk rename.
MAX_PATCH_LINES = 400


DOC_RE = re.compile(r"\.(md|mdx|rst|txt)$|(^|/)docs?/|(^|/)\.github/|(^|/)CHANGELOG")


def should_review(filename: str) -> Tuple[bool, str]:
    """Return (keep, reason_if_skipped)."""
    basename = filename.rsplit("/", 1)[-1]

    if basename in SKIP_FILENAMES:
        return False, "dependency lockfile"

    if DOC_RE.search(filename):
        return False, "documentation / prose"

    for pattern in SKIP_PATH_PATTERNS:
        if pattern.search(filename):
            return False, "generated / vendored / binary"

    return True, ""


def partition_files(files: Iterable) -> Tuple[List, List[Tuple[object, str]]]:
    """Split FileChange objects into (reviewable, [(skipped, reason), ...])."""
    keep, skipped = [], []
    for f in files:
        ok, reason = should_review(f.filename)
        if not ok:
            skipped.append((f, reason))
            continue
        if not f.patch:
            skipped.append((f, "no patch (binary or too large)"))
            continue
        if f.patch.count("\n") > MAX_PATCH_LINES:
            skipped.append((f, f"patch over {MAX_PATCH_LINES} lines"))
            continue
        keep.append(f)
    return keep, skipped
