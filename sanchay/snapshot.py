"""Persist local, mount-scoped snapshots for observed storage growth.

Mtime distributions can give a first-run hint. Later snapshots measure the
selected mounted filesystem's reported usage, while retaining a separate
readable-inventory aggregate for diagnosis. Snapshots contain counts and bytes
only; they never copy a file list or file contents.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from . import scan, storage


SNAPSHOT_SCHEMA_VERSION = 5
MIN_FORECAST_SPAN_SECONDS = 24 * 60 * 60


def _require_filesystem_accounting(document):
    """Reject snapshots without explicit mounted-filesystem measurements."""
    required = {
        "filesystem_total_bytes", "filesystem_used_bytes",
        "filesystem_free_bytes", "filesystem_device",
        "readable_inventory_allocated_bytes",
        "readable_inventory_logical_bytes",
    }
    if not required.issubset(document):
        raise ValueError("Snapshot is missing mounted-filesystem accounting")
    for field in required:
        value = document[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("Snapshot has invalid mounted-filesystem accounting")
    if (document["filesystem_used_bytes"] > document["filesystem_total_bytes"]
            or document["filesystem_free_bytes"] > document["filesystem_total_bytes"]):
        raise ValueError("Snapshot has invalid mounted-filesystem accounting")


def _require_complete_coverage(document):
    """Reject direct snapshot records that lack a complete coverage proof."""
    try:
        coverage = document["scan_coverage"]
        normalized = scan.coverage_summary(coverage)
        if coverage != normalized or not normalized["complete"]:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise ValueError("Snapshots must have complete SANCHAY scan coverage") from None
    return normalized


def capture(files, root, *, filesystem_total_bytes, filesystem_used_bytes,
            filesystem_free_bytes, filesystem_device, now=None,
            scan_coverage=None):
    """Capture aggregate inventory and mounted-filesystem measurements.

    The mounted filesystem metric is the only input to observed-growth and
    trend calculations. The readable inventory remains alongside it so an
    operator can distinguish an inventory result from filesystem capacity.
    """
    coverage = scan.coverage_summary(scan_coverage)
    if not coverage["complete"]:
        raise ValueError("Cannot capture a growth snapshot from incomplete scan coverage")
    accounting = {
        "filesystem_total_bytes": filesystem_total_bytes,
        "filesystem_used_bytes": filesystem_used_bytes,
        "filesystem_free_bytes": filesystem_free_bytes,
        "filesystem_device": filesystem_device,
        "readable_inventory_allocated_bytes": storage.physical_bytes(files),
        "readable_inventory_logical_bytes": storage.logical_bytes(files),
    }
    _require_filesystem_accounting(accounting)
    captured_at = now if now is not None else time.time()
    physical = storage.physical_records(files)
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "root": str(Path(root).resolve()),
        "captured_at": captured_at,
        "captured_at_iso": datetime.fromtimestamp(
            captured_at, tz=timezone.utc).isoformat(),
        "readable_file_count": len(files),
        "readable_physical_file_count": len(physical),
        "readable_hardlink_alias_count": len(files) - len(physical),
        **accounting,
        "scan_coverage": coverage,
    }


def write(snapshot, out):
    path = Path(out)
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    return str(path)


def read(path):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Unsupported SANCHAY snapshot; recapture it with mounted-filesystem accounting")
    required = {
        "schema_version", "root", "captured_at", "readable_file_count",
        "readable_physical_file_count", "readable_hardlink_alias_count",
        "scan_coverage",
    }
    if document.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("Unsupported SANCHAY snapshot; recapture it with mounted-filesystem accounting")
    try:
        _require_complete_coverage(document)
    except ValueError:
        raise ValueError("Snapshot does not have complete SANCHAY scan coverage") from None
    if not required.issubset(document):
        raise ValueError("Unsupported or incomplete SANCHAY snapshot; recapture it with mounted-filesystem accounting")
    _require_filesystem_accounting(document)
    return document


def observed_growth(previous, current):
    """Return measured growth, withholding a rate before a full-day span."""
    if (previous.get("schema_version") != SNAPSHOT_SCHEMA_VERSION
            or current.get("schema_version") != SNAPSHOT_SCHEMA_VERSION):
        raise ValueError("Snapshots must use SANCHAY mounted-filesystem accounting")
    _require_complete_coverage(previous)
    _require_complete_coverage(current)
    _require_filesystem_accounting(previous)
    _require_filesystem_accounting(current)
    if Path(previous["root"]) != Path(current["root"]):
        raise ValueError("Snapshot root does not match the current scan root")
    if previous["filesystem_device"] != current["filesystem_device"]:
        raise ValueError("Snapshot filesystem does not match the current scan filesystem")
    elapsed = current["captured_at"] - previous["captured_at"]
    if elapsed <= 0:
        return None
    delta = current["filesystem_used_bytes"] - previous["filesystem_used_bytes"]
    return {
        "elapsed_seconds": elapsed,
        "net_bytes": delta,
        "bytes_per_day": (delta * 86400 / elapsed
                          if elapsed >= MIN_FORECAST_SPAN_SECONDS else None),
        "minimum_span_seconds": MIN_FORECAST_SPAN_SECONDS,
    }


def linear_trend(snapshots):
    """Fit an explainable local linear trend to aggregate SANCHAY snapshots.

    This deliberately models only locally captured aggregate usage, not file
    names or content. The caller must present at least two distinct capture
    times from the same scan root.
    """
    if len(snapshots) < 2:
        return None
    if any(item.get("schema_version") != SNAPSHOT_SCHEMA_VERSION for item in snapshots):
        raise ValueError("Snapshots must use SANCHAY mounted-filesystem accounting")
    for item in snapshots:
        _require_complete_coverage(item)
        _require_filesystem_accounting(item)
    roots = {str(Path(item["root"])) for item in snapshots}
    if len(roots) != 1:
        raise ValueError("Snapshots must have the same scan root")
    devices = {item["filesystem_device"] for item in snapshots}
    if len(devices) != 1:
        raise ValueError("Snapshots must have the same mounted filesystem")

    points = sorted((float(item["captured_at"]),
                     float(item["filesystem_used_bytes"]))
                    for item in snapshots)
    if len({point[0] for point in points}) != len(points):
        raise ValueError("Snapshots must have distinct capture times")

    elapsed_seconds = points[-1][0] - points[0][0]
    if elapsed_seconds < MIN_FORECAST_SPAN_SECONDS:
        return {
            "sample_count": len(points),
            "elapsed_seconds": elapsed_seconds,
            "bytes_per_day": None,
            "r_squared": None,
            "minimum_span_seconds": MIN_FORECAST_SPAN_SECONDS,
        }

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
        "elapsed_seconds": elapsed_seconds,
        "bytes_per_day": bytes_per_day,
        "r_squared": r_squared,
        "minimum_span_seconds": MIN_FORECAST_SPAN_SECONDS,
    }
