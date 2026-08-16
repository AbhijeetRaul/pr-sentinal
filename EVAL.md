# Sentinal — Evaluation Log

Every prompt, model, or retrieval change is measured on two axes. Detection
alone is gameable by a chatty agent; a low false-positive count alone is
gameable by a silent one.

**Detection** — `--selftest` (8 self-contained bugs) and `--selftest-xfile`
(3 cross-file bugs) against diffs with planted, documented defects.

**False positives** — "safe" fixtures: the same diffs paired with context
proving nothing is broken, where the correct output is zero comments.

The automatic scorer matches keywords and **has failed in both directions**: it
once scored a HIT because an unrelated comment contained the word "promise", and
later scored a MISS on a textbook-correct description of a shared-mutation bug
because the model wrote "retain the changes" instead of "persist across". Both
were caught by reading output the number said was fine. Recorded scores are the
ones verified by reading.

---

## Validated results

All figures below: `openai/gpt-oss-120b`, `temperature=0.0`, automatic retry on
rate limits, MEASUREMENT INVALID banner quiet for the whole run.

### Self-contained bugs — 8/8

Every planted defect found and described correctly, including the two hardest:

- **Broken ownership check** — "the check uses `req.params.id` but the response
  returns the document identified by `req.query.docId`", with the exact attack:
  `GET /documents/123?docId=456`.
- **Race condition** — "both see taken < capacity and both succeed, exceeding
  event.capacity."

Two things better than the score itself:

**The critic visibly earned its place.** On the RegExp fixture the drafter
produced two comments: one claiming a syntax error would be thrown (false), one
about unescaped metacharacters letting `.*` bypass the allowlist (true). The
critic killed the false one and kept the true one.

**It found a defect the fixture author did not plant.** On the interval fixture
it noticed `pollJob` now returns a timer ID where it previously returned a
Promise, breaking `pollJob(id).then(...)`. That bug was accidental and unnoticed.

### Cross-file bugs — context is required, not optional

| | detection | false positives |
|---|---|---|
| diff only | 1/3 | 2 |
| perfect context (oracle) | **3/3** | **1** |

### Retrieval comparison — 13-file corpus with adversarial distractors

| mode | detection | false positives | right file retrieved |
|---|---|---|---|
| none | 1/3 | 2 | — |
| symbol (lexical) | 2/3 | 2 | 5/6 |
| oracle (perfect context) | **3/3** | **1** | — |

---

## Corrections to earlier claims

Both of these were recorded from runs later found to be invalid (API failures
scored as "found no bugs"). They were wrong, and the corrected versions are more
interesting.

**Was: "context does not improve detection, it only reduces false alarms."**
Wrong. That came from runs where the critic was broken or disabled. With a
working critic, blind detection collapses to 1/3 — because the critic correctly
refuses unsupported cross-file guesses, and says so explicitly: *"the claim
depends on external callers but no repository context is provided to
substantiate that any code checks for `err.code === 'ECONNABORTED'`."* Context
restores it to 3/3.

The real finding: **retrieval and critique are complementary.** Critique alone
makes the agent nearly blind to cross-file bugs. Retrieval alone lets it
speculate. Together: 3/3 detection with 1 false positive.

**Was: "symbol search matched perfect context, so the vector database has no
headroom and was not built."** Wrong. Symbol search scores 2/3, between blind
(1/3) and oracle (3/3). It leaves one detection on the table.

The miss is precisely the case predicted to be beyond lexical reach:
`shouldRetry.js` never imports `timeout.js` and shares one token with the diff
(`'ECONNABORTED'`), while the distractor `xhr.js` shares that literal plus
`timeout` and `err`. Exact matching structurally cannot rank it first.
**Embeddings now have a measured target to beat rather than a foregone
conclusion.**

---

## Open questions with a clear next step

**The remaining false positive is probably a fixture flaw, not an agent error.**
The agent says `normalizeHeaders` throws when passed `undefined` — and it does.
The "safe" fixture shows one caller that defaults the value, but nothing proves
other callers do. The function really is fragile. The fixture asserts safety it
does not demonstrate.

**Retrieving two files may be worse than retrieving one.** Symbol search found
the right file for the first safe fixture and still produced a false positive;
the oracle, handed exactly one file, did not. `k=2` adds a distractor. Try `k=1`.

**Verbosity.** On the race-condition fixture the agent emitted five comments;
two are thin. Detection is good, signal-to-noise on a single busy diff is not
yet measured.

---

## Method notes

- Rate limits are per-model, per-minute *and* per-day. All calls retry on 429,
  honouring the delay the API asks for. Before this, a rate-limited call returned
  no comments and scored as "found no bugs".
- Measurement is expensive: one fixture is a draft call plus a critic call per
  comment plus a repro call per survivor. That is what exhausted a 200k daily
  budget in one session.

## Honest limits

- 8 self-contained and 3 cross-file cases. Still small.
- Fixtures are synthetic and written by the same person who tuned the agent —
  and one of them has now been shown to assert safety it does not demonstrate.
- Embedding retrieval is implemented but unmeasured.
- False-positive rate on real pull requests rests on a single PR.
- Single runs, not medians. Differences of 1 should not be over-read.

---

## For the README

The method is the result. Four times, careful measurement overturned the
obvious answer — and twice it overturned a conclusion recorded here earlier:

1. The first agent produced 3 comments and 0 real findings, restating the
   author's own fix as a recommendation.
2. The scorer was wrong in both directions, inflating and then deflating results.
3. An API outage scored identically to a bad reviewer, because a failed call and
   a clean review both returned nothing. Three separate wrong diagnoses followed
   before the real cause surfaced.
4. Retrieval and critique were each judged separately and both judgments were
   wrong; they only make sense as a pair.
