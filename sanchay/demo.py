"""Create a harmless fixture for a real, repeatable SANCHAY demonstration."""
import argparse
import os
from pathlib import Path
import tempfile
import time


_DUPLICATE_BYTES = bytes(range(256)) * 2048
_CACHE_BYTES = b"regenerable-build-output\n" * 8192


def _write(path, content, age_days):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    when = time.time() - age_days * 86400
    os.utime(path, (when, when))


def create(root=None):
    """Create a disposable fixture and return its resolved root path.

    The caller may provide an empty directory. Refusing non-empty directories
    prevents a demo command from being mistaken for a cleanup command.
    """
    if root is None:
        fixture = Path(tempfile.mkdtemp(prefix="sanchay-demo-"))
    else:
        fixture = Path(root).expanduser().resolve()
        if fixture.exists() and not fixture.is_dir():
            raise ValueError(f"Demo root is not a directory: {fixture}")
        if fixture.exists() and any(fixture.iterdir()):
            raise ValueError(f"Refusing to write into non-empty directory: {fixture}")
        fixture.mkdir(parents=True, exist_ok=True)

    _write(fixture / "workspace" / "node_modules" / ".cache" / "bundle.bin",
           _CACHE_BYTES, age_days=45)
    _write(fixture / "archive" / "boss-image.iso", _DUPLICATE_BYTES, age_days=120)
    _write(fixture / "downloads" / "boss-image-copy.iso", _DUPLICATE_BYTES,
           age_days=120)
    _write(fixture / "documents" / "capstone-thesis.txt",
           b"This is a unique demonstration document.\n", age_days=300)

    hardlink_source = fixture / "hardlinks" / "source.bin"
    _write(hardlink_source, b"one physical file, two directory entries\n" * 2048,
           age_days=90)
    os.link(hardlink_source, fixture / "hardlinks" / "alias.bin")
    return fixture


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="sanchay-demo",
        description="create a disposable SANCHAY demonstration fixture")
    parser.add_argument("root", nargs="?", help="empty directory for the fixture")
    args = parser.parse_args(argv)
    fixture = create(args.root)
    print(f"fixture -> {fixture}")
    print(f"scan    -> sanchay {fixture} --plan cleanup-plan.json --snapshot baseline.json")
    print("verify  -> sanchay --verify-plan cleanup-plan.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
