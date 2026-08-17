"""Get a local copy of the repository so retrieval has something to search.

The benchmarks measured retrieval against a synthetic corpus held in memory.
Real pull requests need the actual repository, and there are two ways to get it:

  1. Fetch each file through the GitHub API. One HTTP request per file, against
     an hourly rate limit, and you must guess which files to ask for before you
     have anything to search.
  2. Shallow-clone once and read from disk.

(2) wins on every axis: a single network operation, no per-file rate limit, and
the whole repo is available to search rather than a guessed subset. `--depth 1`
keeps it small - axios is a few MB - and the clone is cached between runs.

Only source files are loaded, and each is truncated, because this corpus is
scored in memory on every review.
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

CACHE_DIR = Path(os.getenv("SENTINAL_CACHE", ".cache/repos"))

SOURCE_EXTENSIONS = {
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".py", ".rb", ".go", ".java", ".rs", ".php",
}

SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", "coverage",
    "vendor", "__pycache__", ".next", "bower_components",
}

MAX_FILES = 1200
MAX_FILE_CHARS = 8000


def git_available() -> bool:
    return shutil.which("git") is not None


def ensure_repo(owner: str, repo: str, quiet: bool = False) -> Optional[Path]:
    """Shallow-clone (or reuse) the repository. Returns None if unavailable."""
    if not git_available():
        return None

    dest = CACHE_DIR / f"{owner}__{repo}"
    if dest.exists() and (dest / ".git").exists():
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/{owner}/{repo}.git"

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", url, str(dest)],
            check=True,
            capture_output=True,
            timeout=300,
        )
        return dest
    except Exception:  # noqa: BLE001 - retrieval is an enhancement, never a blocker
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        return None


def load_corpus(root: Path, exclude: Optional[set] = None) -> List[Dict]:
    """Read source files into the shape SymbolRetriever expects.

    `exclude` should hold the paths changed by the PR - the diff already shows
    those, and retrieving a file that is already in front of the model wastes
    the context budget it was meant to spend on something new.
    """
    exclude = exclude or set()
    corpus: List[Dict] = []

    for path in root.rglob("*"):
        if len(corpus) >= MAX_FILES:
            break
        if not path.is_file():
            continue
        if path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue

        rel = path.relative_to(root).as_posix()
        if rel in exclude:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        corpus.append({"path": rel, "content": text[:MAX_FILE_CHARS]})

    return corpus
