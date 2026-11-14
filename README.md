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
- **Trials live elsewhere:** in `../viki-agent-self-improvement`, which is private because the mining runs on
  private data (a project's files, its transcripts, its people's questions). What a trial finds reaches this
  repository only as a conclusion that changes something: a guideline, a requirement, a FINDINGS line with numbers
  and no private text.
- `skills/vk/SKILL.md`: the `/vk` Claude Code skill, which asks a diary by meaning (`la.py ask`), by words, or
  exactly, and keeps it filed. Install by linking it: `ln -s "$PWD/skills/vk" ~/.claude/skills/vk`. It names
  `vk.py` and `la.py` by absolute path on the machine it was written on; change those two lines on another.
- `REQUIREMENTS_v1.md`, `FINDINGS.md`, `QUEUE.md`: the working set, in SE1's form. The requirements are a draft, not yet read
  back.
- `AGENTS.md` (SE1 v1.7) and `AGENTS-DM.md` (DM1 v1.3): copied unedited from `../viki`, loaded by `CLAUDE.md`.
  This is a minimal adoption: no `se`/`dm` tools and no QUICKREF yet.

## The librarian

`librarian/la.py`: `outline`, `librarian`, `embed` and `ask`, moved here from viki's `tools/vk.py` on 2026-11-10
(Warren: "move the librarian code to viki-agent"; viki `1215fe2` is the last commit that has it). It needs viki
beside this repository, or `$VIKI_TOOLS` pointing at viki's `tools/`: viki's built store library
(`sh core/test/store-check.sh` in viki builds it), and, for vectors, its embedder (`tools/build-embed.sh`) and the
pinned model (`$VIKI_MODEL_DIR`).

```sh
python3 ../viki/tools/vk.py --store D --keyfile K ingest-git PROJECT     # viki: the store
python3 librarian/la.py --store D --keyfile K outline --repo NAME       # concepts, by Sonnet
python3 librarian/la.py --store D --keyfile K librarian --repo NAME     # entries per node; updates from the diff
python3 librarian/la.py --store D --keyfile K embed --repo NAME         # vectors of nodes and questions
python3 librarian/la.py --store D --keyfile K ask "a question in your own words"
python3 librarian/test_la.py                                            # 4 tests, fake models
```

## Vendoring

Not yet defined. The intended shape: `GUIDE.md` copied into a project and imported by its `CLAUDE.md`, as SE1's
`AGENTS.md` is, and `librarian/` beside it, with viki found through `$VIKI_TOOLS`.
