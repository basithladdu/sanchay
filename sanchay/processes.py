"""Expose Linux files that were unlinked but are still held open.

Directory scans cannot see these files because their directory entry is gone,
but POSIX keeps their storage allocated until the last file descriptor closes.
This module only reports the situation through Linux ``/proc``. It never
signals a process, truncates a descriptor, or changes a file.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import stat

from . import storage


PROC_ROOT = Path("/proc")


@dataclass(frozen=True)
class DeletedFileHolder:
    """One observable process file descriptor holding a deleted file."""

    pid: int
    process: str
    fd: str
    path: str


@dataclass(frozen=True)
class DeletedOpenFile:
    """One physical deleted inode, potentially held by several descriptors."""

    device: int
    inode: int
    logical_size: int
    allocated_size: int
    holders: tuple


def available(proc_root=PROC_ROOT):
    """Return whether Linux process descriptors can be inspected."""
    return os.name == "posix" and Path(proc_root).is_dir()


def deleted_open_files(devices=None, proc_root=PROC_ROOT):
    """Return visible deleted regular files held open on selected devices.

    Permission changes and process exit races are normal while walking ``/proc``;
    inaccessible entries are simply omitted. ``devices`` limits the advisory to
    the filesystem(s) selected for the scan.
    """
    proc_root = Path(proc_root)
    if not available(proc_root):
        return []
    selected_devices = None if devices is None else set(devices)
    records = {}
    try:
        process_dirs = list(proc_root.iterdir())
    except OSError:
        return []

    for process_dir in process_dirs:
        if not process_dir.name.isdecimal():
            continue
        try:
            pid = int(process_dir.name)
            descriptors = list((process_dir / "fd").iterdir())
        except (OSError, ValueError):
            continue
        try:
            process = (process_dir / "comm").read_text(
                encoding="utf-8", errors="replace").strip() or "unknown"
        except OSError:
            process = "unknown"

        for descriptor in descriptors:
            try:
                path = os.readlink(descriptor)
                if not path.startswith("/") or not path.endswith(" (deleted)"):
                    continue
                observed = os.stat(descriptor)
            except OSError:
                continue
            if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 0:
                continue
            if selected_devices is not None and observed.st_dev not in selected_devices:
                continue

            identity = (observed.st_dev, observed.st_ino)
            record = records.setdefault(identity, {
                "logical_size": observed.st_size,
                "allocated_size": storage.allocated_bytes_from_stat(observed),
                "holders": [],
            })
            record["holders"].append(DeletedFileHolder(
                pid=pid, process=process, fd=descriptor.name, path=path))

    result = []
    for (device, inode), record in records.items():
        holders = tuple(sorted(record["holders"],
                               key=lambda holder: (holder.pid, holder.fd, holder.path)))
        result.append(DeletedOpenFile(
            device=device,
            inode=inode,
            logical_size=record["logical_size"],
            allocated_size=record["allocated_size"],
            holders=holders,
        ))
    return sorted(result, key=lambda item: (
        -item.allocated_size,
        item.holders[0].path if item.holders else "",
        item.device,
        item.inode,
    ))


def allocated_total(records):
    """Return allocated bytes once per deleted inode."""
    return sum(record.allocated_size for record in records)
