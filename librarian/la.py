#!/usr/bin/env python3
"""la.py -- the librarian, armed with viki (viki-agent: README.md, GUIDE.md, REQUIREMENTS_v1.md).

  la.py --store DIARY --keyfile KEY outline [--repo NAME] [--judge sonnet|haiku] [--history] [--limit N] [--jobs N]
                                             [--skip PATH] [--redo PATH] [--judge-cmd CMD]
  la.py --store DIARY --keyfile KEY librarian [--repo NAME] [--model sonnet|haiku] [--judge J] [--limit N] [--jobs N]
                                               [--skip PATH] [--judge-cmd CMD]
  la.py --store DIARY --keyfile KEY embed [--repo NAME] [--judge J] [--skip PATH] [--only PATH]
  la.py --store DIARY --keyfile KEY ask TEXT [--k N] [--judge J] [--no-entries]
  (--plaintext in place of --keyfile says an unencrypted diary was meant)

viki keeps, searches and forgets; this is the judgment (viki's SHAPE-7). It outlines each file whole into concepts
(viki's OL), writes for every node a summary and the questions it answers in a reader's words (LA, LIB-1),
updates both from the diff when a file changes, embeds nodes and questions with viki's pinned model, and searches
by node. Moved here from viki's tools/vk.py on 2026-11-10 (viki 1215fe2). viki is found at $VIKI_TOOLS, else
../viki/tools beside this repository. The principals it writes as, and their grants, stay in vk.py, so that viki's
own searches honour what it writes (R-4a).
Exit status: 0 done, 1 not found, 3 blind, 2 error.
"""
import argparse
import collections
import difflib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VIKI_TOOLS = os.environ.get("VIKI_TOOLS") or os.path.join(HERE, "..", "..", "viki", "tools")
sys.path.insert(0, VIKI_TOOLS)
from vk import (GRANTS, JUDGES, LIBRARIANS, PRINCIPAL, RIGHTS, KeyError_, now_utc, rank_of,  # noqa: E402
                read_keyfile)
import vkstore as vk  # noqa: E402

# ---- outlines (OL), asked of a judge outside viki (SHAPE-7) ----

# The protocol measured in test/chunking/outline.py (FINDINGS 2026-11-10): a first outline by concept,
# not size; after that, the previous version and its outline, with a preference to keep it.
FIRST = """Below is one version of the file {path}, with each line numbered.

Outline it the way a reader would understand it: the concepts it contains, nested as deeply as the
content's own structure goes. For code, that might be groups of related functions or types, then
each function or type, then its distinct parts if it has any. For prose, sections, then
sub-sections, then topics. Every node is one concept. Do not split or merge anything because of its
length.

Answer with only JSON: a list of top-level nodes, each
{{"title": "<a short name for the concept>", "start": <first line>, "end": <last line>, "children": [<nodes>]}}.
Children lie inside their parent and do not overlap each other. Lines that belong to no concept, such
as blank lines between them, may be left out.

{numbered}"""

CARRY = """Below are the outline of the previous version of the file {path}, and the changes from it to the new
version as a diff. In the diff, each line shows a line number and a mark: "+" a line of the new version that is new,
"-" a line of the previous version that was removed (its number is the previous version's), " " an unchanged line
of the new version, shown for context. The new version has {n} lines; lines not shown are unchanged, shifted by the
lines added or removed above them.

Write the outline of the new version. Prefer to leave the outline the same: keep each node's title, its place and
its children, and move its line numbers to where that text now is. Change the outline only where the changes alter
structure (a concept added, removed, moved, split or merged) or rewrite text whole cloth. Do not split or merge
anything because of its length.

Answer with only JSON: the whole outline of the new version, a list of top-level nodes, each
{{"title": "<a short name for the concept>", "start": <first line>, "end": <last line>, "children": [<nodes>]}}.
Line numbers are the new version's.

Outline of the previous version (the previous version's line numbers):
{outline}

Changes:
{diff}"""


def numbered_diff(a, b):
    """The diff of two versions' lines (str, no endings), numbered: the new version's numbers for added and
    context lines, the previous version's for removed ones. Only the hunks, with 3 lines of context: an
    update costs about the size of the change, not of the file (FINDINGS 2026-11-10)."""
    out = []
    for group in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_grouped_opcodes(3):
        out.append("@@")
        for op, a1, a2, b1, b2 in group:
            if op == "equal":
                out += [f"{j + 1} {b[j]}" for j in range(b1, b2)]
            if op in ("delete", "replace"):
                out += [f"{i + 1}- {a[i]}" for i in range(a1, a2)]
            if op in ("insert", "replace"):
                out += [f"{j + 1}+ {b[j]}" for j in range(b1, b2)]
    return "\n".join(out)


def changed_new_lines(a, b):
    """The new version's line numbers (1-based) that are new, or that border a removal."""
    out = set()
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op in ("insert", "replace"):
            out.update(range(b1 + 1, b2 + 1))
        if op == "delete":
            out.update({max(1, b1), b1 + 1})
    return out


def str_lines(body):
    return [ln.rstrip("\n").rstrip("\r") for ln in body.decode("utf-8", "replace").split("\n")]



def text_lines(body):
    """The body's lines with their endings, or None if it is not text."""
    if b"\0" in body:
        return None
    try:
        body.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return body.splitlines(keepends=True)


def numbered(lines):
    return "".join(f"{i+1}\t{ln.decode('utf-8')}" for i, ln in enumerate(lines))


def line_tree(answer, n_lines):
    """The judge's outline as nested (title, start, end, children) in lines, clipped to the file and
    to each parent, siblings that overlap dropped. None if no JSON list is in the answer."""
    m = re.search(r"\[.*\]", answer, re.S)
    if not m:
        return None
    try:
        raw = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None

    def clean(nodes, lo, hi):
        out, last = [], lo - 1
        good = [n for n in nodes if isinstance(n, dict)]
        def first(n):
            try:
                return int(n.get("start", 0))
            except (TypeError, ValueError):
                return 0
        for n in sorted(good, key=first):
            try:
                s, e = int(n["start"]), int(n["end"])
            except (KeyError, TypeError, ValueError):
                continue
            s, e = max(s, lo, last + 1), min(e, hi)
            if s > e:
                continue
            kids = n.get("children") if isinstance(n.get("children"), list) else []
            out.append((str(n.get("title", "")).strip() or "(untitled)", s, e, clean(kids, s, e)))
            last = e
        return out
    return clean(raw if isinstance(raw, list) else [], 1, n_lines)


def to_bytes(tree, lines):
    """Line ranges (1-based, inclusive) as OL-1 byte ranges (lo, hi exclusive)."""
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    return [{"title": t, "lo": starts[s - 1], "hi": starts[e], "children": to_bytes(k, lines)}
            for t, s, e, k in tree]


def to_lines(nodes, lines):
    """A stored outline back in lines, for the judge."""
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))

    def line_of(off, end):
        import bisect
        i = bisect.bisect_right(starts, off) if not end else bisect.bisect_left(starts, off)
        return max(1, min(len(lines), i))
    return [{"title": n["title"], "start": line_of(n["lo"], False), "end": line_of(n["hi"], True),
             "children": to_lines(n.get("children") or [], lines)} for n in nodes]


def ask_judge(cmd, prompt):
    import shlex
    import tempfile
    with tempfile.TemporaryDirectory(prefix="vk-judge-") as empty:   # the judge sees only the prompt
        r = subprocess.run(shlex.split(cmd), input=prompt, capture_output=True, text=True, cwd=empty,
                           timeout=1200)
    if r.returncode:
        raise vk.VkError(f"judge failed ({r.returncode}): {r.stderr.strip()[:200]}")
    return r.stdout


def outline_answer(judge, ask, r, prev):
    """Ask the judge for r's outline: (tree in lines, lines), or why not. Calls nothing in the store, so
    several run at once. A file is never cut: how a large document divides is the judge's to say (Warren,
    2026-11-10: "do not split large files; that's the librarians task")."""
    lines = text_lines(r.body)
    if lines is None:
        return "not text"
    if not lines:
        return "empty"
    path = r.akey.decode("utf-8", "replace")
    if prev is not None:   # the previous outline and the diff; neither version whole
        plines = text_lines(prev[0].body) or []
        prompt = CARRY.format(path=path, n=len(lines), outline=json.dumps(to_lines(prev[1], plines), indent=1),
                              diff=numbered_diff(str_lines(prev[0].body), str_lines(r.body)))
    else:
        prompt = FIRST.format(path=path, numbered=numbered(lines))
    tree = line_tree(ask(prompt), len(lines))
    return (tree, lines) if tree is not None else "unparseable"


def outline_write(store, judge, r, prev, got):
    """Write an answer from outline_answer: 'written', or why not."""
    if isinstance(got, str):
        return got
    tree, lines = got
    key = vk.outline_key(r.id, judge)
    body = json.dumps(to_bytes(tree, lines), ensure_ascii=False).encode()
    derived = [r.id] + ([prev[2]] if prev is not None else [])
    t = now_utc()
    try:
        store.put(b"outline", key, body, ts=t.isoformat().encode(), rank=rank_of(t.timestamp()),
                  reference=r.id, derived_from=derived, chain=True)   # a redo supersedes (OL-2), never forks
    except vk.VkError as e:
        return f"refused: {e}"
    return "written"


def previous_outline(store, judge, r):
    """The judge's outline of a version r supersedes: (that version, its nodes, the outline's id)."""
    for pid in r.supersedes:
        p = store.get(pid)
        if p is None or p.kind != b"file":
            continue
        key = vk.outline_key(pid, judge)
        st, body = store.current(key)
        if st == vk.OK and body:
            return (p, json.loads(body), store.head_id(key))
    return None


def file_versions(store, repo, history):
    """File versions to outline: the current ones, or with history every version, in arrival order,
    which puts a version after the one it supersedes, so that one is outlined first."""
    prefix = repo.encode() + b"/" if repo is not None else b""
    out = []
    for r in store.walk():
        if r.kind != b"file" or r.erased or not r.akey.startswith(prefix):
            continue
        if not history and not store.standing(r.akey, r.id)[0]:
            continue
        out.append(r)
    return out


def skipped(akey, skip):
    """akey starts with one of the skip prefixes (a file or a directory, as 'repo/path')."""
    a = akey.decode("utf-8", "replace") if isinstance(akey, bytes) else akey
    return any(a == s or a.startswith(s.rstrip("/") + "/") for s in skip)


def cmd_outline(store, repo, judge_name, history, limit, cmd, skip=(), jobs=4, redo=()):
    """redo: files whose current version is outlined again, from its predecessor's outline, though it has one."""
    model, judge = JUDGES[judge_name]
    cmd = cmd or f"claude -p --model {model} --tools \"\" --no-session-persistence --output-format text"
    tally, due = collections.Counter(), []
    for r in file_versions(store, repo, history):
        if skipped(r.akey, skip):
            continue
        st, _ = store.current(vk.outline_key(r.id, judge))
        if st in (vk.OK, vk.FORKED) and not skipped(r.akey, redo):
            tally["already outlined"] += 1
            continue
        lines = text_lines(r.body)
        if not lines:   # nothing to ask: these do not count against --limit
            tally["not text" if lines is None else "empty"] += 1
            continue
        if limit is not None and len(due) >= limit:
            tally["left for a later run"] += 1
            continue
        due.append(r)
    calls = 0

    def counted(prompt):   # parts make more calls than files; this counts calls
        nonlocal calls
        calls += 1
        return ask_judge(cmd, prompt)

    def answer(r, prev):
        try:
            return outline_answer(judge, counted, r, prev)
        except (vk.VkError, subprocess.TimeoutExpired) as e:
            return f"judge failed: {e}"

    def record(r, prev, got):
        why = outline_write(store, judge, r, prev, got)
        if why != "written" and why not in ("not text", "empty"):
            print(f"  {r.akey.decode('utf-8', 'replace')}: {why}", file=sys.stderr)
        tally["refused" if why.startswith("refused") else "judge failed" if why.startswith("judge failed") else why] += 1

    if history or jobs <= 1:   # carrying forward needs each previous outline written first
        for r in due:
            prev = previous_outline(store, judge, r)
            record(r, prev, answer(r, prev))
    else:
        import concurrent.futures
        pre = [(r, previous_outline(store, judge, r)) for r in due]
        with concurrent.futures.ThreadPoolExecutor(jobs) as pool:
            got = list(pool.map(lambda rp: answer(*rp), pre))
        for (r, prev), g in zip(pre, got):
            record(r, prev, g)
    print(f"outlines by {judge.decode()}: " + ", ".join(f"{n} {k}" for k, n in sorted(tally.items())) +
          f"; {calls} judge calls")
    return 0


# ---- vectors (Q-6) and the librarian (LIB) ----

# The search unit is the outline node (OL-4): a judge's concepts, not a size. A file with no outline by the
# chosen judge is one unit, whole. The chunking is part of the model's name (Q-6).
MODEL_DIR = os.environ.get("VIKI_MODEL_DIR", "/opt/viki-bin/model")
VEC_CHARS = 2000   # (invented) the most node text embedded; the model reads at most 256 wordpieces anyway


def is_text(body):
    try:
        body.decode("utf-8")
        return b"\0" not in body
    except UnicodeDecodeError:
        return False


def text_heads(store, kinds, repo=None, skip=()):
    """The current, readable text bodies of these kinds (a fork's heads all count)."""
    for r in store.walk():
        if r.kind not in kinds or not r.body or not is_text(r.body):
            continue
        akey = r.akey.decode("utf-8", "replace")
        if repo is not None and not (akey.startswith(repo + "/") or akey.startswith(f"qa/{repo}/")):
            continue
        if skip and skipped(akey.split("#", 1)[0].removeprefix("qa/"), skip):
            continue
        if store.standing(r.akey, r.id)[0]:
            yield r


def outline_nodes(store, judge, r):
    """The nodes of judge's current outline of file version r, the root (depth 0) first: dicts of path
    (titles from the root down), lo, hi, depth, and own (its byte segments less its children's). One root
    node holding everything if there is no outline."""
    root = {"path": [], "lo": 0, "hi": len(r.body), "depth": 0}
    st, body = store.current(vk.outline_key(r.id, judge))
    tops = json.loads(body) if st == vk.OK and body else []
    out = [root]

    def walk(nodes, path, depth):
        for n in nodes:
            d = {"path": path + [n["title"]], "lo": n["lo"], "hi": n["hi"], "depth": depth}
            out.append(d)
            d["kids"] = n.get("children") or []
            walk(d["kids"], d["path"], depth + 1)
    walk(tops, [], 1)
    root["kids"] = tops
    for d in out:
        segs, at = [], d["lo"]
        for k in sorted(d.pop("kids"), key=lambda k: k["lo"]):
            if k["lo"] > at:
                segs.append((at, k["lo"]))
            at = max(at, k["hi"])
        if at < d["hi"]:
            segs.append((at, d["hi"]))
        d["own"] = segs
    return out


def own_text(body, node):
    return b"".join(body[a:b] for a, b in node["own"]).decode("utf-8", "replace")


def node_text(body, node):
    """What is embedded for a node: its titles, then its own text."""
    return (" > ".join(node["path"]) + "\n" + own_text(body, node))[:VEC_CHARS]


def vector_model(emb, judge):
    """Nodes by judge's outline; a librarian's entry as one vector per question and one for its summary
    (embedded whole, an entry's questions were diluted by its summary, or cut at 256 wordpieces)."""
    return f"{emb.id}/outline:{judge.decode()}/per-question".encode()


def entry_lines(body):
    """(lo, hi) of each 'Q:' and 'Summary:' line of an entry."""
    out, at = [], 0
    for line in body.split(b"\n"):
        if line.startswith(b"Q: ") or line.startswith(b"Summary: "):
            out.append((at, at + len(line)))
        at += len(line) + 1
    return out


def cmd_embed(store, repo, judge, skip=(), librarian=LIBRARIANS["sonnet"][1], only=()):
    """Vectors of every outline node of the current files, and of librarian's entries (no one else's). A body's
    vectors are dropped first, so spans of an outline it no longer has do not linger. only: these files and
    their entries alone. Every run embeds afresh; skipping unchanged bodies is not built."""
    import vkembed
    emb = vkembed.Embedder(MODEL_DIR)
    model, n, rows, empty = vector_model(emb, judge), 0, 0, 0
    store.exec("BEGIN")
    try:
        for r in text_heads(store, {b"file", b"qa"}, repo, skip):
            if r.kind == b"qa" and r.author != librarian:
                continue
            if only and not skipped(r.akey.decode("utf-8", "replace").removeprefix("qa/").split("#", 1)[0], only):
                continue
            store.vector_drop(r.id, model)
            if r.kind == b"qa":
                for lo, hi in entry_lines(r.body):
                    text = r.body[lo:hi].decode("utf-8", "replace").split(": ", 1)[1]
                    store.vector_put(r.id, model, lo, hi, emb.embed(text))
                    n += 1
            else:
                for node in outline_nodes(store, judge, r):
                    text = own_text(r.body, node)
                    if not text.strip():
                        empty += 1   # a node all of whose text is in its children: they carry it
                        continue
                    store.vector_put(r.id, model, node["lo"], node["hi"], emb.embed(node_text(r.body, node)))
                    n += 1
            rows += 1
        store.exec("COMMIT")
    except BaseException:
        store.exec("ROLLBACK")
        raise
    print(f"{n} vectors of {rows} bodies under {model.decode()}; {empty} nodes with no text of their own")
    return 0


LIBRARIAN_PROMPT = """You are the librarian of a software project's repository. Below is one file, with numbered lines,
and the numbered nodes of its outline (each a concept, with the lines it spans). For each node listed, write:
- "summary": two or three sentences on what that concept says, decides or warns about, naming its identifiers;
- "questions": three to six questions a developer would ask that this node answers. Word most of them as someone
  who has not read the file would ask, in their own terms (for example "how do I stop every machine redoing the
  same work?"), and some with the file's own names (for example "where is the embedding defined?").
Answer with only JSON: {{"<node number>": {{"summary": "...", "questions": ["...", "..."]}}, ...}}

File {path}:
{numbered}

Outline nodes:
{nodes}
"""
NODES_PER_CALL = 60   # (invented) a call answers for at most this many nodes; the file is always sent whole


def entry_body(path, node, lines_of, e):
    a, b = lines_of(node)
    qs = [" ".join(str(q).split()) for q in e.get("questions") or [] if str(q).strip()]
    return "\n".join([f"{path} lines {a}-{b}: {' > '.join(node['path']) or '(outside every section)'}",
                      f"Summary: {' '.join(str(e.get('summary', '')).split())}"] + [f"Q: {q}" for q in qs]).encode()


EXCERPT_PROMPT = """You are the librarian of a software project's repository. The file {path} has changed. Below are
the nodes of its outline whose own text the change touched, or that are new, each with its text (numbered lines of
the new version) and the entry it had before, if any. For each node, write its entry afresh:
- "summary": two or three sentences on what that concept says, decides or warns about, naming its identifiers;
- "questions": three to six questions a developer would ask that this node answers. Word most of them as someone
  who has not read the file would ask, in their own terms, and some with the file's own names.
Prefer to keep the previous entry where its meaning still holds.
Answer with only JSON: {{"<node number>": {{"summary": "...", "questions": ["...", "..."]}}, ...}}

{nodes}
"""


def has_entry(store, r, node):
    """The node already has an entry made from this version of its file."""
    head = store.head_id(b"qa/" + r.akey + f"#{node['lo']}-{node['hi']}".encode())
    return head is not None and r.id in (store.get(head).derived_from or [])


def titles_of(node):
    return " > ".join(node["path"]) or "(outside every section)"


def entries_by_file(store, librarian):
    """{file akey: {titles: record}}: every current, non-empty entry by librarian."""
    out = {}
    for r in store.walk():
        if r.kind != b"qa" or r.author != librarian or not r.body or not store.standing(r.akey, r.id)[0]:
            continue
        head = r.body.split(b"\n", 1)[0].decode("utf-8", "replace")
        out.setdefault(r.akey[3:].rsplit(b"#", 1)[0], {})[head.split(": ", 1)[1] if ": " in head else ""] = r
    return out


def parse_entry(body):
    text = body.decode("utf-8", "replace")
    summ = next((l[9:] for l in text.split("\n") if l.startswith("Summary: ")), "")
    return {"summary": summ, "questions": [l[3:] for l in text.split("\n") if l.startswith("Q: ")]}


def cmd_librarian(store, repo, name, judge, limit, cmd, skip=(), jobs=4):
    """LIB-1: an entry for every outline node of each current file. A file whose previous version has entries is
    updated: only the nodes whose own text changed, or that are new, are asked about, from their own text; the
    rest are carried to their new spans with no call, and the entries of nodes that went are retired. A file
    with no entries yet is sent whole (FINDINGS 2026-11-10: an update this way costs a fifth)."""
    model, principal = LIBRARIANS[name]
    cmd = cmd or f"claude -p --model {model} --tools \"\" --no-session-persistence --output-format text"
    held = entries_by_file(store, principal)
    plans, no_outline = [], 0
    for r in text_heads(store, {b"file"}, repo, skip):
        oid = store.head_id(vk.outline_key(r.id, judge))
        if oid is None:
            no_outline += 1
            continue
        nodes = [n for n in outline_nodes(store, judge, r) if own_text(r.body, n).strip()]
        if all(has_entry(store, r, n) for n in nodes):
            continue
        cur = held.get(r.akey, {})
        prev = next((p for p in (store.get(i) for i in r.supersedes) if p and p.kind == b"file" and p.body), None)
        lines = text_lines(r.body)
        starts = [0]
        for ln in lines:
            starts.append(starts[-1] + len(ln))
        import bisect

        def line_no(off, starts=starts):
            return bisect.bisect_right(starts, off)

        def lines_of(n, line_no=line_no):
            return line_no(n["lo"]), max(1, line_no(max(n["lo"], n["hi"] - 1)))
        if cur and prev is not None:
            changed = changed_new_lines(str_lines(prev.body), str_lines(r.body))
            ask = [n for n in nodes if titles_of(n) not in cur or
                   any(line_no(a) <= x <= line_no(max(a, b - 1)) for a, b in n["own"] for x in changed)]
        else:
            ask = nodes
        plans.append({"r": r, "oid": oid, "nodes": nodes, "ask": ask, "cur": cur, "lines": lines,
                      "lines_of": lines_of, "line_no": line_no, "excerpt": bool(cur and prev is not None)})
    if limit is not None:
        plans = plans[:limit]
    calls = []
    for pl in plans:
        for i in range(0, len(pl["ask"]), NODES_PER_CALL):
            calls.append((pl, pl["ask"][i:i + NODES_PER_CALL]))

    def ask(call):
        pl, group = call
        r = pl["r"]
        if pl["excerpt"]:
            parts = []
            for k, n in enumerate(group, 1):
                text = "".join(f"{pl['line_no'](a) + j}\t{ln}\n" for a, b in n["own"]
                               for j, ln in enumerate(r.body[a:b].decode("utf-8", "replace").splitlines()))
                old = pl["cur"].get(titles_of(n))
                parts.append(f"=== node {k}: {titles_of(n)} (lines {pl['lines_of'](n)[0]}-{pl['lines_of'](n)[1]}) ===\n"
                             + text + (f"\nPrevious entry: {json.dumps(parse_entry(old.body))}" if old else ""))
            prompt = EXCERPT_PROMPT.format(path=r.akey.decode(), nodes="\n\n".join(parts))
        else:
            listing = "\n".join(f"{k}. {titles_of(n)} (lines {pl['lines_of'](n)[0]}-{pl['lines_of'](n)[1]})"
                                for k, n in enumerate(group, 1))
            prompt = LIBRARIAN_PROMPT.format(path=r.akey.decode(), numbered=numbered(pl["lines"]), nodes=listing)
        try:
            return call, ask_judge(cmd, prompt)
        except (vk.VkError, subprocess.TimeoutExpired) as e:
            print(f"  {r.akey.decode()}: the librarian failed: {e}", file=sys.stderr)
            return call, ""
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(jobs) as pool:
        answers = list(pool.map(ask, calls))
    fresh = {}
    missing = 0
    for (pl, group), answer in answers:
        m = re.search(r"\{.*\}", answer, re.S)
        try:
            got = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            got = {}
        for k, n in enumerate(group, 1):
            if isinstance(got.get(str(k)), dict):
                fresh[(id(pl), titles_of(n))] = got[str(k)]
            else:
                missing += 1
    asked = carried = retired = 0
    for pl in plans:
        r, used = pl["r"], set()
        for n in pl["nodes"]:
            t = titles_of(n)
            e = fresh.get((id(pl), t))
            if e is None and n in pl["ask"]:
                continue   # asked and unanswered: left for a later run
            old = pl["cur"].get(t)
            if e is None:
                if old is None:
                    continue
                e, carried = parse_entry(old.body), carried + 1
            else:
                asked += 1
            key = b"qa/" + r.akey + f"#{n['lo']}-{n['hi']}".encode()
            used.add(t)
            t0 = now_utc()
            # Supersession acts within one akey (R-1a): the entry chains on its node's key, and if the node moved,
            # the key it had is retired by an empty entry. The old entry is named as a source either way.
            store.put(b"qa", key, entry_body(r.akey.decode(), n, pl["lines_of"], e), ts=t0.isoformat().encode(),
                      rank=rank_of(t0.timestamp()), reference=r.id.hex().encode(),
                      derived_from=[r.id, pl["oid"]] + ([old.id] if old else []), chain=True)
            if old is not None and old.akey != key and store.standing(old.akey, old.id)[0]:
                store.put(b"qa", old.akey, b"", ts=t0.isoformat().encode(), rank=rank_of(t0.timestamp()),
                          reference=r.id.hex().encode(), derived_from=[r.id, old.id], chain=True)
        for t, old in pl["cur"].items():
            if t not in used and store.standing(old.akey, old.id)[0]:
                t0 = now_utc()   # the node went: its entry is retired by an empty one, and stays readable before it
                store.put(b"qa", old.akey, b"", ts=t0.isoformat().encode(), rank=rank_of(t0.timestamp()),
                          reference=r.id.hex().encode(), derived_from=[r.id, pl["oid"]], chain=True)
                retired += 1
    print(f"librarian {principal.decode()}: {asked} node entries written, {carried} carried, {retired} retired, "
          f"{missing} nodes unanswered, {len(calls)} calls over {len(plans)} files; "
          f"{no_outline} files have no outline by {judge.decode()}")
    return 0


def node_key(store, id_, node, cache):
    """A hit as (file akey, lo, hi): the node it stands for. A librarian's entry stands for the node it
    describes; a hit with no node, a file with no outline, stands for the whole file. None if it is not a
    current file or an entry."""
    r = cache.get(id_) or cache.setdefault(id_, store.get(id_))
    if r is None:
        return None
    if r.kind == b"qa":
        if not r.body or not store.standing(r.akey, r.id)[0]:
            return None   # superseded or retired
        path, span = r.akey[3:].decode().rsplit("#", 1)
        lo, hi = span.split("-")
        return (path, int(lo), int(hi))
    if r.kind != b"file" or not store.standing(r.akey, r.id)[0]:
        return None
    if node:
        return (r.akey.decode(), node[1], node[2])
    return (r.akey.decode(), 0, len(r.body))


def ranked(store, emb, text, method, cache, librarian=LIBRARIANS["sonnet"][1]):
    """The nodes one method returns for text, best first, each once, counting only librarian's entries
    (None: no entries at all). None if the method is blind (Q-2)."""
    hits, _ = store.bm25(text.encode()) if method == "bm25" else store.vector(emb.embed(text))
    if hits is None:
        return None
    out, seen = [], set()
    for id_, node in hits:
        r = cache.get(id_) or cache.setdefault(id_, store.get(id_))
        if r is not None and r.kind == b"qa" and r.author != librarian:
            continue
        k = node_key(store, id_, node, cache)
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def fuse(lists, k=60):
    """Reciprocal-rank fusion by node, as src/ fused its legs (k=60)."""
    score = {}
    for lst in lists:
        for rank, key in enumerate(lst, 1):
            score[key] = score.get(key, 0) + 1 / (k + rank)
    return sorted(score, key=lambda key: -score[key])


def cmd_ask(store, text, k, judge, with_qa=True):
    import vkembed
    emb = vkembed.Embedder(MODEL_DIR)
    store.use_vectors(vector_model(emb, judge))
    store.use_outlines(judge)
    cache = {}
    lib = LIBRARIANS["sonnet"][1] if with_qa else None
    legs = {m: ranked(store, emb, text, m, cache, lib) for m in ("bm25", "vector")}
    blind = [m for m, lst in legs.items() if lst is None]
    for i, (f, lo, hi) in enumerate(fuse([lst for lst in legs.values() if lst])[:k], 1):
        print(f"[{i}] {f}  bytes {lo}-{hi}")
    print("legs: " + ", ".join(f"{m} {len(lst)} nodes" for m, lst in legs.items() if lst is not None)
          + (f"; blind: {', '.join(blind)} (vector: run embed)" if blind else ""))
    return 0 if any(legs.values()) else (3 if blind else 1)




def main(argv):
    ap = argparse.ArgumentParser(prog="la.py", description=__doc__.split("\n")[0])
    ap.add_argument("--store", required=True)
    ap.add_argument("--keyfile", help="the diary's raw key (mode 600); make one with viki's vk.py keygen")
    ap.add_argument("--plaintext", action="store_true", help="say an UNENCRYPTED diary was meant")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ol = sub.add_parser("outline", help="ask a judge for outlines of file versions (OL)")
    ol.add_argument("--repo")
    ol.add_argument("--judge", choices=sorted(JUDGES), default="sonnet")
    ol.add_argument("--history", action="store_true", help="every version, oldest first, not only current ones")
    ol.add_argument("--limit", type=int, help="at most this many judge calls this run")
    ol.add_argument("--judge-cmd", help="the command that answers a prompt on stdin (default: the claude CLI)")
    ol.add_argument("--skip", action="append", default=[], metavar="PATH", help="a file or directory, as repo/path")
    ol.add_argument("--redo", action="append", default=[], metavar="PATH",
                    help="outline this file's current version again, from its predecessor's outline")
    ol.add_argument("--jobs", type=int, default=4, help="judge calls in parallel (with --history, one at a time)")
    em = sub.add_parser("embed", help="vectors of each outline node of the current files, and of the librarian's entries (Q-6)")
    em.add_argument("--repo")
    em.add_argument("--judge", choices=sorted(JUDGES), default="sonnet", help="whose outlines set the units")
    em.add_argument("--skip", action="append", default=[], metavar="PATH")
    em.add_argument("--only", action="append", default=[], metavar="PATH", help="these files and their entries alone")
    lb = sub.add_parser("librarian", help="a model writes a summary and questions for every outline node (LIB-1)")
    lb.add_argument("--repo")
    lb.add_argument("--model", choices=sorted(LIBRARIANS), default="sonnet")
    lb.add_argument("--judge", choices=sorted(JUDGES), default="sonnet", help="whose outlines it works on")
    lb.add_argument("--limit", type=int, help="at most this many files this run")
    lb.add_argument("--judge-cmd", help="the command that answers a prompt on stdin (default: the claude CLI)")
    lb.add_argument("--skip", action="append", default=[], metavar="PATH", help="a file or directory the librarian must not read")
    lb.add_argument("--jobs", type=int, default=4, help="calls in parallel")
    ak = sub.add_parser("ask", help="bm25 and vector over outline nodes and the librarian's entries, fused by node")
    ak.add_argument("text")
    ak.add_argument("--k", type=int, default=10)
    ak.add_argument("--judge", choices=sorted(JUDGES), default="sonnet")
    ak.add_argument("--no-entries", action="store_true", help="leave the librarian's entries out")
    args = ap.parse_args(argv)
    try:
        if args.keyfile and args.plaintext:
            raise KeyError_("--keyfile and --plaintext contradict each other")
        if not args.keyfile and not args.plaintext:
            raise KeyError_(f"refusing to open {args.store} without a key: --keyfile PATH, or --plaintext")
        key = read_keyfile(args.keyfile) if args.keyfile else None
        if args.cmd == "librarian":
            me = LIBRARIANS[args.model][1]
        elif args.cmd == "outline":
            me = JUDGES[args.judge][1]
        else:
            me = PRINCIPAL
        # whoever writes writes as itself; the ingester, the judges and the librarians are all entitled (R-4a)
        store = vk.Store(args.store, me, RIGHTS, key=key, others=[(PRINCIPAL, RIGHTS)] + [g for g in GRANTS if g[0] != me])
    except (KeyError_, vk.VkError) as e:
        print(f"la: {e}", file=sys.stderr)
        return 2
    try:
        if args.cmd == "embed":
            return cmd_embed(store, args.repo, JUDGES[args.judge][1], args.skip, only=args.only)
        if args.cmd == "librarian":
            return cmd_librarian(store, args.repo, args.model, JUDGES[args.judge][1], args.limit, args.judge_cmd,
                                 args.skip, args.jobs)
        if args.cmd == "ask":
            return cmd_ask(store, args.text, args.k, JUDGES[args.judge][1], not args.no_entries)
        return cmd_outline(store, args.repo, args.judge, args.history, args.limit, args.judge_cmd, args.skip,
                           args.jobs, args.redo)
    except (vk.VkError, subprocess.CalledProcessError, ValueError) as e:   # ValueError: a model that fails its pin
        print(f"la: {e}", file=sys.stderr)
        return 2
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
