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

### Real pull requests (axios/axios, no retrieval — diff only)

The first test on code neither the author nor the agent wrote. Note the real-PR
path runs **without** retrieval, which today's cross-file result predicts will
cost detection; it is still the right test for false alarms.

| PR | outcome |
|---|---|
| #11118 fix(interceptors) | complete, **0 comments** |
| #11121 fix(xhr) progress | complete, **0 comments** |
| #11141 fix: harden runtime option handling | incomplete (1 failed call), 1 substantive finding — see below |
| #11109, #11096 | incomplete, refused to report |

**2 complete reviews, 0 false alarms.** A small but real number: these PRs were
reviewed and merged by axios maintainers, so silence is the correct answer.

The finding on #11141, which survived the critic:

> `toSafeFlatObject` copies property values using `thing[prop]` instead of
> `current[prop]`; if a prototype defines an accessor that throws or has side
> effects when accessed via the derived object, this will throw or execute
> unintended code.

**Verified against the source. Verdict: real observation, wrong diagnosis.**

The code does do this:

```js
const props = Object.getOwnPropertyNames(current);  // names from current
...
result[prop] = thing[prop];                         // value from thing
```

Enumerating one object and reading from another is a genuine inconsistency and
fair to flag. But the agent's reasoning does not hold up:

- For plain data properties there is no difference — `thing[prop]` resolves up
  the prototype chain to the same value.
- For accessors it does differ, but only in the receiver: `thing[prop]` runs the
  getter with `this === thing`, `current[prop]` with `this === current`.
- **The proposed fix does not prevent what it claims to.** The agent warned about
  getters that throw or have side effects and suggested `current[prop]` — which
  invokes the getter just the same.

The sharper finding, which neither the code nor the agent reached: a function
hardening against prototype pollution executes arbitrary getters simply by using
`[]` access. `Object.getOwnPropertyDescriptor` would let it copy or skip
accessors without running attacker-controlled code.

Recorded as a **partial hit**: correct reading of the code, incorrect reasoning
about consequences, unusable fix. Not posted to the PR — the comment as written
would be wrong. This is the most useful single data point in the file, because
it shows what "the agent found something" is actually worth without a human
checking it.

The critic was visibly working on real code too, rejecting one claim with:
*"the diff shows the Object.prototype modifications are deleted in finally
blocks, so the claim of leaking into other tests is false."*

### Two problems real PRs exposed that fixtures never could

**Requests were too large.** The free tier allows 8,000 tokens per minute; the
code packed up to 50,000 characters (~14k tokens) into one call, so every
substantial PR returned 413 — and 413 is not transient, so retrying wasted time.
Diffs are now reviewed in ~11,000-character batches. Better than the old
truncation, which silently reviewed a prefix.

**The product path had the same silent-failure bug as the harness.** On the
first attempt, four of five PRs failed to be read and the agent announced "no
issues found" for every one, printing the comment it would have posted. The
MEASUREMENT INVALID guard had been added to the *test* code and not to the code
that talks to GitHub — the wrong way round, since only one of those can post a
false review in public. Now: REVIEW INCOMPLETE, refuse to post, non-zero exit.

**Batching fragments context.** The critic rejected a claim as relying on
`fromDataURI.js` "not shown" — but that file *was* in the PR, in batch 4, while
the code referencing it was in batch 8. Splitting to fit the token limit creates
a new blind spot. Unsolved; grouping related files into the same batch is the
obvious next step.

**Documentation was being reviewed.** One batch of nine was `AGENTS.md`,
`copilot-instructions.md` and a changelog — roughly 11% of a daily token budget
spent reviewing prose. Now filtered.

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
