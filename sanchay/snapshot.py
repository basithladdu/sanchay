"""Persist lightweight local snapshots for observed storage growth.

Mtime distributions can give a first-run hint, but a later scan is the only
way to measure net growth reliably. Snapshots contain aggregate counts and
bytes only; they never copy a file list or file contents.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from . import storage


def capture(files, root, free_bytes, now=None):
    captured_at = now if now is not None else time.time()
    physical = storage.physical_records(files)
    return {
        "schema_version": 2,
        "root": str(Path(root).resolve()),
        "captured_at": captured_at,
        "captured_at_iso": datetime.fromtimestamp(
            captured_at, tz=timezone.utc).isoformat(),
        "file_count": len(files),
        "physical_file_count": len(physical),
        "hardlink_alias_count": len(files) - len(physical),
        "used_bytes": sum(file.size for file in physical),
        "free_bytes": free_bytes,
    }


def write(snapshot, out):
    path = Path(out)
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    return str(path)


def read(path):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"schema_version", "root", "captured_at", "used_bytes",
                "physical_file_count", "hardlink_alias_count"}
    if document.get("schema_version") != 2 or not required.issubset(document):
        raise ValueError("Unsupported or incomplete SANCHAY snapshot; capture a new physical-byte snapshot")
    return document


def observed_growth(previous, current):
    """Return a measured net-growth rate, or None for incompatible snapshots."""
    if previous.get("schema_version") != 2 or current.get("schema_version") != 2:
        raise ValueError("Snapshots must use SANCHAY physical-byte accounting")
    if Path(previous["root"]) != Path(current["root"]):
        raise ValueError("Snapshot root does not match the current scan root")
    elapsed = current["captured_at"] - previous["captured_at"]
    if elapsed <= 0:
        return None
    delta = current["used_bytes"] - previous["used_bytes"]
    return {
        "elapsed_seconds": elapsed,
        "net_bytes": delta,
        "bytes_per_day": delta * 86400 / elapsed,
    }


def linear_trend(snapshots):
    """Fit an explainable local linear trend to aggregate SANCHAY snapshots.

    This deliberately models only locally captured aggregate usage, not file
    names or content. The caller must present at least two distinct capture
    times from the same scan root.
    """
    if len(snapshots) < 2:
        return None
    roots = {str(Path(item["root"])) for item in snapshots}
    if len(roots) != 1:
        raise ValueError("Snapshots must have the same scan root")

    points = sorted((float(item["captured_at"]), float(item["used_bytes"]))
                    for item in snapshots)
    if len({point[0] for point in points}) != len(points):
        raise ValueError("Snapshots must have distinct capture times")

    origin = points[0][0]
    x_values = [(captured_at - origin) / 86400 for captured_at, _ in points]
    y_values = [used_bytes for _, used_bytes in points]
    mean_x = sum(x_values) / len(x_values)
    mean_y = sum(y_values) / len(y_values)
    variance_x = sum((value - mean_x) ** 2 for value in x_values)
    if variance_x == 0:
        return None
    bytes_per_day = sum((x - mean_x) * (y - mean_y)
                        for x, y in zip(x_values, y_values)) / variance_x
    intercept = mean_y - bytes_per_day * mean_x
    residual = sum((y - (intercept + bytes_per_day * x)) ** 2
                   for x, y in zip(x_values, y_values))
    total = sum((y - mean_y) ** 2 for y in y_values)
    # A two-point line always fits perfectly; only expose fit quality once the
    # trend has a third independent observation to challenge it.
    r_squared = None if len(points) < 3 or total == 0 else max(0.0, 1 - residual / total)
    return {
        "sample_count": len(points),
        "elapsed_seconds": points[-1][0] - points[0][0],
        "bytes_per_day": bytes_per_day,
        "r_squared": r_squared,
    }
