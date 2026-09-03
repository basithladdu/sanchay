"""Platform-aware user artifact locations."""
import os
from pathlib import Path, PurePosixPath


def _running_under_wsl():
    if os.name == "nt":
        return False
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    try:
        release = Path("/proc/sys/kernel/osrelease").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "microsoft" in release.lower() or "wsl" in release.lower()


def scan_target(value):
    """Translate pasted Windows drive syntax when SANCHAY runs under WSL."""
    supplied = str(value).strip()
    is_drive_path = (
        len(supplied) >= 2
        and supplied[0].isalpha()
        and supplied[1] == ":"
        and (len(supplied) == 2 or supplied[2] in ("/", "\\"))
    )
    if not is_drive_path or not _running_under_wsl():
        return supplied

    mount = PurePosixPath("/mnt") / supplied[0].lower()
    if not Path(str(mount)).is_dir():
        raise ValueError(
            f"Windows drive {supplied[0].upper()}: is not mounted at {mount} in WSL")
    remainder = supplied[2:].lstrip("/\\").replace("\\", "/")
    return str(mount / remainder) if remainder else str(mount)


def downloads_directory():
    """Return the interactive report directory, with a test/admin override."""
    configured = os.environ.get("SANCHAY_DOWNLOAD_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / "Downloads").resolve()


def report_destination(name):
    """Place an HTML report in Downloads regardless of supplied directories."""
    directory = downloads_directory()
    directory.mkdir(parents=True, exist_ok=True)
    # Accept a pasted path for convenience, but keep only its filename. Using
    # both separators makes this deterministic on Windows and Linux.
    filename = str(name).replace("\\", "/").rsplit("/", 1)[-1].strip()
    if filename in ("", ".", ".."):
        raise ValueError("Report filename is empty")
    if not filename.lower().endswith(".html"):
        filename += ".html"
    return directory / filename
