# Sentinal — Evaluation Log

Every prompt or model change gets measured on both axes. Recall alone is
gameable by a chatty agent; precision alone is gameable by a silent one.

**Recall** — `python -m src.review --selftest` against `src/fixtures.py`
(4 diffs with planted, documented bugs). Record the count you verified by
reading the output, not the heuristic number.

**Precision** — run against merged PRs from `axios/axios` that were reviewed
and merged clean. Any comment on these is presumed a false positive unless you
can defend it after reading the code.

---

## Results

| # | Change | Model | Recall (verified) | FP on clean PRs | Notes |
|---|---|---|---|---|---|
| 1 | Initial prompt | llama-3.3-70b-versatile | not measured | 3 FP on 1 PR | Restated the PR's own fix as a finding; generic "add tests"; style nit |
| 2 | Rubric rewrite + `failure_scenario` required, enforced in code | llama-3.3-70b-versatile | 1/4 (heuristic said 2/4) | 0 FP on 1 PR | Precision fixed. Heuristic scorer over-reported — signals were too generic and matched "unhandled promise rejection" for the missing-`await` bug |
| 3 | Signals tightened, token cap added | llama-3.3-70b-versatile | 2/4 | 0 FP on 1 PR | Honest baseline |
| 4 | Model swap only (prompt unchanged) | openai/gpt-oss-120b | 4/4 | 0 FP on 1 PR | Capability, not prompting. Needs a larger clean-PR sample to confirm precision |

---

## Open items

- [ ] Precision sample is n=1. Run 5 more merged, cleanly-reviewed PRs before
      quoting a precision number anywhere.
- [ ] Add fixtures for bug classes not yet represented: race condition, resource
      leak, incorrect error swallowing, auth check on the wrong object.
- [ ] Fixtures are all single-file and self-contained, so they cannot measure
      whether retrieval (Phase 3) helps. Cross-file fixtures needed: a change
      that is only wrong given how the function is called elsewhere.

---

## Method notes for the README

The interesting story here is not the final number — it is that the first
version scored 3 false positives and 0 real findings, and that measuring
recall separately caught a scoring bug that was inflating the result. State
both. "I built an eval, the eval was wrong, I fixed the eval" is a stronger
signal than any headline metric.
