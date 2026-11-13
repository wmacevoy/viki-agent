# FINDINGS

What was learned the expensive way, newest first. Each entry ends with what it changed, or why nothing.

## 2026-11-13 — Unmixing the query did not beat cosine

Warren: "maybe cosine match is wrong. maybe querys should me more like inverse spectroscopy." The vector leg was
re-ranked by non-negative least squares: the query rebuilt from its 200 nearest vectors, each node scored by its
weight (the λ = 0 case of Non-negative Elastic Net decoding, arXiv 2606.17910). Plan and counter-results written
first; same store and 26 DEV questions as the 0.482 result, which the control reproduced exactly. Vector leg alone,
file MRR: cosine 0.380, unmixing 0.294, 6 wins and 12 losses (p = 0.24). Fused with bm25: 0.482 against 0.488, 9
and 7. Pools of 50, 100 and 400 (exploratory) all lost. No model calls. The first run scored nothing: a check found
the harness re-embedding the wrong node of a whole-file span, and it was fixed before any number was seen.

**What it changed:** cosine stays. Not tried: a sparsity penalty (λ > 0), or unmixing into node vectors only
rather than the librarian's question vectors; the paper's gains also came partly from embeddings trained for it.

## 2026-11-10 — The librarian's code and trials moved here from viki

`librarian/la.py` and `test_la.py` (4 tests, each seen to fail on a break after the move), from viki `1215fe2`.
The trial `2026-11-10-librarian` moved with them, then on to the private `../viki-agent-self-improvement` (Warren:
"a private data-mine problem ... and a current public definition"), because its questions came from private
sessions. In viki, `tools/vk.py` kept the store's mechanics and the
principals' grants, and lost its one model call, `ask_judge`. `../compaction`'s `hooks/viki_recall.py` had used
that call, and now carries its own copy. Both suites pass: viki 62 C and 10 host tests, gate 54 green; viki-agent
4 of 4.

**What it changed:** this repository holds no trial data. The trials import `la` from here.

## 2026-11-10 — Where this project starts: the librarian's evidence so far is in viki

The librarian was built and measured in `../viki` before this project existed. Those entries stay there, in viki's
`FINDINGS.md` under 2026-11-10. Their data (plans, harnesses, ledger, runs) is now in the private
`../viki-agent-self-improvement`:

- The librarian finds the right file far more often than no librarian: file MRR 0.482 against 0.170, on 26
  independent questions (post hoc, DEV).
- An update from the diff retrieves as well as a whole-file update, at about a quarter of the cost.
- The first librarian ignored the outline design, and its conclusion was wrong guidance. That episode gave G-7.
- Outline-only against outline-plus-entries: not shown. Warren's correction: an outline is already the librarian's
  work, so "outline only" is not a no-librarian arm.

**What it changed:** `GUIDE.md` G-1 to G-11 come from these. Every number is from one repository.
