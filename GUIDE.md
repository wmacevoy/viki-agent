# Using viki as a librarian

Guidelines for an agent that keeps a project's library in viki. Each names the finding behind it, so it can be
argued with. Drafted 2026-11-10 by Claude Opus 5.5 with Warren MacEvoy, from one project's evidence (viki's own
repository); none has been tried on a second project. Findings cited as "viki FINDINGS" are in `../viki/FINDINGS.md`,
newest first, under the dates given.

## The unit of meaning

- **G-1. The outline node is the unit.** Outline each document into concepts (`vk.py outline`) and search,
  embed and describe by node. Do not cut text by size: windows of a fixed size were measured and set aside (viki
  FINDINGS, 2026-11-10, chunking and outlines). An outline is already the librarian's work: a model had to
  understand the text to divide it.
- **G-2. Send a document whole; dividing it is the librarian's task.** No splitting by size, however large: a
  244 KB file was outlined in one call, into 174 nodes (Warren: "do not split large files; that's the librarians
  task").

## What the librarian writes

- **G-3. For every node, a summary and the questions it answers, mostly in the asker's words.** The words a
  person searches with are rarely the document's. With entries on outline nodes, the right file ranked first for 9
  of 26 independent questions, against 3 for whole files without a librarian (file MRR 0.482 against 0.170; viki
  FINDINGS, 2026-11-10). A question nobody anticipated is still missed: "every laptop redoing work a colleague's
  machine already finished" found nothing.
- **G-4. One vector per question, not one per entry.** Embedded whole, an entry's summary drowned its questions,
  and the right entry ranked 2,706th. Its own question, embedded alone, ranked first.

## Keeping it current

- **G-5. Update from the diff.** The outline is updated from the previous outline and the changes. Entries are
  asked for only where a node's own text changed, or the node is new. The rest carry over, and the entries of
  nodes that went are retired. Over 13 file updates this cost about a quarter of a whole-file update, with the same
  retrieval (viki FINDINGS, 2026-11-10).
- **G-6. Old maps stay readable.** Every outline and entry supersedes the one before; nothing is edited (viki's
  SHAPE-2). A change in meaning can be traced by reading the chain.

## Claims about the librarian

- **G-7. Before concluding, check that the test exercised the design asked for.** A flat librarian on fixed
  windows was measured, and its result reported as a finding about the librarian. It was wrong guidance (Warren:
  "that k3 meant all you just tested did not matter and gave bad guidance").
- **G-8. Write down what would count against a claim before running, and keep the run in a ledger.** A defect
  found after seeing results makes the rerun post hoc. Say so.
- **G-9. Questions must be independent of their answers.** A question whose answer was written in response to it,
  or that quotes it, tests that history, not retrieval. Keep the evaluation's own files out of the corpus: a query
  file in the corpus scored 25 of 28 at rank 1 until it was removed.
- **G-10. Do not re-run a concluded experiment as an arm.** An arm earns its place only if its outcome could
  change what is done next.
- **G-11. Compare from one starting state.** Two whole-file runs gave one document 118 and 174 nodes, and that
  variance moved scores more than the method under test.

## Drift (not yet built)

- **G-12. Map concepts across documents, then watch the map.** A requirement, the design that answers it and the
  code that implements it are one concept in three places. When one changes and the others do not, the librarian
  points at the gap, with where to look; it does not resolve it. Nothing here has been measured yet.
