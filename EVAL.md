# Sentinal — Evaluation Log

Every prompt, model, or retrieval change gets measured on both axes. Recall
alone is gameable by a chatty agent; precision alone is gameable by a silent
one. Numbers below are the ones verified by reading output, not the heuristic
scorer's — it has over-reported twice and both cases are recorded.

**Detection** — `--selftest` (self-contained bugs) and `--selftest-xfile`
(cross-file bugs) against diffs with planted, documented defects.

**False positives** — merged, cleanly-reviewed PRs from `axios/axios`, plus
"safe" fixtures: identical diffs where context proves nothing is broken and the
correct output is zero comments.

---

## Prompt and model iterations

| # | Change | Model | Detection | False positives | Notes |
|---|---|---|---|---|---|
| 1 | Initial prompt | llama-3.3-70b | not measured | 3 on 1 clean PR | Restated the PR's own fix as a finding; generic "add tests"; style nit. Zero real findings |
| 2 | Rubric rewrite; `failure_scenario` required and enforced in code | llama-3.3-70b | 1/4 | 0 | Precision fixed. Heuristic scorer claimed 2/4 — it matched the word "promise" in an unrelated comment |
| 3 | Scoring signals tightened, token cap added | llama-3.3-70b | 2/4 | 0 | Honest baseline |
| 4 | Model swap only, prompt unchanged | gpt-oss-120b | 4/4 | 0 | Capability, not prompting |

Controlled: #3 → #4 changed one variable. Recall 50% → 100%, precision held.

---

## Does codebase context help? (Phase 3 justification)

First attempt measured the wrong axis. Cross-file fixtures, oracle context:

| | diff only | with perfect context |
|---|---|---|
| Detection (bug present) | 3/3 | 3/3 |

Detection was saturated — a capable model guesses "callers may expect the old
shape" from the diff alone. But that guess is *speculation*: it cannot know
whether any caller actually breaks. So the same diffs were re-run with context
proving the change was safe, where the correct answer is silence:

| | diff only | with perfect context |
|---|---|---|
| False positives (no bug present) | 4 | 2 |

**Context's value is suppressing unfounded warnings, not finding more bugs.**
The oracle's remaining 2 false positives are not context failures — perfect
information did not remove them. They are rubric failures, and belong to the
self-critique phase.

---

## Retrieval comparison

Corpus: 13 files with deliberate distractors — two mention `ECONNABORTED`,
three do header normalisation, two handle config objects.

| mode | detection | false positives | right file retrieved |
|---|---|---|---|
| none | 3/3 | 4 | — |
| symbol (lexical) | 3/3 | **2** | 5/6 |
| embeddings | not yet run | not yet run | not yet run |
| oracle (perfect context) | 3/3 | **2** | — |

**Symbol search matched the oracle.** Exact-symbol lookup plus an import check
captured all of the available benefit at zero marginal cost and zero
infrastructure. A vector store has no measured headroom left on this set.

The one retrieval miss is instructive: `shouldRetry.js` never imports
`timeout.js` and shares exactly one token with the diff (`'ECONNABORTED'`),
while the distractor `xhr.js` shares that literal plus `timeout` and `err`.
Lexical ranking structurally cannot win that case — it is the one place
embeddings could plausibly beat it, and it is why the comparison is still worth
finishing.

### Caveats, stated plainly
- 3 cross-file fixtures, 6 retrieval trials. Small.
- Fixtures are synthetic and written by the same person who tuned the retriever.
- Embedding retriever is implemented but unmeasured (needs `OPENAI_API_KEY`).
  No claim about lexical-vs-semantic is warranted until it runs.

---

## Open items

- [ ] Run `--bench-retrieval` with an OpenAI key to fill the embeddings row
- [ ] Precision on real PRs is n=1. Run 5 more merged, cleanly-reviewed PRs
- [ ] Attack the residual 2 false positives with self-critique (Phase 5) — the
      oracle result proves retrieval cannot touch them
- [ ] Add fixtures for uncovered bug classes: race conditions, resource leaks,
      swallowed errors, auth checks on the wrong object

---

## For the README

The headline is not a metric, it is a method. Three times, measuring carefully
overturned the obvious answer:

1. The first agent produced 3 comments and 0 real findings — it was restating
   the author's fix back at them.
2. The recall scorer itself was buggy and inflating results. Caught by reading
   output that the number said was fine.
3. Retrieval was justified for the wrong reason. It does not find more bugs; it
   stops the agent from crying wolf — and the cheap lexical version matched
   perfect context, so the planned vector database was not built.

"I measured before building, and the measurement said don't build it" is a
stronger engineering signal than any architecture diagram.
