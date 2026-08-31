"""Find duplicate content.

Size-bucket first, then hash only the buckets that collide, then only the
colliding heads before hashing in full. Hardlinks to the same inode are not
duplicates -- they already share their bytes.
"""
import hashlib
from collections import defaultdict

HEAD = 64 * 1024


def _digest(path, limit=None):
    h = hashlib.blake2b(digest_size=16)
    try:
        with open(path, "rb") as fh:
            if limit:
                h.update(fh.read(limit))
            else:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def same_content(left, right):
    """Return whether two readable files have the same full-content digest.

    This is deliberately used only after the fast scan has already identified
    a duplicate candidate.  Plan verification rechecks the named survivor so a
    reviewer never relies on a stale duplicate relationship.
    """
    left_digest = _digest(left)
    right_digest = _digest(right)
    return left_digest is not None and left_digest == right_digest


def _bucket(files, key):
    groups = defaultdict(list)
    for f in files:
        k = key(f)
        if k is not None:
            groups[k].append(f)
    return [g for g in groups.values() if len(g) > 1]


def duplicates(files, min_size=4096):
    candidates = [f for f in files if f.size >= min_size]
    groups = _bucket(candidates, lambda f: f.size)

    refined = []
    for group in groups:
        refined += _bucket(group, lambda f: _digest(f.path, HEAD))

    final = []
    for group in refined:
        for same in _bucket(group, lambda f: _digest(f.path)):
            # Collapse hardlinks: one (device, inode) identity is one copy.
            # Inode numbers alone are only unique within a filesystem.
            if len({(getattr(f, "device", 0), f.inode) for f in same}) > 1:
                final.append(same)
    return final


def reclaimable(groups):
    """Bytes freed by keeping one copy from each group."""
    return sum(g[0].size * (len(g) - 1) for g in groups)


def duplicate_map(groups):
    """Map each removable duplicate to the deterministic copy that survives.

    A duplicate is only a safe candidate if the plan names a specific surviving
    copy.  Sorting makes the result independent of filesystem walk order.
    """
    copies = {}
    for group in groups:
        ordered = sorted(group, key=lambda f: f.path.replace("\\", "/"))
        keeper = ordered[0]
        for duplicate in ordered[1:]:
            copies[duplicate.path] = keeper.path
    return copies
