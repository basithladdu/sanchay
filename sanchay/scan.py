"""Walk a tree and record what is actually there.

One stat() per file, no content read. Content hashing happens later and only
for files whose size already collides, because hashing everything is what makes
naive dedup tools slow on large trees.
"""
import os
from dataclasses import dataclass


@dataclass
class FileInfo:
    path: str
    size: int
    atime: float
    mtime: float
    inode: int


def scan(root, skip=(".git/objects", "/proc", "/sys", "/dev")):
    files = []
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        if any(s in dirpath.replace("\\", "/") for s in skip):
            dirnames[:] = []
            continue
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                st = os.lstat(path)
            except OSError:
                continue
            if not os.path.isfile(path):
                continue
            files.append(FileInfo(path, st.st_size, st.st_atime, st.st_mtime, st.st_ino))
    return files
