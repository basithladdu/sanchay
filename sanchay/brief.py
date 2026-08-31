"""Create a path-free aggregate handoff for a secure storage operator.

The normal SANCHAY review plan and HTML report are intentionally detailed local
artifacts: they contain candidate paths so an operator can inspect evidence.
This module produces a separate aggregate brief for a monitored endpoint or
support handoff. It deliberately excludes roots, paths, file names, process
identifiers, process names, file content, mount points, and device sources.
It never transmits or remediates anything.
"""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path

from . import managed, scan, storage


OPERATOR_BRIEF_SCHEMA_VERSION = 1
_RECOMMENDATION_KINDS = ("disposable", "duplicate", "tracked")
_SOURCE_CLASSES = frozenset({
    "block_device", "device_mapper", "overlay_layer", "unspecified",
    "virtual_or_network_source",
})


def _fingerprint(document):
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fingerprint_valid(document):
    """Return whether a brief's checksum still matches its serialized content."""
    claimed = document.get("fingerprint_sha256") if isinstance(document, dict) else None
    unsigned = ({key: value for key, value in document.items()
                 if key != "fingerprint_sha256"}
                if isinstance(document, dict) else {})
    return (isinstance(claimed, str)
            and hmac.compare_digest(claimed, _fingerprint(unsigned)))


def _non_negative_int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _recommendation_summary(recommendations):
    summary = {kind: {"count": 0, "allocated_bytes": 0}
               for kind in _RECOMMENDATION_KINDS}
    for item in recommendations:
        if not isinstance(item, dict) or item.get("kind") not in summary:
            continue
        entry = summary[item["kind"]]
        entry["count"] += 1
        entry["allocated_bytes"] += _non_negative_int(item.get("size"))
    return summary


def _managed_summary(advisories):
    allowed_keys = {policy.key for policy in managed.POLICIES}
    totals = defaultdict(lambda: {"entries": 0, "allocated_bytes": 0})
    for item in advisories:
        if not isinstance(item, dict) or item.get("key") not in allowed_keys:
            continue
        total = totals[item["key"]]
        total["entries"] += _non_negative_int(item.get("entries"))
        total["allocated_bytes"] += _non_negative_int(item.get("allocated_bytes"))
    return [
        {"policy": key, **totals[key]}
        for key in sorted(totals)
    ]


def _mount_summary(filesystem_context):
    context = filesystem_context if isinstance(filesystem_context, dict) else {}
    source_class = context.get("source_class")
    return {
        "context_observed": bool(context),
        "source_class": source_class if source_class in _SOURCE_CLASSES else "other_or_unknown",
    }


def _capacity_summary(capacity_accounting):
    if not isinstance(capacity_accounting, dict):
        return {"requested": False, "assessed": False}
    if not capacity_accounting.get("assessed"):
        return {
            "requested": True,
            "assessed": False,
            "inode_capacity": {"assessed": False},
            "block_availability": {"assessed": False},
        }
    summary = {
        "requested": True,
        "assessed": True,
        "filesystem_used_bytes": _non_negative_int(
            capacity_accounting.get("filesystem_used_bytes")),
        "readable_file_allocated_bytes": _non_negative_int(
            capacity_accounting.get("readable_file_allocated_bytes")),
        "visible_deleted_open_allocated_bytes": _non_negative_int(
            capacity_accounting.get("deleted_open_allocated_bytes")),
        "visible_accounted_bytes": _non_negative_int(
            capacity_accounting.get("visible_accounted_bytes")),
        "accounting_gap_bytes": capacity_accounting.get("accounting_gap_bytes")
        if isinstance(capacity_accounting.get("accounting_gap_bytes"), int)
        and not isinstance(capacity_accounting.get("accounting_gap_bytes"), bool) else 0,
        "gap_direction": capacity_accounting.get("gap_direction")
        if capacity_accounting.get("gap_direction") in {
            "filesystem_used_exceeds_visible_accounting",
            "visible_accounting_exceeds_filesystem_used",
            "visible_accounting_matches_filesystem_used",
        } else "unavailable",
    }
    inode_capacity = capacity_accounting.get("inode_capacity")
    if not isinstance(inode_capacity, dict) or not inode_capacity.get("assessed"):
        summary["inode_capacity"] = {"assessed": False}
    else:
        total = _non_negative_int(inode_capacity.get("total_inodes"))
        free = _non_negative_int(inode_capacity.get("free_inodes"))
        used = _non_negative_int(inode_capacity.get("used_inodes"))
        available = inode_capacity.get("available_inodes")
        available = (_non_negative_int(available)
                     if available is not None else None)
        if (total is None or total == 0 or free is None or used is None
                or free > total or used > total or used != total - free
                or (available is not None and available > total)):
            summary["inode_capacity"] = {"assessed": False}
        else:
            summary["inode_capacity"] = {
                "assessed": True,
                "total_inodes": total,
                "free_inodes": free,
                "available_inodes": available,
                "used_inodes": used,
                "used_percent": inode_capacity.get("used_percent")
                if isinstance(inode_capacity.get("used_percent"), (int, float))
                and not isinstance(inode_capacity.get("used_percent"), bool) else 0,
            }
    block_availability = capacity_accounting.get("block_availability")
    if not isinstance(block_availability, dict) or not block_availability.get("assessed"):
        summary["block_availability"] = {"assessed": False}
        return summary
    allowed = {
        key: _non_negative_int(block_availability.get(key))
        for key in (
            "total_bytes", "used_bytes", "free_bytes", "available_bytes",
            "free_unavailable_to_unprivileged_bytes",
        )
    }
    if (any(value is None for value in allowed.values())
            or allowed["used_bytes"] + allowed["free_bytes"] != allowed["total_bytes"]
            or allowed["available_bytes"] > allowed["free_bytes"]
            or (allowed["free_bytes"] - allowed["available_bytes"]
                != allowed["free_unavailable_to_unprivileged_bytes"])):
        summary["block_availability"] = {"assessed": False}
        return summary
    summary["block_availability"] = {"assessed": True, **allowed}
    return summary


def build(files, cleanup_plan, *, process_held=None, capacity_accounting=None,
          now=None):
    """Return a path-free, local-only aggregate summary for operator review."""
    if not isinstance(cleanup_plan, dict) or not isinstance(cleanup_plan.get("safety"), dict):
        raise ValueError("A complete SANCHAY cleanup plan is required for an operator brief")
    safety = cleanup_plan["safety"]
    coverage = scan.coverage_summary(safety.get("scan_coverage"))
    selected = cleanup_plan.get("selection")
    selected_summary = None
    if isinstance(selected, dict):
        selected_summary = {
            "requested_reclaim_bytes": _non_negative_int(
                selected.get("target_reclaim_bytes")),
            "selected_reclaim_bytes": _non_negative_int(
                selected.get("selected_reclaim_bytes")),
            "shortfall_bytes": _non_negative_int(selected.get("shortfall_bytes")),
            "target_met": bool(selected.get("target_met")),
        }
    deleted_records = tuple(process_held or ())
    document = {
        "schema_version": OPERATOR_BRIEF_SCHEMA_VERSION,
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(),
        "purpose": (
            "aggregate local operator handoff; this is not a security event log, "
            "a remediation instruction, or a network submission"
        ),
        "privacy_boundary": {
            "raw_paths_included": False,
            "file_names_included": False,
            "process_identifiers_included": False,
            "process_names_included": False,
            "file_content_included": False,
            "network_transmission": False,
        },
        "execution": {
            "automatic_deletion": False,
            "requires_human_review": True,
        },
        "scope": {
            "scan_scope": ("cross_filesystem_inventory"
                           if safety.get("scan_scope") == "cross_filesystem_inventory"
                           else "single_filesystem"),
            "scan_coverage": coverage,
            "mount_context": _mount_summary(safety.get("filesystem_context")),
        },
        "storage": {
            "logical_file_entries": _non_negative_int(safety.get("logical_file_entries")),
            "physical_file_count": _non_negative_int(safety.get("physical_file_count")),
            "allocated_physical_bytes": storage.physical_bytes(files),
            "logical_physical_bytes": storage.logical_bytes(files),
        },
        "review": {
            "eligible_candidate_count": _non_negative_int(safety.get("candidate_count")),
            "eligible_candidate_allocated_bytes": _non_negative_int(
                safety.get("candidate_bytes")),
            "selected_by_evidence_class": _recommendation_summary(
                cleanup_plan.get("recommendations", ())),
            "target_selection": selected_summary,
        },
        "safety": {
            "protected_unique_files": _non_negative_int(safety.get("protected_unique_files")),
            "protected_unique_allocated_bytes": _non_negative_int(
                safety.get("protected_unique_bytes")),
            "excluded_credential_control_entries": _non_negative_int(
                safety.get("excluded_credential_control_entries")),
            "excluded_hardlink_entries": _non_negative_int(
                safety.get("excluded_hardlink_entries")),
            "excluded_hardlink_allocated_bytes": _non_negative_int(
                safety.get("excluded_hardlink_physical_bytes")),
            "managed_storage": _managed_summary(
                safety.get("managed_operational_storage", ())),
        },
        "operational_advisories": {
            "visible_deleted_open_inode_count": len(deleted_records),
            "visible_deleted_open_allocated_bytes": sum(
                _non_negative_int(getattr(record, "allocated_size", None))
                for record in deleted_records),
            "capacity_accounting": _capacity_summary(capacity_accounting),
        },
        "integrity": {
            "algorithm": "SHA-256",
            "purpose": "detects accidental brief changes; this checksum is not a signature",
        },
    }
    document["fingerprint_sha256"] = _fingerprint(document)
    return document


def write(document, out):
    """Write an operator brief locally without transmitting it."""
    path = Path(out)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return str(path)


def read(path):
    """Load a brief for checksum verification without acting on endpoint data."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {
        "schema_version", "generated_at", "purpose", "privacy_boundary",
        "execution", "scope", "storage", "review", "safety",
        "operational_advisories", "integrity", "fingerprint_sha256",
    }
    if (not isinstance(document, dict)
            or document.get("schema_version") != OPERATOR_BRIEF_SCHEMA_VERSION
            or not required.issubset(document)):
        raise ValueError("Unsupported or incomplete SANCHAY operator brief")
    return document
