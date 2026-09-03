"""Walk a tree and record what is actually there.

One stat() per file, no content read. Content hashing happens later and only
for files whose size already collides, because hashing everything is what makes
naive dedup tools slow on large trees.
"""
import os
import stat
from concurrent.futures import CancelledError
from dataclasses import dataclass

from . import mounts, storage


def _check_cancel(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise CancelledError("scan cancelled")


# These contain repository internals or credential material rather than user
# storage candidates. Prune them before metadata collection and before any
# duplicate-candidate hashing can open a file.
DEFAULT_SKIP_DIRS = frozenset({
    ".aws", ".azure", ".docker", ".git", ".gnupg", ".hg", ".kube",
    ".oci", ".password-store", ".pki", ".ssh", ".svn", ".terraform.d",
})
DEFAULT_SKIP_FILES = frozenset({
    ".boto", ".env", ".git-credentials", ".netrc", ".npmrc", ".pypirc",
    ".terraformrc", "credentials", "credentials.json", "credentials.tfrc.json",
    "id_dsa", "id_ecdsa", "id_ed25519", "id_rsa", "secrets.json",
})
DEFAULT_SKIP_SUFFIXES = (".kdbx", ".key", ".p12", ".pem", ".pfx")


@dataclass
class FileInfo:
    path: str
    size: int
    atime: float
    mtime: float
    inode: int
    device: int = 0
    nlink: int = 1
    # Logical byte length remains necessary for duplicate matching. The
    # allocated size is what a filesystem can actually return on deletion.
    # It is None only when the platform does not expose block allocation.
    allocated_size: int = None
    # A nanosecond mtime makes later identity rechecks less dependent on the
    # display-oriented float field's filesystem timestamp precision.
    mtime_ns: int = None


@dataclass(frozen=True)
class ScanCoverage:
    """Counts eligible paths that could not be inspected during a scan.

    The counts deliberately avoid storing inaccessible path names. They make an
    incomplete inventory visible without adding potentially sensitive system
    paths to a plan, snapshot, or report.
    """
    unreadable_directories: int = 0
    unreadable_files: int = 0

    @property
    def complete(self):
        return not (self.unreadable_directories or self.unreadable_files)

    def as_dict(self):
        return coverage_summary(self)


def coverage_summary(coverage=None):
    """Return a serialisable, internally consistent scan-coverage record."""
    if coverage is None:
        directories = files = 0
    elif isinstance(coverage, ScanCoverage):
        directories = coverage.unreadable_directories
        files = coverage.unreadable_files
    elif isinstance(coverage, dict):
        directories = coverage.get("unreadable_directories", 0)
        files = coverage.get("unreadable_files", 0)
    else:
        raise ValueError("Scan coverage must be a ScanCoverage record or mapping")

    if (isinstance(directories, bool) or isinstance(files, bool)
            or not isinstance(directories, int) or not isinstance(files, int)
            or directories < 0 or files < 0):
        raise ValueError("Scan coverage counts must be non-negative integers")

    complete = not (directories or files)
    if isinstance(coverage, dict) and "complete" in coverage:
        if coverage["complete"] is not complete:
            raise ValueError("Scan coverage completeness does not match its counts")
    return {
        "complete": complete,
        "unreadable_directories": directories,
        "unreadable_files": files,
        "boundary": (
            "all in-scope, non-sensitive paths were inspected"
            if complete else
            "some in-scope paths could not be inspected; inventory and growth "
            "claims apply only to readable files"
        ),
    }


def _is_protected_file(name):
    """Keep common credential material out of metadata and hash passes."""
    normalized = name.lower()
    if normalized in DEFAULT_SKIP_FILES or normalized.endswith(DEFAULT_SKIP_SUFFIXES):
        return True
    return (normalized.startswith(".env.")
            and normalized not in {".env.example", ".env.sample"})


def _path_is_protected(path, protected_dirs):
    parts = [part for part in str(path).replace("\\", "/").split("/")
             if part not in {"", "."}]
    return (any(part.lower() in protected_dirs for part in parts)
            or bool(parts) and _is_protected_file(parts[-1]))


def is_protected_path(path, skip=DEFAULT_SKIP_DIRS):
    """Return whether a path is a known credential or control path.

    This public predicate lets callers that already hold ``FileInfo`` records
    preserve the same metadata and content-read boundary as :func:`scan`.
    It is intentionally a conservative path policy, not a claim that every
    sensitive file can be identified by its name.
    """
    protected_dirs = frozenset(str(name).lower() for name in skip)
    return _path_is_protected(path, protected_dirs)


def scan_with_coverage(root, skip=DEFAULT_SKIP_DIRS,
                       cross_filesystems=False, cancel_event=None):
    """Return regular files plus honest coverage evidence for one tree.

    A default scan stays on the root filesystem and prunes every visible child
    mount point, including a same-device bind mount. This prevents a workstation
    cleanup pass from silently traversing mounted network shares, removable
    media, separately governed system volumes, or a recursive bind-mounted
    view of an already visited tree. Credential/control paths are intentionally
    pruned under a separate safety policy; coverage reports only unexpected
    traversal or metadata failures for otherwise in-scope paths.
    """
    # Canonicalise the user-supplied root once.  All emitted paths then share
    # one stable root for later descriptor-relative content reads.
    _check_cancel(cancel_event)
    root = os.path.realpath(os.path.abspath(root))
    protected_dirs = frozenset(str(name).lower() for name in skip)
    if _path_is_protected(root, protected_dirs):
        raise ValueError(f"Refusing to scan protected directory: {root}")
    try:
        root_device = os.stat(root).st_dev
    except OSError as exc:
        raise ValueError(f"Cannot scan {root}: {exc}") from exc

    def path_key(path):
        return os.path.normcase(os.path.realpath(os.path.abspath(path)))

    # On Linux, a child mount can have the same st_dev as the selected root
    # (for example, a bind mount). Device filtering alone would then walk a
    # foreign or recursive namespace view. The default single-filesystem mode
    # keeps these child mounts outside its inventory; their count is surfaced
    # separately through mounts.capacity_context().
    nested_mount_points = (
        frozenset(path_key(record.mount_point)
                  for record in mounts.nested_mounts(root))
        if not cross_filesystems else frozenset()
    )

    files = []
    unreadable_directories = 0
    unreadable_files = 0
    visited_directories = set()

    def record_directory_error(_error):
        nonlocal unreadable_directories
        unreadable_directories += 1

    for dirpath, dirnames, filenames in os.walk(root, onerror=record_directory_error):
        _check_cancel(cancel_event)
        # Prune at the parent so os.walk never descends into sensitive or
        # control directories. `skip` accepts directory basenames to keep this
        # policy portable across Linux and Windows paths.
        dirnames[:] = [
            name for name in dirnames
            if not _path_is_protected(os.path.join(dirpath, name), protected_dirs)
        ]
        try:
            directory_stat = os.stat(dirpath)
        except OSError:
            unreadable_directories += 1
            dirnames[:] = []
            continue
        directory_identity = (directory_stat.st_dev, directory_stat.st_ino)
        if directory_identity in visited_directories:
            # A bind mount can expose an ancestor again. In explicit
            # cross-filesystem mode, inventory it once rather than allowing an
            # infinite recursive walk or duplicate physical records.
            dirnames[:] = []
            continue
        visited_directories.add(directory_identity)
        if not cross_filesystems:
            if directory_stat.st_dev != root_device:
                dirnames[:] = []
                continue
            # Avoid entering a mounted child at all, rather than only
            # detecting its different device after os.walk has entered it.
            same_filesystem = []
            for name in dirnames:
                child_path = os.path.join(dirpath, name)
                if path_key(child_path) in nested_mount_points:
                    continue
                try:
                    if os.stat(child_path).st_dev == root_device:
                        same_filesystem.append(name)
                except OSError:
                    unreadable_directories += 1
                    continue
            dirnames[:] = same_filesystem
        for name in filenames:
            _check_cancel(cancel_event)
            path = os.path.join(dirpath, name)
            if _path_is_protected(path, protected_dirs):
                continue
            if not cross_filesystems and path_key(path) in nested_mount_points:
                continue
            try:
                st = os.lstat(path)
            except OSError:
                unreadable_files += 1
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            if not cross_filesystems and st.st_dev != root_device:
                continue
            files.append(FileInfo(path, st.st_size, st.st_atime, st.st_mtime,
                                  st.st_ino, st.st_dev, st.st_nlink,
                                  storage.allocated_bytes_from_stat(st),
                                  getattr(st, "st_mtime_ns", None)))
    return files, ScanCoverage(unreadable_directories, unreadable_files)


def scan(root, skip=DEFAULT_SKIP_DIRS,
         cross_filesystems=False, cancel_event=None):
    """Return regular files below *root* without following symlinks.

    This compatibility API returns only files. Call :func:`scan_with_coverage`
    when an operator-visible completeness boundary is required.
    """
    return scan_with_coverage(root, skip=skip,
                              cross_filesystems=cross_filesystems,
                              cancel_event=cancel_event)[0]
