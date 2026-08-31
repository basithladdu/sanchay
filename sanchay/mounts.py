"""Read Linux mount context without changing filesystem or volume state.

SANCHAY's capacity claims are scoped to the selected mounted filesystem. Linux
mount information lets it surface important boundary conditions such as Btrfs,
overlay layers, and device-mapper sources without invoking administrative tools
or inferring that a file-level scan describes an entire host or volume group.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import posixpath
import re


MOUNTINFO = Path("/proc/self/mountinfo")


@dataclass(frozen=True)
class MountInfo:
    """The stable fields SANCHAY needs from one Linux mountinfo record."""

    mount_id: int
    parent_id: int
    device: str
    root: str
    mount_point: str
    filesystem: str
    source: str


def _unescape(value):
    """Decode the octal escapes defined by Linux procfs mountinfo."""
    return re.sub(r"\\([0-7]{3})",
                  lambda match: chr(int(match.group(1), 8)), value)


def parse(line):
    """Parse one mountinfo line, returning None for malformed input."""
    fields = line.split()
    try:
        separator = fields.index("-")
        if separator < 6 or len(fields) < separator + 4:
            return None
        return MountInfo(
            mount_id=int(fields[0]),
            parent_id=int(fields[1]),
            device=fields[2],
            root=_unescape(fields[3]),
            mount_point=_unescape(fields[4]),
            filesystem=fields[separator + 1],
            source=_unescape(fields[separator + 2]),
        )
    except (ValueError, IndexError):
        return None


def entries(mountinfo_path=MOUNTINFO):
    """Return observable mount records, or an empty tuple when unavailable."""
    try:
        lines = Path(mountinfo_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    return tuple(record for record in (parse(line) for line in lines)
                 if record is not None)


def _target_path(path):
    """Normalize a path for the POSIX mountpoint comparison."""
    raw = str(path)
    if os.name == "posix":
        raw = os.path.realpath(os.path.abspath(raw))
    return posixpath.normpath(raw.replace("\\", "/"))


def _contains(mount_point, target):
    mount_point = posixpath.normpath(mount_point)
    if mount_point == "/":
        return target.startswith("/")
    return target == mount_point or target.startswith(mount_point + "/")


def mount_for(path, mountinfo_path=MOUNTINFO):
    """Return the most specific observable mount containing *path*."""
    target = _target_path(path)
    matches = [record for record in entries(mountinfo_path)
               if _contains(record.mount_point, target)]
    return max(matches, key=lambda record: (len(record.mount_point),
                                             record.mount_id), default=None)


def _source_class(source):
    if source == "overlay":
        return "overlay_layer"
    if source.startswith("/dev/mapper/"):
        return "device_mapper"
    if source.startswith("/dev/"):
        return "block_device"
    if source in {"none", "-"}:
        return "unspecified"
    return "virtual_or_network_source"


def capacity_context(path, mountinfo_path=MOUNTINFO):
    """Return a serializable, read-only capacity context for a selected root.

    The result describes boundaries, not an automatic storage operation. A
    missing procfs record is normal on non-Linux hosts and simply returns None.
    """
    record = mount_for(path, mountinfo_path)
    if record is None:
        return None
    context = {
        "filesystem": record.filesystem,
        "mount_point": record.mount_point,
        "source_class": _source_class(record.source),
        "capacity_scope": "free-space and reclaim claims are scoped to this mounted filesystem",
    }
    if record.filesystem == "btrfs":
        context.update({
            "label": "Btrfs capacity boundary",
            "advisory": (
                "Btrfs shared extents, snapshots, metadata reservations, and "
                "block-group profiles can make directory totals differ from "
                "filesystem capacity."
            ),
            "review_action": (
                "If capacity disagrees with the scan, review `btrfs filesystem "
                "usage <mount>` and the snapshot policy. SANCHAY does not run "
                "a balance, delete a snapshot, or alter filesystem state."
            ),
        })
    elif record.filesystem == "overlay":
        context.update({
            "label": "Overlay filesystem boundary",
            "advisory": (
                "An overlay layer is not a host-wide capacity measurement; its "
                "writable layer is governed by the backing runtime and host "
                "filesystem."
            ),
            "review_action": (
                "Confirm the backing or upper filesystem with the container or "
                "host operator. SANCHAY does not claim that a layer scan frees "
                "host-wide storage."
            ),
        })
    elif record.source.startswith("/dev/mapper/"):
        context.update({
            "label": "Device-mapper capacity boundary",
            "advisory": (
                "Mounted filesystem free space does not establish logical-volume "
                "or thin-pool headroom beneath a device-mapper source."
            ),
            "review_action": (
                "Ask the platform owner to review the managed volume policy. "
                "SANCHAY does not run LVM commands, resize volumes, or infer "
                "encryption or thin-provisioning state."
            ),
        })
    return context
