"""Verify a retained archival copy without copying, moving, or deleting files.

An old or large file is not automatically safe to archive.  This module checks
only the narrow claim needed before a human can treat a retained copy as
recovery evidence: both paths are allowed regular files, they are separate
inodes, and their bytes and identities remain unchanged during comparison.
"""
import os
import stat

from . import dedup, managed, scan, storage


ARCHIVE_PROOF_SCHEMA_VERSION = 1


def _identity(observed):
    return {
        "device": observed.st_dev,
        "inode": observed.st_ino,
        "size": observed.st_size,
        "allocated_size": storage.allocated_bytes_from_stat(observed),
        "mtime": observed.st_mtime,
        "mtime_ns": getattr(observed, "st_mtime_ns", None),
        "nlink": observed.st_nlink,
    }


def _observe(path, role):
    """Return a stable identity for one explicitly chosen local file."""
    candidate = os.path.abspath(os.fspath(path))
    if scan.is_protected_path(candidate):
        raise ValueError(f"Refusing protected credential/control {role} path")
    if managed.classify(candidate) is not None:
        raise ValueError(f"Refusing system-managed or reserved {role} path")
    try:
        observed = os.lstat(candidate)
    except OSError as exc:
        raise ValueError(f"Cannot read {role}: {exc.strerror or exc}") from None
    if not stat.S_ISREG(observed.st_mode):
        raise ValueError(f"{role.capitalize()} is not a regular file")
    return candidate, _identity(observed)


def _shared_parent(left, right):
    """Find a descriptor-root for both paths when the platform has one."""
    try:
        return os.path.commonpath((os.path.dirname(left), os.path.dirname(right)))
    except ValueError:
        # Different Windows drives cannot have a lexical shared parent.  The
        # duplicate reader still uses no-follow protection for the final names.
        return None


def _storage_boundary(same_filesystem):
    if same_filesystem:
        return (
            "The files are separate inodes on the same filesystem. This can "
            "prove a retained survivor for a manual space-recovery review, "
            "but it is not an independent backup."
        )
    return (
        "The files are on different filesystems. This proves byte equivalence "
        "and separate inodes, not destination durability, retention, or a "
        "restore procedure."
    )


def verify(source, retained_copy):
    """Return an auditable, non-executing retained-copy verification record.

    ``verified`` means only that a named retained file was a separate inode
    with identical bytes for the duration of this check.  It never establishes
    a backup policy and never changes either file.
    """
    source_path, source_identity = _observe(source, "source")
    retained_path, retained_identity = _observe(retained_copy, "retained copy")
    same_inode = ((source_identity["device"], source_identity["inode"])
                  == (retained_identity["device"], retained_identity["inode"]))
    same_filesystem = source_identity["device"] == retained_identity["device"]
    result = {
        "schema_version": ARCHIVE_PROOF_SCHEMA_VERSION,
        "verified": False,
        "source": {"path": source_path, "identity": source_identity},
        "retained_copy": {"path": retained_path, "identity": retained_identity},
        "comparison": "byte_for_byte_stream",
        "separate_inode": not same_inode,
        "same_filesystem": same_filesystem,
        "reclaimable_allocated_bytes": (
            source_identity["allocated_size"] if source_identity["nlink"] == 1
            and not same_inode else 0
        ),
        "execution": {
            "automatic_copy": False,
            "automatic_deletion": False,
            "boundary": "SANCHAY verifies evidence only; it never copies, moves, or deletes files.",
        },
    }

    if same_inode:
        result["reason"] = (
            "source and retained copy are the same inode; removing one name "
            "would not reclaim physical storage"
        )
        return result
    if source_identity["size"] != retained_identity["size"]:
        result["reason"] = "source and retained copy have different logical sizes"
        return result

    matches = dedup.same_content(
        source_path, retained_path,
        expected_left=source_identity,
        expected_right=retained_identity,
        root=_shared_parent(source_path, retained_path),
    )
    try:
        _, source_after = _observe(source_path, "source")
        _, retained_after = _observe(retained_path, "retained copy")
    except ValueError as exc:
        result["reason"] = f"could not recheck file identity: {exc}"
        return result
    if source_after != source_identity or retained_after != retained_identity:
        result["reason"] = "file identity changed during verification"
        return result
    if not matches:
        result["reason"] = (
            "could not confirm a byte-for-byte match under the regular-file "
            "and no-follow read boundary"
        )
        return result

    result["verified"] = True
    result["storage_boundary"] = _storage_boundary(same_filesystem)
    return result
