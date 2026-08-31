"""Score a file by what it costs to be wrong about deleting it.

Every cleanup tool ranks by bytes freed. That is the wrong objective: freeing
2 GB of package cache and freeing 2 GB of someone's only copy of their thesis
score identically, and only one of them is recoverable.

So rank by regret instead:

    priority = bytes * unchanged_age * (1 - regret)

Regret is estimated from reproducibility, not from content. A file is cheap to
lose if the system can produce it again -- it lives in a build or package cache,
it is committed to a git repo, or an identical copy exists elsewhere on disk.
A file that is none of those is irreplaceable and is never recommended,
regardless of size.
"""
import os
import subprocess
import time

# Directories whose contents a build or package tool will regenerate on demand.
DISPOSABLE = (
    "/.cache/", "/var/cache/", "/node_modules/", "/__pycache__/", "/.venv/",
    "/target/debug/", "/target/release/", "/build/", "/dist/", "/.gradle/",
    "/.npm/", "/.m2/repository/", "/site-packages/", "/.next/", "/.tox/",
)

REGRET = {
    "disposable": 0.02,   # a build system rebuilds it
    "duplicate": 0.10,    # another copy survives the delete
    "tracked": 0.20,      # committed to a repo
    "unique": 1.00,       # nothing gets it back
}


def _norm(path):
    return path.replace("\\", "/")


_repo_cache = {}


def _repo_root(path):
    d = os.path.dirname(path)
    while True:
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def _tracked_set(root):
    """Files whose current contents can be restored exactly from HEAD."""
    if root not in _repo_cache:
        try:
            committed = subprocess.run(
                ["git", "-C", root, "ls-tree", "-r", "--name-only", "-z", "HEAD"],
                capture_output=True, check=True, timeout=30)
            changed = subprocess.run(
                ["git", "-C", root, "diff", "--name-only", "-z", "HEAD", "--"],
                capture_output=True, check=True, timeout=30)
            committed_paths = {
                _norm(os.path.join(root, p))
                for p in committed.stdout.decode("utf-8", "replace").split(chr(0)) if p}
            changed_paths = {
                _norm(os.path.join(root, p))
                for p in changed.stdout.decode("utf-8", "replace").split(chr(0)) if p}
            _repo_cache[root] = committed_paths - changed_paths
        except (OSError, subprocess.SubprocessError):
            _repo_cache[root] = set()
    return _repo_cache[root]


def in_repo(path):
    root = _repo_root(path)
    return bool(root) and _norm(path) in _tracked_set(root)


def classify(info, duplicated):
    p = _norm(info.path)
    if any(marker in p for marker in DISPOSABLE):
        return "disposable"
    if duplicated:
        return "duplicate"
    if in_repo(info.path):
        return "tracked"
    return "unique"


def staleness(info, now=None):
    """0 for a file modified today, approaching 1 after a year unchanged.

    Access time is mount-policy dependent and can be changed by a duplicate
    hash read. Modification time is therefore the stable, inspectable signal
    available to a local scan; this is an unchanged-age factor, not a claim
    that a file has not been read.
    """
    days = max(0.0, ((now or time.time()) - info.mtime) / 86400)
    return min(1.0, days / 365)


def score(info, duplicated=False, now=None):
    kind = classify(info, duplicated)
    regret = REGRET[kind]
    stale = staleness(info, now)
    return {
        "path": info.path,
        "size": info.size,
        "kind": kind,
        "regret": regret,
        "staleness": round(stale, 3),
        "priority": info.size * stale * (1 - regret),
    }


def rank(files, duplicate_paths=frozenset(), now=None, limit=25):
    scored = [score(f, f.path in duplicate_paths, now) for f in files]
    safe = [s for s in scored if s["kind"] != "unique"]
    safe.sort(key=lambda s: s["priority"], reverse=True)
    return safe[:limit]
