# pr-sentinal — Build Roadmap
### (Display name: Sentinal | Repo/package name: pr-sentinal)

**Goal:** Ship a working, evaluated, portfolio-ready autonomous PR review agent in the shortest realistic time — roughly **14-18 days** at 2-4 focused hours/day (student pace), or **~7-8 days** if you can go near full-time.

The plan is sequenced so you have a demo-able thing early (end of Phase 2) and everything after that is what makes it *impressive* rather than just functional. If you run out of time, you can stop after Phase 4 and still have a strong project.

---

## Stack decisions (locked in now to avoid burning days on tooling choices)

| Layer | Choice | Why |
|---|---|---|
| LLM | Groq API | You already have working integration + fast inference (matters for an agent loop with many calls) |
| Orchestration | Simple custom Python state machine first; upgrade to LangGraph only if time allows | Debugging a framework you don't know eats days; a plan→act→observe→revise loop is ~150 lines of your own code |
| Vector store | Postgres + pgvector | You already know Postgres — zero new infra to learn |
| Embeddings | Hosted embedding API (OpenAI `text-embedding-3-small` or Voyage) | Avoids GPU/local model setup entirely |
| Sandbox execution | Docker | You already do this in HealthNest/HirePilot |
| GitHub integration | GitHub REST API + Personal Access Token | A full GitHub App with webhooks is a stretch goal, not a blocker — PAT + polling or manual trigger is enough for v1 |
| Test target | **A public repo with an active review culture** (see Phase 6) | Your own repos have zero PRs, and more importantly public repos come with *real maintainer review comments* — free ground-truth labels for evaluation |

---

## Phase 0 — Setup (Day 1, ~2-3 hrs)

- [ ] New repo: `pr-sentinal`
- [ ] Groq API key, GitHub PAT with repo scope, Postgres instance with pgvector extension enabled
- [ ] Pick your first target: one of your own repos with at least 5-10 closed PRs (for later eval)
- [ ] Write a one-paragraph spec for yourself: what counts as a "good" review comment for this project (bug risk, security issue, missed test, style violation you actually care about) — this prevents scope creep later

**Deliverable:** empty repo, working API keys, a target repo picked.

---

## Phase 1 — Fetch & understand a PR (Days 2-3, ~4-6 hrs)

- [ ] Script that takes a PR URL and pulls: the diff, changed file list, full content of changed files, PR description
- [ ] Parse the diff into a structured format (file, hunk, added/removed lines) — don't hand this raw to the LLM, structure it first
- [ ] Sanity check: print a clean, readable summary of any PR from your target repo

**Deliverable:** `fetch_pr.py` — given a PR URL, outputs structured diff + context. No LLM involved yet.

---

## Phase 2 — Minimum viable review (Days 4-6, ~6-8 hrs) → **first demo-able version**

- [ ] Single LLM call: feed the structured diff to Groq, ask it to draft review comments
- [ ] Post comments back via GitHub API (as a draft/dry-run first — print instead of posting until you trust it)
- [ ] Run it end-to-end on 3-5 real PRs from your target repo

**Deliverable:** a working, if unsophisticated, review bot. This is your fallback "it works" checkpoint — everything past this point is upgrading quality, not building from scratch.

---

## Phase 3 — Give it real context via retrieval (Days 7-9, ~6-8 hrs)

This is the part that turns "LLM read a diff" into "agent that understands the codebase."

- [ ] Chunk and embed the full repo (not just the diff) into pgvector
- [ ] Before drafting a review, retrieve related code: functions the diff calls, functions that call the changed code, similar existing patterns elsewhere in the repo
- [ ] Re-run the LLM call with diff + retrieved context; compare output quality against Phase 2 on the same PRs — save both outputs, you'll want this comparison later for your README/interview story

**Deliverable:** retrieval-augmented review generation, with a documented before/after quality comparison.

---

## Phase 4 — Tool use: let it actually run things (Days 10-12, ~6-8 hrs)

- [ ] Dockerized sandbox that can run the repo's test suite and linter against the PR branch
- [ ] Agent decides *when* to invoke a tool (e.g., "this diff touches a function with existing tests → run them") rather than always running everything — this is what makes it agentic rather than a fixed pipeline
- [ ] Feed tool output (test failures, lint errors) back into the review-drafting step

**Deliverable:** agent that runs real tools and incorporates results into its comments, not just LLM opinion.

---

## Phase 5 — Self-critique loop (Days 13-14, ~4-6 hrs)

- [ ] Before posting, have the agent re-read its own draft comments against a rubric (is this actually a bug, or noise? is this comment specific and actionable?) and drop or rewrite weak ones
- [ ] Log what got filtered — this becomes a concrete "reduced false-positive rate by X%" number, same style as your HealthNest latency stat

**Deliverable:** measurable noise reduction between raw draft and posted comments.

---

## Phase 6 — Evaluation set (Days 15-16, ~4-6 hrs) — **do not skip this**

**Ground truth comes from real human reviewers, not your own guesses.** Pick merged PRs
from a public repo that *received substantive review comments*, and treat what the
maintainer actually flagged as the label. This is a stronger eval than self-labeling and
a much better interview line: *"I benchmarked against what human reviewers actually caught."*

Repo selection criteria (pick ONE, stick with it):
- Active review culture — PRs have real comments, not just "LGTM"
- Language you can read fluently (JS/TS given your stack, or Python)
- Small enough that its test suite runs in a container without a huge setup

Good candidates: `expressjs/express`, `axios/axios`, `pallets/flask`, `fastapi/fastapi`.

- [ ] Pick the repo, then collect 15-20 merged PRs that have real review comments
- [ ] Extract the human review comments via the GitHub API (`/pulls/{n}/comments`) — these are your labels
- [ ] Normalize each into: file, line/hunk, category (bug / security / test-gap / style), one-line summary
- [ ] Run the agent on the same PRs with review comments hidden, compute precision/recall against the human labels
- [ ] Report the numbers honestly, including where the agent found things humans missed (that's a *feature*, note it separately rather than counting it as a false positive)

**Deliverable:** a real evaluation table benchmarked against human reviewers. This is the
single highest-leverage thing for making the project credible — it's the difference between
"I built a demo" and "I built and measured a system."

---

## Phase 7 — Polish & ship (Days 17-18, ~4-6 hrs)

- [ ] README with architecture diagram (plan→act→observe→revise loop), the eval numbers, before/after retrieval comparison, and a short demo video/GIF
- [ ] Deploy or at minimum make it runnable via a single command/Docker Compose
- [ ] One paragraph you can say out loud in an interview: what it does, the hardest technical decision, and the eval result

**Deliverable:** portfolio-ready repo + a rehearsed 60-second pitch.

---

## Stretch goals (only if time remains)

- GitHub App with webhook auto-trigger on new PRs (instead of manual URL input)
- LangGraph migration if you want the framework name on your resume specifically
- Multi-agent split (a "security reviewer" + "style reviewer" + "logic reviewer" that vote/merge) — genuinely impressive but real scope, don't start this until Phase 6 is done

---

## Time-compression notes

- If you're tight on time, **Phases 3 and 6 are non-negotiable** — retrieval is what makes it more than a chatbot, and the eval is what makes it credible. Everything else can be simplified.
- Phase 4 (tool sandboxing) can be simplified to "run linter only" instead of full test suites if Docker setup is eating time.
- Don't build the GitHub App/webhook version until the core loop is proven — it adds infra complexity for zero improvement in what the agent actually does.

---

## Environment gotchas (hit during setup, recorded so they don't bite twice)

- **Python 3.14** is newer than several packages have wheels for. `psycopg2-binary` fails to
  build on it (wants MSVC C++ build tools). Use `psycopg[binary]` instead when Phase 3 needs
  a Postgres driver — do not install the C++ build tools just for this.
- **PowerShell execution policy** blocks venv activation. One-time fix:
  `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
- Phase 1 only needs: `PyGithub python-dotenv groq rich`. Install the DB/embedding deps at
  the start of Phase 3, not before.
