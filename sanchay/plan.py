"""Create a reviewable cleanup plan without deleting anything.

The optimizer's job is to present recoverability evidence, not to act on a
user's files. This module turns those recommendations into a stable JSON
manifest that can be inspected and independently rechecked before any
separate cleanup action is taken.
"""
from datetime import datetime, timezone
import hmac
import hashlib
import json
import os
from pathlib import Path
import stat

from . import dedup, regret, storage


ACTION = {
    "disposable": "review through the owning cache or build tool before any manual clear",
    "duplicate": "retain the named survivor and review this byte-confirmed alternate copy",
    "tracked": "confirm the project owner accepts removal; Git HEAD is a restoration route",
}

DECISION_MODEL = {
    "name": "regret_aware_priority",
    "version": 1,
    "formula": "priority = size_bytes × unchanged_age × (1 - regret_weight)",
    "boundary": "unique and hardlinked entries are excluded before ranking",
}


def _evidence(row, duplicate_of):
    """Return evidence with its strength instead of overstating certainty."""
    if row["kind"] == "duplicate":
        return {
            "type": "byte_for_byte_match",
            "strength": "direct",
            "detail": "byte-for-byte match with the named retained survivor at "
                      f"{duplicate_of[row['path']]}",
        }
    if row["kind"] == "tracked":
        return {
            "type": "clean_git_head",
            "strength": "repository_state",
            "detail": "clean relative to Git HEAD; modified and staged files are excluded",
        }
    return {
        "type": "known_regenerable_path",
        "strength": "heuristic",
        "detail": "matched a narrow cache or tool-specific build-output path; "
                  "confirm with the owning tool before manual clearing",
    }


def _decision_trace(row):
    """Freeze the exact model inputs behind one review recommendation."""
    return {
        **DECISION_MODEL,
        "inputs": {
            "size_bytes": row["size"],
            "unchanged_age": row["staleness"],
            "regret_weight": row["regret"],
        },
        "computed_priority": row["priority"],
    }


def _fingerprint(document):
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _identity(info):
    return {
        "device": getattr(info, "device", 0),
        "inode": info.inode,
        "size": info.size,
        "mtime": info.mtime,
        "nlink": getattr(info, "nlink", 1),
    }


def _fingerprint_valid(document):
    claimed = document.get("fingerprint_sha256")
    unsigned = {key: value for key, value in document.items()
                if key != "fingerprint_sha256"}
    expected = _fingerprint(unsigned)
    return isinstance(claimed, str) and hmac.compare_digest(claimed, expected)


def build(files, duplicate_groups, root, now=None, limit=25,
          target_reclaim_bytes=None):
    """Build a non-executing cleanup manifest from one scan result."""
    if target_reclaim_bytes is not None and target_reclaim_bytes <= 0:
        raise ValueError("Reclaim target must be greater than zero")
    duplicate_of = dedup.confirmed_duplicate_map(duplicate_groups)
    by_path = {info.path: info for info in files}
    eligible = []
    protected_count = 0
    protected_bytes = 0
    excluded_hardlink_entries = 0
    hardlinked = []

    for info in files:
        if storage.is_hardlinked(info):
            excluded_hardlink_entries += 1
            hardlinked.append(info)
            continue
        row = regret.score(info, info.path in duplicate_of, now)
        if row["kind"] == "unique":
            protected_count += 1
            protected_bytes += info.size
            continue
        eligible.append((row, info))

    eligible.sort(key=lambda item: (-item[0]["priority"],
                                    item[0]["path"].replace("\\", "/")))
    selected = eligible[:limit]
    if target_reclaim_bytes is not None:
        selected = []
        selected_bytes = 0
        for item in eligible:
            if selected_bytes >= target_reclaim_bytes:
                break
            selected.append(item)
            selected_bytes += item[0]["size"]

    recommendations = []
    for row, info in selected:
        item = {
            **row,
            "proposed_action": ACTION[row["kind"]],
            "recovery_evidence": _evidence(row, duplicate_of),
            "decision_trace": _decision_trace(row),
            "requires_human_review": True,
            "observed_identity": _identity(info),
        }
        if row["kind"] == "duplicate":
            survivor_path = duplicate_of[row["path"]]
            item["survivor_path"] = survivor_path
            item["survivor_identity"] = _identity(by_path[survivor_path])
        recommendations.append(item)

    document = {
        "schema_version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(Path(root).resolve()),
        "execution": {
            "automatic_deletion": False,
            "requires_human_review": True,
            "boundary": "SANCHAY creates recommendations only; it never deletes or moves files.",
        },
        "safety": {
            "protected_unique_files": protected_count,
            "protected_unique_bytes": protected_bytes,
            "logical_file_entries": len(files),
            "physical_file_count": len(storage.physical_records(files)),
            "excluded_hardlink_entries": excluded_hardlink_entries,
            "excluded_hardlink_physical_bytes": storage.physical_bytes(hardlinked),
            "candidate_count": len(eligible),
            "candidate_bytes": sum(row["size"] for row, _ in eligible),
            "rule": "unique, untracked, uncached files and every hardlinked entry are excluded before ranking",
        },
        "integrity": {
            "algorithm": "SHA-256",
            "purpose": "detects accidental plan changes; this checksum is not a signature",
        },
        "decision_model": DECISION_MODEL,
        "recommendations": recommendations,
    }
    if target_reclaim_bytes is not None:
        selected_bytes = sum(item["size"] for item in recommendations)
        document["selection"] = {
            "intent": "reclaim_at_least",
            "target_reclaim_bytes": target_reclaim_bytes,
            "selected_reclaim_bytes": selected_bytes,
            "target_met": selected_bytes >= target_reclaim_bytes,
            "shortfall_bytes": max(0, target_reclaim_bytes - selected_bytes),
            "method": "deterministic priority order after the recovery-evidence safety gate; no file action is executed",
        }
    document["fingerprint_sha256"] = _fingerprint(document)
    return document


def write(document, out):
    path = Path(out)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return str(path)


def duplicate_evidence_paths(document):
    """Return both sides of each byte-confirmed duplicate relationship.

    A treemap should show the retained survivor as duplicate evidence too; only
    the alternate copy is a review recommendation.
    """
    paths = set()
    for item in document.get("recommendations", []):
        if not isinstance(item, dict) or item.get("kind") != "duplicate":
            continue
        path = item.get("path")
        survivor = item.get("survivor_path")
        if isinstance(path, str):
            paths.add(path)
        if isinstance(survivor, str):
            paths.add(survivor)
    return frozenset(paths)


def read(path):
    """Load a plan without performing any filesystem action."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"schema_version", "root", "execution", "recommendations", "safety",
                "fingerprint_sha256"}
    safety_required = {"protected_unique_files", "protected_unique_bytes",
                       "logical_file_entries", "physical_file_count",
                       "excluded_hardlink_entries", "excluded_hardlink_physical_bytes",
                       "candidate_count", "candidate_bytes", "rule"}
    if (document.get("schema_version") != 3 or not required.issubset(document)
            or not isinstance(document["root"], str)
            or not isinstance(document["execution"], dict)
            or not isinstance(document["safety"], dict)
            or not safety_required.issubset(document["safety"])
            or not isinstance(document["recommendations"], list)
            or not isinstance(document["fingerprint_sha256"], str)):
        raise ValueError("Unsupported or incomplete SANCHAY cleanup plan")
    return document


def _current_identity(path):
    try:
        observed = os.lstat(path)
    except OSError as exc:
        return None, f"cannot read path: {exc.strerror or exc}"
    if not stat.S_ISREG(observed.st_mode):
        return None, "path is no longer a regular file"
    return {
        "device": observed.st_dev,
        "inode": observed.st_ino,
        "size": observed.st_size,
        "mtime": observed.st_mtime,
        "nlink": observed.st_nlink,
    }, None


def _identity_check(path, expected, role):
    if not isinstance(expected, dict):
        return f"{role} identity is missing from the plan"
    actual, error = _current_identity(path)
    if error:
        return error
    for field in ("device", "inode", "size", "mtime", "nlink"):
        if actual[field] != expected.get(field):
            return f"{role} {field} changed since the plan was created"
    return None


def _inside_root(path, root, role):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
    except (OSError, ValueError):
        return f"{role} is outside the selected scan root"
    return None


def verify(document):
    """Recheck a review plan against the filesystem without changing it.

    A valid result means the plan checksum and each retained recovery-evidence
    check still match. It is a review gate, not an authorization to delete
    anything.
    """
    result = {
        "valid": False,
        "fingerprint_valid": _fingerprint_valid(document),
        "checked": 0,
        "recommendations": [],
    }
    if not result["fingerprint_valid"]:
        result["reason"] = "plan integrity checksum does not match its contents"
        return result

    # Git's clean-HEAD result is intentionally refreshed at verification time.
    regret._repo_cache.clear()
    for item in document["recommendations"]:
        reasons = []
        if not isinstance(item, dict):
            result["checked"] += 1
            result["recommendations"].append({
                "path": None,
                "kind": None,
                "valid": False,
                "reasons": ["recommendation is not an object"],
            })
            continue

        kind = item.get("kind")
        path = item.get("path")
        if kind not in ACTION or not isinstance(path, str):
            reasons.append("unsupported recommendation")
        else:
            changed = _inside_root(path, document["root"], "candidate")
            if not changed:
                changed = _identity_check(path, item.get("observed_identity", {}),
                                          "candidate")
            if changed:
                reasons.append(changed)
            if kind == "duplicate":
                survivor = item.get("survivor_path")
                if not isinstance(survivor, str):
                    reasons.append("duplicate survivor is missing")
                else:
                    changed = _inside_root(survivor, document["root"], "survivor")
                    if not changed:
                        changed = _identity_check(
                            survivor, item.get("survivor_identity", {}), "survivor")
                    if changed:
                        reasons.append(changed)
                    elif not dedup.same_content(path, survivor):
                        reasons.append("candidate and survivor no longer match")
            elif kind == "tracked" and not regret.in_repo(path):
                reasons.append("candidate is no longer cleanly recoverable from Git HEAD")

        result["checked"] += 1
        result["recommendations"].append({
            "path": path,
            "kind": kind,
            "valid": not reasons,
            "reasons": reasons,
        })

    result["valid"] = all(item["valid"] for item in result["recommendations"])
    return result
