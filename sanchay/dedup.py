"""Find duplicate content.

Size-bucket first, then hash only the buckets that collide, then only the
colliding heads before hashing in full. Hardlinks to the same inode are not
duplicates -- they already share their bytes.
"""
import hashlib
import os
from collections import defaultdict

from . import storage

HEAD = 64 * 1024
CHUNK = 1 << 20
DIGEST_SIZE = 32


def _digest(path, limit=None):
    h = hashlib.blake2b(digest_size=DIGEST_SIZE)
    try:
        with open(path, "rb") as fh:
            if limit:
                h.update(fh.read(limit))
            else:
                for chunk in iter(lambda: fh.read(CHUNK), b""):
                    h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def same_content(left, right):
    """Return whether two readable files match byte for byte.

    The fast scan already narrows this expensive comparison to pairs with the
    same size, prefix digest, and full BLAKE2b-256 digest. A review plan then
    performs this direct comparison before relying on a named survivor.
    """
    try:
        if os.path.getsize(left) != os.path.getsize(right):
            return False
        with open(left, "rb") as left_fh, open(right, "rb") as right_fh:
            while True:
                left_chunk = left_fh.read(CHUNK)
                right_chunk = right_fh.read(CHUNK)
                if left_chunk != right_chunk:
                    return False
                if not left_chunk:
                    return True
    except OSError:
        return False


def _bucket(files, key):
    groups = defaultdict(list)
    for f in files:
        k = key(f)
        if k is not None:
            groups[k].append(f)
    return [g for g in groups.values() if len(g) > 1]


def duplicates(files, min_size=4096):
    # Select one path per inode before opening any candidate. A hardlink alias
    # has the same bytes, so hashing it again would only repeat I/O.
    candidates = [f for f in storage.physical_records(files) if f.size >= min_size]
    groups = _bucket(candidates, lambda f: f.size)

    refined = []
    for group in groups:
        refined += _bucket(group, lambda f: _digest(f.path, HEAD))

    final = []
    for group in refined:
        for same in _bucket(group, lambda f: _digest(f.path)):
            if len(same) > 1:
                final.append(same)
    return final


def reclaimable(groups):
    """Return bytes an individual review action could actually release.

    A hardlinked path has more than one name for the same inode. Removing one
    name frees no storage, so only standalone physical copies count here.
    """
    return sum(candidate.size
               for group in groups
               for candidate, _ in _reviewable_duplicate_pairs(group))


def duplicate_map(groups):
    """Map each removable duplicate to the deterministic copy that survives.

    A duplicate is only reviewable if the plan names a specific surviving copy.
    Sorting makes the result independent of filesystem walk order.
    """
    copies = {}
    for group in groups:
        for duplicate, keeper in _reviewable_duplicate_pairs(group):
            copies[duplicate.path] = keeper.path
    return copies


def confirmed_duplicate_map(groups):
    """Keep only digest candidates that also pass a byte-for-byte comparison."""
    return {
        duplicate: survivor
        for duplicate, survivor in duplicate_map(groups).items()
        if same_content(duplicate, survivor)
    }


def _physical_copies(group):
    """Pick one deterministic directory entry for each physical inode."""
    copies = {}
    for info in group:
        identity = storage.inode_identity(info)
        prior = copies.get(identity)
        if prior is None or _path_key(info) < _path_key(prior):
            copies[identity] = info
    return sorted(copies.values(), key=_path_key)


def _reviewable_duplicate_pairs(group):
    """Yield removable standalone copies paired with a retained survivor."""
    copies = _physical_copies(group)
    if len(copies) < 2:
        return []
    # Prefer an inode with multiple names as survivor. That leaves a standalone
    # duplicate as the action a human could review to reclaim physical storage.
    keeper = min(copies, key=lambda info: (-getattr(info, "nlink", 1),
                                           _path_key(info)))
    return [(info, keeper) for info in copies
            if info is not keeper and not storage.is_hardlinked(info)]


def _path_key(info):
    return str(info.path).replace("\\", "/")
