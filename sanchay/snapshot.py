"""Persist local, mount-scoped snapshots for observed storage growth.

Mtime distributions can give a first-run hint. Later snapshots measure the
selected mounted filesystem's reported usage, while retaining a separate
readable-inventory aggregate for diagnosis. Snapshots contain counts and bytes
only; they never copy a file list or file contents.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
from pathlib import Path
import time

from . import scan, storage


SNAPSHOT_SCHEMA_VERSION = 6
MIN_FORECAST_SPAN_SECONDS = 24 * 60 * 60
# A two-point line always has a perfect apparent fit.  SANCHAY therefore
# treats a rate from two captures as useful observation, but not as enough
# evidence to issue an exhaustion-date projection.
MIN_RUNWAY_SNAPSHOT_COUNT = 3
MIN_RUNWAY_R_SQUARED = 0.80
# A capacity-hit probability needs more than a line through two or three
# captures. Seven locally observed points across a week create six separate
# increments from which the local drift and variability can be estimated. Each
# interval must itself be meaningfully separated so rapid repeated scans do not
# masquerade as independent capacity observations.
MIN_RISK_SNAPSHOT_COUNT = 7
MIN_RISK_SPAN_SECONDS = 7 * 24 * 60 * 60
MIN_RISK_INTERVAL_SECONDS = 12 * 60 * 60
CAPACITY_RISK_MODEL = "brownian_motion_with_drift_hitting_risk"
_LOG_SQRT_2PI = 0.5 * math.log(2 * math.pi)


class SnapshotIntegrityError(ValueError):
    """Raised when a stored aggregate snapshot no longer matches its checksum."""


def _fingerprint(document):
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fingerprint_valid(document):
    """Return whether an aggregate snapshot still matches its stored checksum.

    The checksum detects a mismatch against its stored aggregate content; it
    is deliberately not a signature, device attestation, or authorization to
    take a storage action.
    """
    claimed = document.get("fingerprint_sha256") if isinstance(document, dict) else None
    unsigned = ({key: value for key, value in document.items()
                 if key != "fingerprint_sha256"}
                if isinstance(document, dict) else {})
    return (isinstance(claimed, str)
            and hmac.compare_digest(claimed, _fingerprint(unsigned)))


def _normal_survival(value):
    """Return the upper tail of a standard normal distribution."""
    return 0.5 * math.erfc(value / math.sqrt(2.0))


def _log_normal_survival(value):
    """Return log(P(Z > value)) without underflowing in a far tail.

    The capacity hitting formula has an exponential multiplied by a normal
    tail. Computing those terms independently can overflow for ordinary byte
    values even when their product is small. The asymptotic tail expansion is
    sufficient beyond eight standard deviations and keeps that product finite.
    """
    if value < 8.0:
        return math.log(_normal_survival(value))
    inverse_square = 1.0 / (value * value)
    correction = (1.0 - inverse_square + 3.0 * inverse_square ** 2
                  - 15.0 * inverse_square ** 3
                  + 105.0 * inverse_square ** 4)
    return (-0.5 * value * value - _LOG_SQRT_2PI - math.log(value)
            + math.log(correction))


def _probability_from_log(value):
    """Convert a log probability to a finite closed-unit probability."""
    if value <= -745.0:
        return 0.0
    return min(1.0, math.exp(min(0.0, value)))


def _risk_withheld(horizon_days, sample_count, elapsed_seconds, reason):
    """Make a non-assessment explicit instead of emitting a fake zero risk."""
    return {
        "assessed": False,
        "model": CAPACITY_RISK_MODEL,
        "horizon_days": horizon_days,
        "sample_count": sample_count,
        "elapsed_seconds": elapsed_seconds,
        "minimum_sample_count": MIN_RISK_SNAPSHOT_COUNT,
        "minimum_span_seconds": MIN_RISK_SPAN_SECONDS,
        "minimum_interval_seconds": MIN_RISK_INTERVAL_SECONDS,
        "reason": reason,
        "boundary": (
            "A local capacity-risk estimate is withheld when the historical "
            "evidence is too weak or the mounted capacity changed. It never "
            "authorizes a cleanup, volume action, or alert."
        ),
    }


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
    document = {
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
    document["fingerprint_sha256"] = _fingerprint(document)
    return document


def write(snapshot, out):
    """Write a new snapshot without replacing an existing evidence artifact."""
    path = Path(out)
    if (isinstance(snapshot, dict)
            and snapshot.get("schema_version") == SNAPSHOT_SCHEMA_VERSION
            and not fingerprint_valid(snapshot)):
        raise SnapshotIntegrityError(
            "refusing to write a snapshot whose integrity checksum does not match")
    with path.open("x", encoding="utf-8") as artifact:
        artifact.write(json.dumps(snapshot, indent=2) + "\n")
    return str(path)


def read(path):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Unsupported SANCHAY snapshot; recapture it with mounted-filesystem accounting")
    required = {
        "schema_version", "root", "captured_at", "readable_file_count",
        "readable_physical_file_count", "readable_hardlink_alias_count",
        "scan_coverage", "fingerprint_sha256",
    }
    if document.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("Unsupported SANCHAY snapshot; recapture it with mounted-filesystem accounting")
    try:
        _require_complete_coverage(document)
    except ValueError:
        raise ValueError("Snapshot does not have complete SANCHAY scan coverage") from None
    if not required.issubset(document):
        raise ValueError("Unsupported or incomplete SANCHAY snapshot; recapture it with mounted-filesystem accounting")
    if not fingerprint_valid(document):
        raise SnapshotIntegrityError("snapshot integrity checksum does not match")
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
        "sample_count": 2,
        "elapsed_seconds": elapsed,
        "net_bytes": delta,
        "bytes_per_day": (delta * 86400 / elapsed
                          if elapsed >= MIN_FORECAST_SPAN_SECONDS else None),
        "r_squared": None,
        "capacity_stable": (
            previous["filesystem_total_bytes"] == current["filesystem_total_bytes"]
        ),
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
    capacity_stable = len({item["filesystem_total_bytes"]
                           for item in snapshots}) == 1

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
            "capacity_stable": capacity_stable,
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
        "capacity_stable": capacity_stable,
        "minimum_span_seconds": MIN_FORECAST_SPAN_SECONDS,
    }


def runway_readiness(measurement):
    """Return whether a measured growth rate supports a runway projection.

    This is intentionally a conservative product gate rather than a claim that
    a linear forecast is statistically guaranteed. It keeps an observed rate
    visible, while rejecting a date extrapolated from an uncheckable two-point
    line or a weakly fitting history.
    """
    if not isinstance(measurement, dict):
        return {
            "ready": False,
            "reason": "no measured growth record is available",
        }
    if measurement.get("capacity_stable") is False:
        return {
            "ready": False,
            "reason": (
                "mounted filesystem capacity changed between snapshots; "
                "runway projection is withheld"
            ),
        }
    rate = measurement.get("bytes_per_day")
    if (isinstance(rate, bool) or not isinstance(rate, (int, float))
            or not math.isfinite(rate) or rate <= 0):
        return {
            "ready": False,
            "reason": "a measured rate is not available yet",
        }
    sample_count = measurement.get("sample_count")
    if (isinstance(sample_count, bool) or not isinstance(sample_count, int)
            or sample_count < MIN_RUNWAY_SNAPSHOT_COUNT):
        return {
            "ready": False,
            "reason": (
                f"at least {MIN_RUNWAY_SNAPSHOT_COUNT} snapshots are required "
                "to assess trend fit"
            ),
        }
    r_squared = measurement.get("r_squared")
    if (isinstance(r_squared, bool) or not isinstance(r_squared, (int, float))
            or not math.isfinite(r_squared) or not 0 <= r_squared <= 1
            or r_squared < MIN_RUNWAY_R_SQUARED):
        return {
            "ready": False,
            "reason": (
                f"trend fit is below the R-squared {MIN_RUNWAY_R_SQUARED:.2f} "
                "projection threshold"
            ),
        }
    return {"ready": True, "reason": None}


def capacity_risk(snapshots, horizon_days):
    """Estimate local capacity-hit risk within a requested number of days.

    This is an explainable Brownian-motion-with-drift hitting-time estimate on
    aggregate mounted-filesystem used bytes. It deliberately requires more
    history than the simple local slope, holds back when capacity changed, and
    reports a probability only under the model assumptions. It never performs
    a cleanup, mount, volume, alert, or network action.
    """
    if (isinstance(horizon_days, bool) or not isinstance(horizon_days, int)
            or horizon_days <= 0):
        raise ValueError("Capacity risk horizon must be a positive whole number of days")
    snapshots = tuple(snapshots)
    sample_count = len(snapshots)
    if sample_count < 2:
        return _risk_withheld(
            horizon_days, sample_count, 0,
            f"at least {MIN_RISK_SNAPSHOT_COUNT} complete snapshots are required")
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
    try:
        points = sorted(
            (float(item["captured_at"]), float(item["filesystem_used_bytes"]),
             int(item["filesystem_total_bytes"]), int(item["filesystem_free_bytes"]))
            for item in snapshots)
    except (TypeError, ValueError) as exc:
        raise ValueError("Snapshots must have finite capture times") from exc
    if any(not math.isfinite(point[0]) for point in points):
        raise ValueError("Snapshots must have finite capture times")
    if len({point[0] for point in points}) != len(points):
        raise ValueError("Snapshots must have distinct capture times")
    elapsed_seconds = points[-1][0] - points[0][0]
    if sample_count < MIN_RISK_SNAPSHOT_COUNT:
        return _risk_withheld(
            horizon_days, sample_count, elapsed_seconds,
            f"at least {MIN_RISK_SNAPSHOT_COUNT} complete snapshots are required")
    if elapsed_seconds < MIN_RISK_SPAN_SECONDS:
        return _risk_withheld(
            horizon_days, sample_count, elapsed_seconds,
            "history must span at least "
            f"{MIN_RISK_SPAN_SECONDS / 86400:.0f} days")
    if len({point[2] for point in points}) != 1:
        return _risk_withheld(
            horizon_days, sample_count, elapsed_seconds,
            "mounted filesystem capacity changed between snapshots")

    increments = []
    for previous, current in zip(points, points[1:]):
        elapsed_days = (current[0] - previous[0]) / 86400
        if elapsed_days * 86400 < MIN_RISK_INTERVAL_SECONDS:
            return _risk_withheld(
                horizon_days, sample_count, elapsed_seconds,
                "each snapshot interval must be at least "
                f"{MIN_RISK_INTERVAL_SECONDS / 3600:.0f} hours")
        increments.append((current[1] - previous[1], elapsed_days))

    observed_days = sum(elapsed_days for _, elapsed_days in increments)
    drift = sum(delta for delta, _ in increments) / observed_days
    residual_sum = sum(
        (delta - drift * elapsed_days) ** 2 / elapsed_days
        for delta, elapsed_days in increments)
    variance = residual_sum / (len(increments) - 1)
    volatility = math.sqrt(max(0.0, variance))
    current_free = points[-1][3]

    if current_free <= 0:
        probability = 1.0
    elif volatility <= 1e-12:
        probability = 1.0 if drift > 0 and drift * horizon_days >= current_free else 0.0
    else:
        horizon = float(horizon_days)
        scaled_volatility = volatility * math.sqrt(horizon)
        distance = current_free / scaled_volatility
        drift_term = drift * math.sqrt(horizon) / volatility
        reflected_log_probability = (
            2.0 * drift_term * distance
            + _log_normal_survival(drift_term + distance))
        probability = min(1.0, max(
            0.0,
            _probability_from_log(reflected_log_probability)
            + _normal_survival(distance - drift_term)))

    return {
        "assessed": True,
        "model": CAPACITY_RISK_MODEL,
        "horizon_days": horizon_days,
        "sample_count": sample_count,
        "elapsed_seconds": elapsed_seconds,
        "current_free_bytes": current_free,
        "drift_bytes_per_day": drift,
        "volatility_bytes_per_sqrt_day": volatility,
        "risk_probability": probability,
        "minimum_sample_count": MIN_RISK_SNAPSHOT_COUNT,
        "minimum_span_seconds": MIN_RISK_SPAN_SECONDS,
        "minimum_interval_seconds": MIN_RISK_INTERVAL_SECONDS,
        "reason": None,
        "boundary": (
            "This is a local Brownian-motion-with-drift model over aggregate "
            "mounted-filesystem use. It assumes past observed increments are "
            "informative; it is not a capacity guarantee, a root-cause "
            "diagnosis, or permission to change files or volumes."
        ),
    }
