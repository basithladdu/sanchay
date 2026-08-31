"""Account for allocated storage rather than directory-entry appearances.

Two hardlink paths name the same inode. They are useful paths to show a user,
but they do not consume two copies of the file's bytes. These helpers keep disk
totals, growth estimates, and duplicate decisions honest about that distinction.
On Linux, ``st_blocks * 512`` also avoids treating a sparse file's logical byte
length as if it were all allocated on disk.
"""


def allocated_bytes(info):
    """Return the filesystem allocation for one file, with a safe fallback.

    Python exposes POSIX ``st_blocks`` as units of 512 bytes where available.
    The scanner records that allocation. Platforms without that field fall
    back to the logical byte length instead of fabricating a block count.
    """
    allocated = getattr(info, "allocated_size", None)
    return info.size if allocated is None else allocated


def allocated_bytes_from_stat(stat_result):
    """Read the portable allocation measure from an ``os.stat`` result."""
    blocks = getattr(stat_result, "st_blocks", None)
    return stat_result.st_size if blocks is None else blocks * 512


def inode_identity(info):
    """Return a stable inode identity, falling back to a path when unavailable."""
    inode = getattr(info, "inode", None)
    if inode in (None, 0):
        return ("path", str(info.path).replace("\\", "/"))
    return ("inode", getattr(info, "device", 0), inode)


def physical_records(files):
    """Return one deterministic record per physical inode."""
    records = {}
    for info in files:
        identity = inode_identity(info)
        prior = records.get(identity)
        if prior is None or _path_key(info) < _path_key(prior):
            records[identity] = info
    return sorted(records.values(), key=_path_key)


def physical_bytes(files):
    """Count allocated bytes for every physical inode at most once."""
    return sum(allocated_bytes(info) for info in physical_records(files))


def logical_bytes(files):
    """Count logical lengths for every physical inode at most once."""
    return sum(info.size for info in physical_records(files))


def hardlink_alias_count(files):
    """Count directory entries that do not add any physical bytes."""
    return max(0, len(files) - len(physical_records(files)))


def is_hardlinked(info):
    """Return whether removing this single path leaves its inode allocated."""
    return getattr(info, "nlink", 1) > 1


def _path_key(info):
    return str(info.path).replace("\\", "/")
