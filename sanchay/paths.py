"""Platform-aware user artifact locations."""
import os
from pathlib import Path


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
