# Requirements — v1 (DRAFT, not yet read back)

What must be observably true of viki-agent. Changes only with the client; a change is a new version. Drafted
2026-11-10 by Claude Opus 5.5 from the client's words. *Tell us what is wrong with it.*

Client: Warren MacEvoy.

## Mission

- **MISSION-1** *(judged)* A really good librarian for a project, armed with viki, and guidelines for using viki.
  The client, 2026-11-10: "viki-agent is a self-improvement project to make a really good librarian and guidelines
  of how to use viki." Judge: the client *(inferred)*.

## Glossary

| Term | Meaning |
| ---- | ------- |
| Librarian | The agent that keeps a project's library in viki: outlines, entries, concept maps. Its judgment, not viki's. |
| Outline | A document's concepts as nested nodes with line ranges (viki's OL). |
| Entry | A node's summary and the questions it answers, by the librarian. |
| Concept map | Concepts across documents and how they relate (viki's LIB-2, not built). |
| Drift | Places that state one concept and no longer agree. |

## Requirements

Invented numbers are marked *(invented)*.

- **LA-1** A project can vendor the librarian: copy a directory in, import its guide from the project's agent
  file, and point it at a viki diary. Nothing in the project is changed otherwise.
- **LA-2** The librarian runs unattended. No person takes part in outlining, writing entries, or updating either.
- **LA-3** It keeps its library current as files change, at a cost that grows with the change, not the file
  (GUIDE G-5).
- **LA-4** It keeps every earlier outline, entry and map readable, so a change in meaning can be traced (G-6).
- **LA-5** *(not built)* It maps concepts across documents, and reports drift: a concept whose statements no
  longer agree. It points at where to look, and does not decide which is right.
- **LA-6** Every change to the librarian's prompts or protocol is tested before it is kept: a plan with what
  would count against it, written first; questions independent of their answers; a held-out set read once; a
  ledger of every run (G-7 to G-11).
- **LA-7** Its cost is measured and reported per run, from the model CLI's own figure.

## Non-goals

- Storing, searching, syncing or forgetting: that is viki's.
- Deciding which of two drifting statements is right: that belongs to the project's owner.

## Not yet answered

1. **Where the librarian's code lives.** Today it is in viki's `tools/vk.py` (outline, librarian, embed, ask).
   viki's SHAPE-7 puts judgment outside viki, which argues for moving the prompts and protocols here and leaving
   viki's host the mechanics. Proposal: move it, once the client says so.
2. **What a drift report looks like,** and how it is tested (a planted disagreement, as `../compaction` plants
   claims).
3. **A question set that is independent of the answers,** large enough to tell a 0.05 change in MRR from chance
   *(invented)*: from whom, and kept how.
4. **The model per task:** Sonnet for outlines and entries now; whether a cheaper model can do the update step.
