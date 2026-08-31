"""Describe the boundary between filesystem use and a readable file inventory.

Directory scans cannot fully explain a filesystem's used blocks.  Protected
paths are intentionally omitted, files may be hidden under mounts, and Linux
filesystems can retain metadata, shared extents, snapshots, or deleted-open
inodes outside the visible tree.  This module quantifies only the observable
gap and never turns it into a cleanup action.
"""
import os

from . import scan, storage


ACCOUNTING_SCHEMA_VERSION = 1
INODE_CAPACITY_SCHEMA_VERSION = 1
BLOCK_AVAILABILITY_SCHEMA_VERSION = 1
BOUNDARY = (
    "This is a readable-inventory accounting diagnostic, not a full filesystem "
    "reconciliation. Protected paths, filesystem metadata, snapshots or shared "
    "extents, mount-overlaid data, and inaccessible state can contribute to the gap."
)
INODE_BOUNDARY = (
    "This is a mount-level inode/file-entry capacity observation, not a cleanup "
    "recommendation or a diagnosis. It cannot identify a safe file to remove, "
    "and some filesystems do not expose meaningful inode counters."
)
BLOCK_AVAILABILITY_BOUNDARY = (
    "This is a mount-level block-availability observation, not a cleanup "
    "recommendation or a diagnosis. Free blocks that are unavailable to an "
    "unprivileged process can reflect filesystem policy; this does not identify "
    "bytes to remove or authorize a policy change."
)


def _unassessed(reason, coverage):
    return {
        "schema_version": ACCOUNTING_SCHEMA_VERSION,
        "assessed": False,
        "reason": reason,
        "scan_coverage": coverage,
        "boundary": BOUNDARY,
    }


def _inode_unassessed(reason, coverage):
    return {
        "schema_version": INODE_CAPACITY_SCHEMA_VERSION,
        "assessed": False,
        "reason": reason,
        "scan_coverage": coverage,
        "boundary": INODE_BOUNDARY,
    }


def _block_unassessed(reason, coverage):
    return {
        "schema_version": BLOCK_AVAILABILITY_SCHEMA_VERSION,
        "assessed": False,
        "reason": reason,
        "scan_coverage": coverage,
        "boundary": BLOCK_AVAILABILITY_BOUNDARY,
    }


def _capacity_gate(*, scan_coverage, root_is_mount, cross_filesystems,
                   unavailable):
    """Return an unassessed reason when this is not one complete mount scan."""
    coverage = scan.coverage_summary(scan_coverage)
    if cross_filesystems:
        return unavailable(
            "capacity auditing is unavailable for a cross-filesystem inventory",
            coverage)
    if not root_is_mount:
        return unavailable(
            "capacity auditing requires the selected root to be the mounted filesystem root",
            coverage)
    if not coverage["complete"]:
        return unavailable(
            "capacity auditing requires complete readable-path coverage", coverage)
    return None


def _non_negative_int(value):
    return (value if isinstance(value, int) and not isinstance(value, bool)
            and value >= 0 else None)


def _statvfs(root, *, scan_coverage, unavailable):
    """Read POSIX mount statistics without leaking a target path in failures."""
    statvfs = getattr(os, "statvfs", None)
    if not callable(statvfs):
        return None, unavailable(
            "POSIX capacity counters are unavailable because this platform has no statvfs support",
            scan.coverage_summary(scan_coverage))
    try:
        return statvfs(root), None
    except OSError as exc:
        return None, unavailable(
            "POSIX capacity counters are unavailable from this filesystem "
            f"({type(exc).__name__})", scan.coverage_summary(scan_coverage))


def assess_block_availability(root, *, scan_coverage=None, root_is_mount=False,
                              cross_filesystems=False):
    """Read POSIX block availability without suggesting a filesystem change."""
    gate = _capacity_gate(
        scan_coverage=scan_coverage, root_is_mount=root_is_mount,
        cross_filesystems=cross_filesystems, unavailable=_block_unassessed)
    if gate:
        return gate

    stats, unavailable = _statvfs(
        root, scan_coverage=scan_coverage, unavailable=_block_unassessed)
    if unavailable:
        return unavailable
    fragment = _non_negative_int(getattr(stats, "f_frsize", None))
    if not fragment:
        fragment = _non_negative_int(getattr(stats, "f_bsize", None))
    total_blocks = _non_negative_int(getattr(stats, "f_blocks", None))
    free_blocks = _non_negative_int(getattr(stats, "f_bfree", None))
    available_blocks = _non_negative_int(getattr(stats, "f_bavail", None))
    if (not fragment or total_blocks is None or total_blocks == 0
            or free_blocks is None
            or available_blocks is None or free_blocks > total_blocks
            or available_blocks > free_blocks):
        return _block_unassessed(
            "this filesystem does not report usable block-availability counters",
            scan.coverage_summary(scan_coverage))

    return {
        "schema_version": BLOCK_AVAILABILITY_SCHEMA_VERSION,
        "assessed": True,
        "total_bytes": total_blocks * fragment,
        "used_bytes": (total_blocks - free_blocks) * fragment,
        "free_bytes": free_blocks * fragment,
        "available_bytes": available_blocks * fragment,
        "free_unavailable_to_unprivileged_bytes": (
            free_blocks - available_blocks) * fragment,
        "scan_coverage": scan.coverage_summary(scan_coverage),
        "boundary": BLOCK_AVAILABILITY_BOUNDARY,
    }


def assess_inode_capacity(root, *, scan_coverage=None, root_is_mount=False,
                          cross_filesystems=False):
    """Read POSIX inode/file-entry counters as a strictly advisory diagnostic.

    ``statvfs`` is available on Unix platforms.  Its file-entry fields expose
    mount-level capacity, not a count of the readable files SANCHAY saw.  The
    same complete, one-mount preconditions as the byte accounting audit avoid
    mixing an inventory from one scope with capacity from another.
    """
    gate = _capacity_gate(
        scan_coverage=scan_coverage, root_is_mount=root_is_mount,
        cross_filesystems=cross_filesystems, unavailable=_inode_unassessed)
    if gate:
        return gate

    stats, unavailable = _statvfs(
        root, scan_coverage=scan_coverage, unavailable=_inode_unassessed)
    if unavailable:
        return unavailable

    total = _non_negative_int(getattr(stats, "f_files", None))
    free = _non_negative_int(getattr(stats, "f_ffree", None))
    available = _non_negative_int(getattr(stats, "f_favail", None))
    if total is None or total == 0 or free is None or free > total:
        return _inode_unassessed(
            "this filesystem does not report usable inode/file-entry capacity",
            scan.coverage_summary(scan_coverage))
    if available is not None and available > total:
        available = None

    used = total - free
    return {
        "schema_version": INODE_CAPACITY_SCHEMA_VERSION,
        "assessed": True,
        "total_inodes": total,
        "free_inodes": free,
        "available_inodes": available,
        "used_inodes": used,
        "used_percent": round((used * 100) / total, 1),
        "scan_coverage": scan.coverage_summary(scan_coverage),
        "boundary": INODE_BOUNDARY,
    }


def assess(files, filesystem_used_bytes, *, process_held_bytes=0,
           scan_coverage=None, root_is_mount=False, cross_filesystems=False):
    """Return a bounded accounting record for a complete single-mount scan.

    ``filesystem_used_bytes`` must be the mounted filesystem's reported used
    space.  The result intentionally calls any difference an accounting gap,
    not reclaimable or unexplained space.
    """
    gate = _capacity_gate(
        scan_coverage=scan_coverage, root_is_mount=root_is_mount,
        cross_filesystems=cross_filesystems, unavailable=_unassessed)
    if gate:
        return gate
    coverage = scan.coverage_summary(scan_coverage)
    if (isinstance(filesystem_used_bytes, bool)
            or not isinstance(filesystem_used_bytes, int)
            or filesystem_used_bytes < 0):
        raise ValueError("Filesystem used bytes must be a non-negative integer")
    if (isinstance(process_held_bytes, bool)
            or not isinstance(process_held_bytes, int)
            or process_held_bytes < 0):
        raise ValueError("Process-held bytes must be a non-negative integer")

    readable_file_bytes = storage.physical_bytes(files)
    visible_accounted_bytes = readable_file_bytes + process_held_bytes
    gap = filesystem_used_bytes - visible_accounted_bytes
    direction = (
        "filesystem_used_exceeds_visible_accounting" if gap > 0 else
        "visible_accounting_exceeds_filesystem_used" if gap < 0 else
        "visible_accounting_matches_filesystem_used"
    )
    return {
        "schema_version": ACCOUNTING_SCHEMA_VERSION,
        "assessed": True,
        "filesystem_used_bytes": filesystem_used_bytes,
        "readable_file_allocated_bytes": readable_file_bytes,
        "deleted_open_allocated_bytes": process_held_bytes,
        "visible_accounted_bytes": visible_accounted_bytes,
        "accounting_gap_bytes": gap,
        "gap_direction": direction,
        "scan_coverage": coverage,
        "boundary": BOUNDARY,
    }
