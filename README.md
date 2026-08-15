# pr-sentinal

An autonomous AI agent that reviews GitHub pull requests: it retrieves relevant
codebase context, runs the repo's own tests/linters in a sandbox, drafts review
comments, self-critiques them against a rubric, and posts the survivors back to
the PR — the way a senior engineer would review, not just an LLM reading a diff.

## Status

🚧 In active development. See `ROADMAP.md` for build phases.

## Architecture (target)

```
PR URL
  │
  ▼
fetch_pr.py ── pulls diff + changed files via GitHub API
  │
  ▼
retrieval ── embeds & searches related code in pgvector
  │
  ▼
tool use ── runs linter/tests in Docker sandbox
  │
  ▼
LLM review draft (Groq) ── diff + retrieved context + tool output
  │
  ▼
self-critique ── drops/rewrites weak or noisy comments
  │
  ▼
post to GitHub PR
```

## Setup

1. Copy `.env.example` to `.env` and fill in:
   - `GITHUB_TOKEN` — a GitHub Personal Access Token with `repo` scope
   - `GROQ_API_KEY` — your Groq API key
   - `DATABASE_URL` — leave as default if using the provided docker-compose

2. Start Postgres with pgvector:
   ```
   docker compose up -d
   ```

3. Install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. Try Phase 1 (fetch & inspect a PR, no LLM yet):
   ```
   python -m src.fetch_pr https://github.com/<owner>/<repo>/pull/<number>
   ```

## Evaluation

See `eval/` (added in Phase 6) for the hand-labeled PR set and precision/recall
results once the agent is functional.
