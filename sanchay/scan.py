"""Walk a tree and record what is actually there.

One stat() per file, no content read. Content hashing happens later and only
for files whose size already collides, because hashing everything is what makes
naive dedup tools slow on large trees.
"""
import os
import stat
from dataclasses import dataclass

from . import storage


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


def _is_protected_file(name):
    """Keep common credential material out of metadata and hash passes."""
    normalized = name.lower()
    if normalized in DEFAULT_SKIP_FILES or normalized.endswith(DEFAULT_SKIP_SUFFIXES):
        return True
    return (normalized.startswith(".env.")
            and normalized not in {".env.example", ".env.sample"})


def scan(root, skip=DEFAULT_SKIP_DIRS,
         cross_filesystems=False):
    """Return regular files below *root* without following symlinks.

    A default scan stays on the root filesystem. This prevents a workstation
    cleanup pass from silently traversing mounted network shares, removable
    media, or a separately governed system volume.
    """
    # Canonicalise the user-supplied root once.  All emitted paths then share
    # one stable root for later descriptor-relative content reads.
    root = os.path.realpath(os.path.abspath(root))
    if os.path.basename(os.path.normpath(root)) in skip:
        raise ValueError(f"Refusing to scan protected directory: {root}")
    try:
        root_device = os.stat(root).st_dev
    except OSError as exc:
        raise ValueError(f"Cannot scan {root}: {exc}") from exc

    files = []
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        # Prune at the parent so os.walk never descends into sensitive or
        # control directories. `skip` accepts directory basenames to keep this
        # policy portable across Linux and Windows paths.
        dirnames[:] = [name for name in dirnames if name not in skip]
        if not cross_filesystems:
            try:
                if os.stat(dirpath).st_dev != root_device:
                    dirnames[:] = []
                    continue
            except OSError:
                dirnames[:] = []
                continue
            # Avoid entering a mounted child at all, rather than only
            # detecting its different device after os.walk has entered it.
            same_filesystem = []
            for name in dirnames:
                try:
                    if os.stat(os.path.join(dirpath, name)).st_dev == root_device:
                        same_filesystem.append(name)
                except OSError:
                    continue
            dirnames[:] = same_filesystem
        for name in filenames:
            if _is_protected_file(name):
                continue
            path = os.path.join(dirpath, name)
            try:
                st = os.lstat(path)
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            files.append(FileInfo(path, st.st_size, st.st_atime, st.st_mtime,
                                  st.st_ino, st.st_dev, st.st_nlink,
                                  storage.allocated_bytes_from_stat(st),
                                  getattr(st, "st_mtime_ns", None)))
    return files
