"""Describe the boundary between filesystem use and a readable file inventory.

Directory scans cannot fully explain a filesystem's used blocks.  Protected
paths are intentionally omitted, files may be hidden under mounts, and Linux
filesystems can retain metadata, shared extents, snapshots, or deleted-open
inodes outside the visible tree.  This module quantifies only the observable
gap and never turns it into a cleanup action.
"""
from . import scan, storage


ACCOUNTING_SCHEMA_VERSION = 1
BOUNDARY = (
    "This is a readable-inventory accounting diagnostic, not a full filesystem "
    "reconciliation. Protected paths, filesystem metadata, snapshots or shared "
    "extents, mount-overlaid data, and inaccessible state can contribute to the gap."
)


def _unassessed(reason, coverage):
    return {
        "schema_version": ACCOUNTING_SCHEMA_VERSION,
        "assessed": False,
        "reason": reason,
        "scan_coverage": coverage,
        "boundary": BOUNDARY,
    }


def assess(files, filesystem_used_bytes, *, process_held_bytes=0,
           scan_coverage=None, root_is_mount=False, cross_filesystems=False):
    """Return a bounded accounting record for a complete single-mount scan.

    ``filesystem_used_bytes`` must be the mounted filesystem's reported used
    space.  The result intentionally calls any difference an accounting gap,
    not reclaimable or unexplained space.
    """
    coverage = scan.coverage_summary(scan_coverage)
    if cross_filesystems:
        return _unassessed(
            "capacity auditing is unavailable for a cross-filesystem inventory",
            coverage)
    if not root_is_mount:
        return _unassessed(
            "capacity auditing requires the selected root to be the mounted filesystem root",
            coverage)
    if not coverage["complete"]:
        return _unassessed(
            "capacity auditing requires complete readable-path coverage", coverage)
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
