# Sentinal — Evaluation Log

Every prompt, model, or retrieval change gets measured on both axes. Recall
alone is gameable by a chatty agent; precision alone is gameable by a silent
one. Numbers below are the ones verified by reading output, not the heuristic
scorer's — it has over-reported twice and both cases are recorded.

**Detection** — `--selftest` (self-contained bugs) and `--selftest-xfile`
(cross-file bugs) against diffs with planted, documented defects.

The automatic scorer matches keywords and **has failed in both directions**: it
once scored a HIT because an unrelated comment contained the word "promise",
and later scored a MISS on a textbook-correct description of a shared-mutation
bug because the model wrote "retain the changes" instead of "persist across".
Both were caught by reading output the number said was fine. Treat it as a
convenience only; the recorded score is always the one verified by reading.

**False positives** — merged, cleanly-reviewed PRs from `axios/axios`, plus
"safe" fixtures: identical diffs where context proves nothing is broken and the
correct output is zero comments.

---

## ⚠️ Validity note — read before trusting any number here

A long stretch of results in this project were measured while the Groq daily
token quota was draining and then exhausted (HTTP 429). A failed model call
returned no comments, and the harness scored that as "found no bugs" — so an
outage was indistinguishable from a bad reviewer. Scores degraded 4/4 → 3/4 →
2/4 → 0/4 and were diagnosed, wrongly and repeatedly, as temperature noise, an
over-aggressive critic, and an over-eager execution check.

Fixed: every model call now increments a failure counter and any run with a
non-zero count prints MEASUREMENT INVALID and must be discarded.

Status of the numbers below:
- **Valid** — anything explicitly re-run after the fix, on a quiet banner.
- **Suspect** — the mid-session 3/4 and 2/4 recall figures.
- **Invalid** — every 0/4. Those were an outage, not a result.

The retrieval comparison (4 → 2 → 2 false alarms) was taken early, well below
the quota ceiling, and is most likely sound — but it should be re-run once on
fresh quota before being quoted anywhere.

---

## Prompt and model iterations

| # | Change | Model | Detection | False positives | Notes |
|---|---|---|---|---|---|
| 1 | Initial prompt | llama-3.3-70b | not measured | 3 on 1 clean PR | Restated the PR's own fix as a finding; generic "add tests"; style nit. Zero real findings |
| 2 | Rubric rewrite; `failure_scenario` required and enforced in code | llama-3.3-70b | 1/4 | 0 | Precision fixed. Heuristic scorer claimed 2/4 — it matched the word "promise" in an unrelated comment |
| 3 | Scoring signals tightened, token cap added | llama-3.3-70b | 2/4 | 0 | Honest baseline |
| 4 | Model swap only, prompt unchanged | gpt-oss-120b | 4/4 | 0 | Capability, not prompting |
| 5 | Critic fix (self-contained vs cross-file claims) + critic token cap 300→1500 | llama-3.3-70b | **3/4 (verified by reading)** | — | First run after the quota fix, banner quiet. Scorer said 2/4; fixture 4 was a genuine hit it failed to match |

Controlled: #3 → #4 changed one variable. Recall 50% → 100%, precision held.

Row 5 is on the *weaker* model (quota exhausted on gpt-oss-120b), so 3/4 is not
comparable to row 4's 4/4. The one genuine miss — the unawaited async call — is
the same class llama-3.3-70b missed in row 3, which is consistent: it is a model
capability gap, not a pipeline regression.

Two things row 5 does establish, both previously unknown:
- The critic works. It kept three real findings and dropped nothing valid. Every
  earlier 0/4 was the outage, not the critic.
- The critic prompt fix matters: it now separates claims provable from the diff
  alone (an off-by-one is proof of itself) from claims that need other files.

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

---

## Self-critique ablation (Phase 5)

An independent critic call per drafted comment, told that absent evidence means
reject. Same fixtures, one variable changed.

| | detection (diff only) | FP (diff only) | detection (with context) | FP (with context) |
|---|---|---|---|---|
| no critique | 3/3 | 3–4 | 3/3 | 2 |
| **with critique** | 2/3 | 2 | **3/3** | **0** |

**These two phases are not independent — retrieval supplies the evidence the
critic demands.**

- Retrieval alone: still 2 false positives.
- Critique alone: costs a real finding (3/3 → 2/3), because blind cross-file
  findings were speculation that happened to be right. The critic rejects
  unevidenced claims and cannot tell a lucky guess from a wrong one — correctly.
- Together: 3/3 detection, 0 false positives.

The blind-plus-critic row is the most informative cell in this whole document.
It shows the cost of demanding rigour without supplying information, and it is
why "add a self-critique step" is not a free improvement.

### Caveats, stated plainly
- 3 cross-file fixtures, 6 retrieval trials. Small.
- Fixtures are synthetic and written by the same person who tuned the retriever.
- Embedding retriever is implemented but unmeasured (needs `OPENAI_API_KEY`).
  No claim about lexical-vs-semantic is warranted until it runs.
- **Run-to-run variance is real.** The no-critique blind FP count came out 4 on
  one run and 3 on the next with nothing changed — the drafter runs at
  `temperature=0.2`. Single runs at n=3 cannot separate a 1-point difference
  from noise. Every number quoted as final should be the median of 3 runs, or
  the drafter should be pinned to `temperature=0.0` and the figures regenerated.
  Differences of 2+ (4→2, 2→0) are outside the observed noise band; a 1-point
  move is not.

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
4. Self-critique is not a free win. Added alone it *cost* a real finding. It only
   pays off once retrieval supplies the evidence it demands — 3/3 detection with
   0 false positives, where each component alone plateaus.

"I measured before building, and the measurement said don't build it" is a
stronger engineering signal than any architecture diagram.
