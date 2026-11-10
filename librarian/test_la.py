"""test_la.py -- la.py, the librarian, against scratch git repositories and a viki diary (viki-agent LA, viki's OL and Q-6).

Each repository is built here with fixed names and dates, so a run repeats
exactly. Prints PASS/FAIL lines in the form core/test/gate.py reads.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VIKI_TOOLS = os.environ.get("VIKI_TOOLS") or os.path.join(HERE, "..", "..", "viki", "tools")
VK = [sys.executable, os.path.join(VIKI_TOOLS, "vk.py")]
LA = [sys.executable, os.path.join(HERE, "la.py")]
sys.path.insert(0, VIKI_TOOLS)
failed = 0


class Scratch:
    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="vk-test-")
        self.tick = 0
        self.store = os.path.join(self.root, "diary.db")

    def env(self):
        self.tick += 1
        when = f"2026-11-09T10:{self.tick:02d}:00+00:00"
        e = dict(os.environ, HOME=self.root, GIT_CONFIG_NOSYSTEM="1",
                 GIT_AUTHOR_NAME="Tester", GIT_AUTHOR_EMAIL="t@example.invalid",
                 GIT_COMMITTER_NAME="Tester", GIT_COMMITTER_EMAIL="t@example.invalid",
                 GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
        return e

    def git(self, repo, *args):
        subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, env=self.env())

    def repo(self, name):
        d = os.path.join(self.root, name)
        os.makedirs(d)
        self.git(d, "init", "-q", "-b", "main")
        return d

    def write(self, repo, path, text):
        p = os.path.join(repo, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)

    def commit(self, repo, msg):
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", msg)

    def vk(self, *args):
        r = subprocess.run(VK + ["--store", self.store, "--plaintext", *args], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def la(self, *args):
        r = subprocess.run(LA + ["--store", self.store, "--plaintext", *args], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def vk_bare(self, *args):
        """vk.py with exactly these arguments: no --store or --plaintext added."""
        r = subprocess.run(VK + list(args), capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def close(self):
        shutil.rmtree(self.root)


def check(cond, what, out=""):
    global failed_now
    if not cond:
        print(f"  {what}")
        if out:
            print("    " + out.strip().replace("\n", "\n    "))
        failed_now = True


def run(rid, name, fn):
    global failed, failed_now
    failed_now = False
    s = Scratch()
    try:
        fn(s)
    except Exception as e:   # a crash is a failure, said plainly
        check(False, f"raised {type(e).__name__}: {e}")
    finally:
        s.close()
    print(f"{'FAIL' if failed_now else 'PASS'} {rid} {name}")
    failed += failed_now


FAKE_JUDGE = r"""
import json, os, re, sys
prompt = sys.stdin.read()
log = os.environ.get("VK_FAKE_LOG")
if log:
    with open(log, "a") as f:
        f.write("CARRY\n" if "Outline of the previous version" in prompt else "FIRST\n")
if "Changes:\n" in prompt:   # an update: the diff's new-version lines, "N text" or "N+ text"
    block = prompt.split("Changes:\n", 1)[1]
    lines = [re.sub(r"^(\d+)\+? ", r"\1\t", ln) for ln in block.splitlines() if re.match(r"^\d+\+? ", ln)]
else:
    lines = [ln for ln in prompt.splitlines() if re.match(r"^\d+\t", ln)]
nodes = []
for ln in lines:
    n, text = ln.split("\t", 1)
    if text.startswith("#"):
        nodes.append({"title": text.lstrip("# ").strip(), "start": int(n), "children": []})
if "Changes:\n" in prompt:   # keep the previous outline's nodes the diff does not show (this edit only appends)
    prev = json.loads(prompt.split("line numbers):\n", 1)[1].split("\n\nChanges:", 1)[0])
    seen = {nd["title"] for nd in nodes}
    nodes = sorted([{**p, "children": []} for p in prev if p["title"] not in seen] + nodes, key=lambda nd: nd["start"])
last = max(int(ln.split("\t")[0]) for ln in lines)
for i, nd in enumerate(nodes):
    nd["end"] = nodes[i + 1]["start"] - 1 if i + 1 < len(nodes) else last
print("Here is the outline:\n" + json.dumps(nodes))
"""


def t_ol_cmd(s):
    judge = os.path.join(s.root, "judge.py")
    with open(judge, "w") as f:
        f.write(FAKE_JUDGE)
    log = os.path.join(s.root, "judge.log")
    os.environ["VK_FAKE_LOG"] = log
    cmd = f"{sys.executable} {judge}"
    a = s.repo("alpha")
    s.write(a, "notes.md", "# Alpha\nfirst words\n# Beta\nsecond words\n")
    with open(os.path.join(a, "blob.bin"), "wb") as f:
        f.write(b"\x00\x01binary")
    s.commit(a, "one")
    s.write(a, "notes.md", "# Alpha\nfirst words\n# Beta\nsecond words\n# Gamma\nthe marker-gamma words\n")
    s.commit(a, "two")
    s.vk("ingest-git", a)
    rc, out = s.la("outline", "--judge-cmd", cmd)
    check(rc == 0 and "1 written" in out and "1 not text" in out and "1 judge calls" in out,
          "the current versions are outlined; a binary one is not", out)
    rc, out = s.la("outline", "--judge-cmd", cmd)
    check(rc == 0 and "1 already outlined" in out and "0 judge calls" in out, "a second run asks nothing", out)
    rc, out = s.vk("grep", "marker-gamma", "--outlines", "vk.judge.sonnet")
    check(rc == 0 and "in: Gamma" in out, "the judge's outline is searched", out)
    # with history, on a fresh diary: the old version first, then the new one carried forward
    s.store = os.path.join(s.root, "history.db")
    open(log, "w").close()
    s.vk("ingest-git", a)
    rc, out = s.la("outline", "--history", "--judge-cmd", cmd)
    check(rc == 0 and "2 written" in out, "both versions are outlined", out)
    with open(log) as f:
        check(f.read().split() == ["FIRST", "CARRY"], "the first is outlined fresh, the second carried forward")
    import vkstore as vk  # viki's binding, on VIKI_TOOLS
    st = vk.Store(s.store, b"vk.ingest.git", vk.READ, others=[(b"vk.judge.sonnet", vk.ORIGINATE | vk.SUPERSEDE | vk.READ)])
    try:
        outlines = [r for r in st.walk() if r.kind == b"outline"]
        check(len(outlines) == 2 and sorted(len(r.derived_from) for r in outlines) == [1, 2],
              "the carried outline names the one it carried (OL-3)")
        carried = max(outlines, key=lambda r: len(r.derived_from))
        titles = [n["title"] for n in json.loads(carried.body)]
        check(titles == ["Alpha", "Beta", "Gamma"], "the update is made from the diff, and holds the new section", str(titles))
    finally:
        st.close()
    s.store = os.path.join(s.root, "limit.db")
    s.vk("ingest-git", a)
    rc, out = s.la("outline", "--history", "--limit", "1", "--judge-cmd", cmd)
    check(rc == 0 and "1 judge calls" in out and "1 left for a later run" in out, "--limit stops and says so", out)


FAKE_LIBRARIAN = r"""
import json, os, re, sys
prompt = sys.stdin.read()
if "has changed" in prompt:   # an update: excerpts of the nodes whose own text changed
    path = re.search(r"The file (\S+) has changed", prompt).group(1)
    nodes = re.findall(r"^=== node (\d+): (.+?) \(lines", prompt, re.M)
else:
    path = re.search(r"^File (.+):$", prompt, re.M).group(1)
    nodes = re.findall(r"^(\d+)\. (.+?) \(lines", prompt.split("Outline nodes:", 1)[1], re.M)
with open(os.environ["VK_FAKE_LOG"], "a") as f:
    f.write(("UPDATE " if "has changed" in prompt else "WHOLE ") + path + " " + ",".join(t for _, t in nodes) + "\n")
print(json.dumps({n: {"summary": "a summary", "questions": [f"where is the {t.lower()} part kept?", "marker definition"]}
                  for n, t in nodes}))
"""


def t_librarian(s):
    lib = os.path.join(s.root, "librarian.py")
    with open(lib, "w") as f:
        f.write(FAKE_LIBRARIAN)
    judge = os.path.join(s.root, "judge.py")
    with open(judge, "w") as f:
        f.write(FAKE_JUDGE)
    log = os.path.join(s.root, "librarian.log")
    os.environ["VK_FAKE_LOG"] = log
    cmd, jcmd = f"{sys.executable} {lib}", f"{sys.executable} {judge}"
    a = s.repo("alpha")
    s.write(a, "notes.md", "# Notes\nthe marker is here\n# More\nmore words\n")
    s.write(a, "plain.md", "# Plain\nno outline will be asked for this one\n")
    s.write(a, "questions.tsv", "# held out\nnever to be read\n")
    s.commit(a, "one")
    s.vk("ingest-git", a)
    s.la("outline", "--skip", "alpha/plain.md", "--judge-cmd", jcmd)
    open(log, "w").close()
    rc, out = s.la("librarian", "--skip", "alpha/questions.tsv", "--judge-cmd", cmd)
    check(rc == 0 and "2 node entries written" in out and "1 files have no outline" in out,
          "one entry per outline node; a file with no outline is not guessed at", out)
    with open(log) as f:
        sent = f.read()
    check("alpha/notes.md" in sent and "questions.tsv" not in sent, "a skipped file is never sent", sent)
    rc, out = s.la("librarian", "--skip", "alpha/questions.tsv", "--judge-cmd", cmd)
    check(rc == 0 and "0 node entries written" in out and "0 calls" in out, "a second run asks nothing", out)
    rc, out = s.vk("grep", "Q: marker definition")
    check(rc == 0 and out.count("qa  ") == 2, "each node's entry is its own assertion, in question form", out)
    s.la("embed")
    rc, out = s.la("ask", "where is the more part kept?")
    check(rc == 0 and "[1] alpha/notes.md  bytes 27-45" in out, "an entry's hit returns its node", out)
    # an update: the More section's text changes, a new section is added; Notes is untouched
    s.write(a, "notes.md", "# Notes\nthe marker is here\n# More\nmore words, now rewritten\n# Late\nadded later\n")
    s.commit(a, "two")
    s.vk("ingest-git", a)
    s.la("outline", "--skip", "alpha/plain.md", "--judge-cmd", jcmd)
    open(log, "w").close()
    rc, out = s.la("librarian", "--skip", "alpha/questions.tsv", "--judge-cmd", cmd)
    check(rc == 0 and "2 node entries written, 1 carried, 0 retired" in out,
          "an update asks only the changed and new nodes; the untouched one is carried", out)
    with open(log) as f:
        sent = f.read()
    check(sent.strip() == "UPDATE alpha/notes.md More,Late", "only their own text is sent, not the whole file", sent)
    # a section goes: its entry is retired, not left current
    s.write(a, "notes.md", "# Notes\nthe marker is here\n# Late\nadded later\n")
    s.commit(a, "three")
    s.vk("ingest-git", a)
    s.la("outline", "--skip", "alpha/plain.md", "--judge-cmd", jcmd)
    rc, out = s.la("librarian", "--skip", "alpha/questions.tsv", "--judge-cmd", cmd)
    check(rc == 0 and "1 retired" in out, "the entry of a node that went is retired", out)
    s.la("embed")
    rc, out = s.la("ask", "where is the more part kept?")
    check(rc == 0 and "bytes 27-45" not in out, "a retired entry is not returned", out)


MODEL_DIR = os.environ.get("VIKI_MODEL_DIR", "/opt/viki-bin/model")


def t_vector(s):
    if not os.path.isfile(os.path.join(MODEL_DIR, "model.onnx")):
        check(False, f"no pinned model at {MODEL_DIR} (set VIKI_MODEL_DIR): not run, and not a pass")
        return
    a = s.repo("alpha")
    s.write(a, "pasture.md", "Six horses were grazing near the water trough at dawn.\n")
    s.write(a, "taxes.md", "The quarterly tax filing deadline is in April.\n")
    s.commit(a, "one")
    s.vk("ingest-git", a)
    rc, out = s.la("ask", "animals drinking")
    check(rc == 3 and "blind: vector" in out and "bm25 0 nodes" in out,
          "before embed, the vector leg is blind and says so, apart from bm25 finding nothing", out)
    rc, out = s.la("embed")
    check(rc == 0 and "2 vectors of 2 bodies" in out, "a file with no outline is one unit, whole", out)
    rc, out = s.la("ask", "animals drinking")
    check(rc == 0 and out.startswith("[1] alpha/pasture.md") and "bm25 0 nodes" in out,
          "a query sharing no word with the file finds it by vector", out)
    bad = os.path.join(s.root, "badmodel")
    os.makedirs(bad)
    for f in ("model.onnx", "viki-manifest.json"):
        os.symlink(os.path.join(MODEL_DIR, f), os.path.join(bad, f))
    with open(os.path.join(bad, "vocab.txt"), "w") as f:
        f.write("[PAD]\n")
    env = dict(os.environ, VIKI_MODEL_DIR=bad)
    r = subprocess.run(LA + ["--store", s.store, "--plaintext", "embed"], capture_output=True, text=True, env=env)
    check(r.returncode == 2 and "does not match viki-manifest.json" in r.stderr, "a model that fails its pin is refused",
          r.stdout + r.stderr)


def t_ol_large(s):
    judge = os.path.join(s.root, "judge.py")
    with open(judge, "w") as f:
        f.write(FAKE_JUDGE)
    os.environ["VK_FAKE_LOG"] = os.path.join(s.root, "judge.log")
    a = s.repo("alpha")
    sections = [f"# Section {i}\n" + "".join(f"line {j} of section {i}, with some words in it.\n" for j in range(60))
                for i in range(50)]
    sections[47] = sections[47].replace("line 30 of", "the marker-late line 30 of")
    s.write(a, "big.md", "".join(sections))
    s.commit(a, "one")
    s.vk("ingest-git", a)
    rc, out = s.la("outline", "--judge-cmd", f"{sys.executable} {judge}")
    calls = int(out.rsplit(";", 1)[1].split()[0]) if ";" in out else 0
    check(rc == 0 and "1 written" in out and calls == 1, "a large file goes to the judge whole, in one call", out)
    rc, out = s.vk("grep", "marker-late", "--outlines", "vk.judge.sonnet")
    check(rc == 0 and "in: Section 47" in out, "a word near the end lands in its own section", out)




def main():
    run("OL-3", "outline asks a judge, carries outlines forward from the diff, and writes each once", t_ol_cmd)
    run("OL-1", "a large file is outlined whole: dividing it is the judge's task", t_ol_large)
    run("Q-6", "embed and ask: a query in other words finds the file by vector", t_vector)
    run("LA-3", "the librarian writes an entry per node, updates from the diff, skips what it is told", t_librarian)
    print(f"{failed} of 4 failed")
    return failed != 0


if __name__ == "__main__":
    sys.exit(main())
