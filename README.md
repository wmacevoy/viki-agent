# viki-agent

A librarian for a project, armed with [viki](../viki) as its tool, and the work that makes it a good one.

Warren MacEvoy, 2026-11-10: "i think we found viki -> the librarian armed with viki the tool. make a sibling
project, viki-agent, which can be vendored on a project that needs a librarian. once the concepts are mapped the
librarian can help to manage drift. ... viki-agent is a self-improvement project to make a really good librarian
and guidelines of how to use viki."

**viki** keeps, searches, merges and forgets. It holds no opinions: judgment lives outside it (viki's SHAPE-7).
**The librarian** is that judgment. It outlines each document into concepts, writes what each concept answers in a
reader's words, keeps that current as files change, and maps how concepts relate. With the map in place it can point
at drift: a requirement, its design and the code that implements it no longer saying the same thing.

## What is here

- `GUIDE.md`: how to use viki as a librarian. **This is the part a project vendors.** Each guideline names the
  finding behind it.
- `trials/`: one directory per trial: what was asked, what would count against the claim (written first), the
  harness, and the results. What a trial finds reaches `GUIDE.md` only as a conclusion that changes something.
- `REQUIREMENTS_v1.md`, `FINDINGS.md`: the working set, in SE1's form. The requirements are a draft, not yet read
  back.
- `AGENTS.md` (SE1 v1.7) and `AGENTS-DM.md` (DM1 v1.3): copied unedited from `../viki`, loaded by `CLAUDE.md`.
  This is a minimal adoption: no `se`/`dm` tools and no QUICKREF yet.

## Where things are today

The librarian's code is still in viki: `vk.py outline`, `librarian`, `embed` and `ask` (viki's `tools/vk.py`,
commit `4697c8f` on viki's `dogfood` branch), with its experiments in viki's `test/librarian/`. Whether it moves
here is open: see `REQUIREMENTS_v1.md`, Not yet answered 1.

## Vendoring

Not yet defined. The intended shape is `GUIDE.md` copied into a project and imported by its `CLAUDE.md`, as SE1's
`AGENTS.md` is, plus the librarian's commands. That depends on Not yet answered 1.
