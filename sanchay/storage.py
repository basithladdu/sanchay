"""Account for physical storage rather than directory-entry appearances.

Two hardlink paths name the same inode. They are useful paths to show a user,
but they do not consume two copies of the file's bytes. These helpers keep disk
totals, growth estimates, and duplicate decisions honest about that distinction.
"""


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
    """Count every physical inode at most once."""
    return sum(info.size for info in physical_records(files))


def hardlink_alias_count(files):
    """Count directory entries that do not add any physical bytes."""
    return max(0, len(files) - len(physical_records(files)))


def is_hardlinked(info):
    """Return whether removing this single path leaves its inode allocated."""
    return getattr(info, "nlink", 1) > 1


def _path_key(info):
    return str(info.path).replace("\\", "/")
