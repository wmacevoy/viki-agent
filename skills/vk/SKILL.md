---
name: vk
description: Search a viki diary (an encrypted mirror of git repositories, their history and conversations, filed by a librarian into topics) by meaning, by words, or exactly. Use when the user types /vk, or when a task asks where a concept lives, what else touches it, or where something used to be, in a repository that has a viki diary.
---

# /vk — ask the viki diary

A viki diary mirrors git repositories: every file version, check-in and branch, and optionally conversations.
A librarian (viki-agent) then files each file into topics: an outline of its concepts, and for each one a summary
and the questions it answers in a reader's words. Once filed, the diary answers what the tree cannot:

- **by meaning:** "what handles a stale count?" finds the code even when it never uses those words;
- **by topic:** a hit is the section it is in, with the section's titles, not a line out of context;
- **across history and repositories:** past versions, deleted files, every ingested repository at once.

**Usage:** `/vk [STORE KEYFILE] QUERY`

## Find the diary

1. If the arguments start with two paths, they are STORE and KEYFILE.
2. Otherwise use `$VIKI_STORE` and `$VIKI_KEYFILE` if they are set.
3. Otherwise ask the user which diary. **Never run `keygen` or create a diary unless the user asks.**
   A keyfile is a secret: refer to it by path, never print or copy its contents.

**Setting the two variables for one project.** A machine holds several diaries, one per project, so do not put
them in a shell profile: every project's `/vk` would then use the same diary. For Claude Code, put them in the
project's `.claude/settings.local.json`, which applies only to sessions started there and is not committed:

```json
{ "env": { "VIKI_STORE": "/abs/path/store", "VIKI_KEYFILE": "/abs/path/key" } }
```

Write the paths absolute. A session reads this at start, so it takes effect in the next one. When the user asks
for a new diary and names no place, keep its key outside every repository, so that it cannot be committed:
`~/.viki/PROJECT/key` (mode 600, in a mode-700 directory), with the store beside it.

```sh
VK="python3 /home/paradox/projects/viki/tools/vk.py --store $STORE --keyfile $KEYFILE"
LA="python3 /home/paradox/projects/viki-agent/librarian/la.py --store $STORE --keyfile $KEYFILE"
```

## Asking

| Need | Command |
| --- | --- |
| what the diary holds, and as of which commit | `$VK coverage` |
| **by meaning**: the concept, in any words | `$LA ask "QUESTION" [--k N]` |
| by words, ranked, returning the topic each hit is in | `$VK find "WORDS" --outlines vk.judge.sonnet [--repo NAME] [--k N]` |
| every exact occurrence, with its topic | `$VK grep "TEXT" --outlines vk.judge.sonnet [--repo NAME]` |
| also past versions (where it used to be) | add `--all` to `find` or `grep` |
| the current check-ins of a repository | `$VK heads NAME` |

Start with `coverage` once per session; "nothing ingested" (exit 1) means the diary is empty.

- **`ask`** is for "where is the code about X" and "what else touches X". It fuses bm25 and vector search over
  outline nodes and the librarian's questions, and returns each node as `path  bytes LO-HI`: read that range.
  **Read its last line, `legs:`.** Without the filing below it still exits 0, but answers from bm25 over whole
  files and says `blind: vector`: that is word search, not meaning. Say so, or file first.
- **`grep`** is exact and exhaustive over what is covered: use it for "is X used anywhere", never `ask`.
- **`find`** is ranked words; it may miss a passing mention.

## Keeping it filed

The diary mirrors git, so what is not committed is not in it. After commits, in this order:

1. `$VK ingest-git REPO_DIR [--name NAME]`: no model calls; adds only what is new.
2. `$LA outline [--repo NAME]`: a Sonnet call per changed file; skips what is already outlined.
3. `$LA librarian [--repo NAME]`: a Sonnet call per changed file; updates from the diff.
4. `$LA embed [--repo NAME]`: local, no model calls.

**Steps 2 and 3 spend money.** Measured in viki-agent's 2026-11-10 trial: about $0.05 per file to outline and
$0.10 for the librarian, so about $0.15 per file, or $48 for 318 files. Updating from a diff cost about a quarter
of that. **Before filing more than a few files, say the file count and estimated cost, and ask.** `--limit N`
caps the calls in one run; `--skip PATH` keeps a file or directory out, for anything private or generated.

## Read the exit status, not just the output

- **0** found or done. **1** searched and not found. **3** blind: the diary does not hold what was asked (a
  repository never ingested). **2** error. `ask` reports a missing leg on its `legs:` line instead.
- **Blind is not "not found".** Say "the diary does not cover that", then use the working tree.
- Each `find`/`grep` hit is marked current, superseded, or one head of a fork. Superseded versions are hidden
  unless `--all`, and the output says how many were hidden.

## Reporting

- Give the hit's repository, path and range or commit, and the coverage the answer rests on.
- Write to the diary only by the four filing commands. Do not run `forget-chat` or any erase unless the user
  asks.
