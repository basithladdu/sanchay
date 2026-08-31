"""Find duplicate content.

Size-bucket first, then hash only the buckets that collide, then only the
colliding heads before hashing in full. Hardlinks to the same inode are not
duplicates -- they already share their bytes.
"""
import hashlib
import os
import stat
from collections import defaultdict

from . import managed, storage

HEAD = 64 * 1024
CHUNK = 1 << 20
DIGEST_SIZE = 32


def root_anchoring_available():
    """Return whether this platform can safely walk a root by descriptor."""
    return (hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW")
            and os.open in getattr(os, "supports_dir_fd", set()))


def _read_flags(directory=False):
    """Build read-only flags that cannot block on an unexpected FIFO."""
    flags = os.O_RDONLY
    for name in ("O_BINARY", "O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK"):
        flags |= getattr(os, name, 0)
    if directory:
        flags |= getattr(os, "O_DIRECTORY", 0)
    return flags


def _path_under_root(path, root):
    """Return a canonical root and lexical relative path, or ``None``.

    The target remains lexical on purpose: resolving it here would follow a
    parent symlink that the descriptor walk below is meant to reject.
    """
    canonical_root = os.path.realpath(os.path.abspath(os.fspath(root)))
    target = os.path.abspath(os.fspath(path))
    try:
        relative = os.path.relpath(target, canonical_root)
    except ValueError:
        return None
    if (relative in {"", os.curdir, os.pardir}
            or relative.startswith(os.pardir + os.sep)
            or os.path.isabs(relative)):
        return None
    return canonical_root, relative


def _open_readonly(path, root=None):
    """Open a candidate without following path components when supported.

    On Linux, ``openat`` walks every component from the canonical scan-root
    descriptor with ``O_NOFOLLOW``.  Other platforms still use no-follow where
    available and the caller validates the opened descriptor before reading.
    """
    if root is not None and root_anchoring_available():
        rooted = _path_under_root(path, root)
        if rooted is None:
            raise OSError("candidate is outside the canonical scan root")
        canonical_root, relative = rooted
        directory_fd = os.open(canonical_root, _read_flags(directory=True))
        try:
            parts = relative.split(os.sep)
            for part in parts[:-1]:
                next_fd = os.open(part, _read_flags(directory=True),
                                  dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = next_fd
            return os.open(parts[-1], _read_flags(), dir_fd=directory_fd)
        finally:
            os.close(directory_fd)
    return os.open(path, _read_flags())


def _identity_from_stat(stat_result):
    return {
        "device": getattr(stat_result, "st_dev", None),
        "inode": getattr(stat_result, "st_ino", None),
        "size": getattr(stat_result, "st_size", None),
        "allocated_size": storage.allocated_bytes_from_stat(stat_result),
        "mtime": getattr(stat_result, "st_mtime", None),
        "mtime_ns": getattr(stat_result, "st_mtime_ns", None),
        "nlink": getattr(stat_result, "st_nlink", None),
    }


def _identity_from_info(info):
    if isinstance(info, dict):
        return info
    return {
        "device": getattr(info, "device", None),
        "inode": getattr(info, "inode", None),
        "size": getattr(info, "size", None),
        "allocated_size": storage.allocated_bytes(info),
        "mtime": getattr(info, "mtime", None),
        "mtime_ns": getattr(info, "mtime_ns", None),
        "nlink": getattr(info, "nlink", None),
    }


def _matches_expected(stat_result, expected):
    """Return whether an opened descriptor is still the scanned file."""
    if expected is None:
        return True
    actual = _identity_from_stat(stat_result)
    expected_identity = _identity_from_info(expected)
    for field in actual:
        if (expected_identity.get(field) is not None
                and actual[field] != expected_identity[field]):
            return False
    return True


def _open_verified(path, expected=None, root=None):
    """Pin a regular candidate descriptor and reject scan-time identity drift."""
    fd = None
    try:
        fd = _open_readonly(path, root=root)
        observed = os.fstat(fd)
        if (not stat.S_ISREG(observed.st_mode)
                or not _matches_expected(observed, expected)):
            os.close(fd)
            return None
        return fd, observed
    except OSError:
        if fd is not None:
            os.close(fd)
        return None


def _unchanged(before, after):
    return _identity_from_stat(before) == _identity_from_stat(after)


def _digest(path, limit=None, expected=None, root=None):
    """Hash one unchanged, regular file descriptor or return ``None``.

    A scan result is only evidence for the exact inode that was observed.  The
    descriptor is verified both before and after reading so a concurrent path
    swap or mutation cannot become duplicate evidence.
    """
    opened = _open_verified(path, expected=expected, root=root)
    if opened is None:
        return None
    fd, before = opened
    h = hashlib.blake2b(digest_size=DIGEST_SIZE)
    try:
        with os.fdopen(fd, "rb", closefd=False) as fh:
            if limit:
                h.update(fh.read(limit))
            else:
                for chunk in iter(lambda: fh.read(CHUNK), b""):
                    h.update(chunk)
        if not _unchanged(before, os.fstat(fd)):
            return None
    except OSError:
        return None
    finally:
        os.close(fd)
    return h.hexdigest()


def same_content(left, right, expected_left=None, expected_right=None,
                 root=None):
    """Return whether two readable files match byte for byte.

    The fast scan already narrows this expensive comparison to pairs with the
    same size, prefix digest, and full BLAKE2b-256 digest. A review plan then
    performs this direct comparison before relying on a named survivor.
    """
    left_opened = _open_verified(left, expected=expected_left, root=root)
    if left_opened is None:
        return False
    right_opened = _open_verified(right, expected=expected_right, root=root)
    if right_opened is None:
        os.close(left_opened[0])
        return False
    left_fd, left_before = left_opened
    right_fd, right_before = right_opened
    try:
        if left_before.st_size != right_before.st_size:
            return False
        with os.fdopen(left_fd, "rb", closefd=False) as left_fh, \
                os.fdopen(right_fd, "rb", closefd=False) as right_fh:
            while True:
                left_chunk = left_fh.read(CHUNK)
                right_chunk = right_fh.read(CHUNK)
                if left_chunk != right_chunk:
                    return False
                if not left_chunk:
                    return (_unchanged(left_before, os.fstat(left_fd))
                            and _unchanged(right_before, os.fstat(right_fd)))
    except OSError:
        return False
    finally:
        os.close(left_fd)
        os.close(right_fd)


def _bucket(files, key):
    groups = defaultdict(list)
    for f in files:
        k = key(f)
        if k is not None:
            groups[k].append(f)
    return [g for g in groups.values() if len(g) > 1]


def duplicates(files, min_size=4096, root=None):
    # Select one path per inode before opening any candidate. A hardlink alias
    # has the same bytes, so hashing it again would only repeat I/O. System-
    # managed and system-reserved paths are filtered here as a second boundary
    # for library callers as well as the CLI/TUI/report pre-filter.
    candidates = [
        f for f in storage.physical_records(files)
        if f.size >= min_size and managed.classify(f.path) is None
    ]
    groups = _bucket(candidates, lambda f: f.size)

    refined = []
    for group in groups:
        refined += _bucket(group, lambda f: _digest(f.path, HEAD,
                                                     expected=f, root=root))

    final = []
    for group in refined:
        for same in _bucket(group, lambda f: _digest(f.path, expected=f,
                                                      root=root)):
            if len(same) > 1:
                final.append(same)
    return final


def reclaimable(groups):
    """Return bytes an individual review action could actually release.

    A hardlinked path has more than one name for the same inode. Removing one
    name frees no storage, so only standalone physical copies count here.
    """
    return sum(storage.allocated_bytes(candidate)
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


def confirmed_duplicate_map(groups, root=None):
    """Keep only digest candidates that also pass a byte-for-byte comparison."""
    return {
        duplicate.path: survivor.path
        for group in groups
        for duplicate, survivor in _reviewable_duplicate_pairs(group)
        if same_content(duplicate.path, survivor.path,
                        expected_left=duplicate, expected_right=survivor,
                        root=root)
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
    copies = _physical_copies(
        info for info in group if managed.classify(info.path) is None)
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
