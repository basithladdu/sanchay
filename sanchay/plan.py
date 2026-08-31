"""Create a reviewable cleanup plan without deleting anything.

The optimizer's job is to make safe recommendations, not to act on a user's
files.  This module turns those recommendations into a stable JSON manifest
that can be inspected, shared, and independently checked before any separate
cleanup action is taken.
"""
from datetime import datetime, timezone
import hmac
import hashlib
import json
import os
from pathlib import Path
import stat

from . import dedup, regret


ACTION = {
    "disposable": "review and clear through the owning cache or build tool",
    "duplicate": "remove this copy after preserving the named survivor",
    "tracked": "restore from Git only after reviewing repository state",
}


def _proof(row, duplicate_of):
    if row["kind"] == "duplicate":
        return f"byte-identical survivor retained at {duplicate_of[row['path']]}"
    if row["kind"] == "tracked":
        return "current file matches Git HEAD; modified and staged files are excluded"
    return "matched a known regenerable cache or build-output path"


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
    }


def _fingerprint_valid(document):
    claimed = document.get("fingerprint_sha256")
    unsigned = {key: value for key, value in document.items()
                if key != "fingerprint_sha256"}
    expected = _fingerprint(unsigned)
    return isinstance(claimed, str) and hmac.compare_digest(claimed, expected)


def build(files, duplicate_groups, root, now=None, limit=25):
    """Build a non-executing cleanup manifest from one scan result."""
    duplicate_of = dedup.duplicate_map(duplicate_groups)
    by_path = {info.path: info for info in files}
    eligible = []
    protected_count = 0
    protected_bytes = 0

    for info in files:
        row = regret.score(info, info.path in duplicate_of, now)
        if row["kind"] == "unique":
            protected_count += 1
            protected_bytes += info.size
            continue
        eligible.append((row, info))

    eligible.sort(key=lambda item: item[0]["priority"], reverse=True)
    recommendations = []
    for row, info in eligible[:limit]:
        item = {
            **row,
            "proposed_action": ACTION[row["kind"]],
            "safety_proof": _proof(row, duplicate_of),
            "requires_human_review": True,
            "observed_identity": _identity(info),
        }
        if row["kind"] == "duplicate":
            survivor_path = duplicate_of[row["path"]]
            item["survivor_path"] = survivor_path
            item["survivor_identity"] = _identity(by_path[survivor_path])
        recommendations.append(item)

    document = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "execution": {
            "automatic_deletion": False,
            "requires_human_review": True,
            "boundary": "SANCHAY creates recommendations only; it never deletes or moves files.",
        },
        "safety": {
            "protected_unique_files": protected_count,
            "protected_unique_bytes": protected_bytes,
            "candidate_count": len(eligible),
            "candidate_bytes": sum(row["size"] for row, _ in eligible),
            "rule": "unique, untracked, uncached files are excluded before ranking",
        },
        "recommendations": recommendations,
    }
    document["fingerprint_sha256"] = _fingerprint(document)
    return document


def write(document, out):
    path = Path(out)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return str(path)


def read(path):
    """Load a plan without performing any filesystem action."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"schema_version", "execution", "recommendations", "safety",
                "fingerprint_sha256"}
    if document.get("schema_version") != 2 or not required.issubset(document):
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
    }, None


def _identity_check(path, expected, role):
    actual, error = _current_identity(path)
    if error:
        return error
    for field in ("device", "inode", "size", "mtime"):
        if actual[field] != expected.get(field):
            return f"{role} {field} changed since the plan was created"
    return None


def verify(document):
    """Recheck a review plan against the filesystem without changing it.

    A valid result means the signed manifest and each retained safety proof
    still match. It is a review gate, not an authorization to delete anything.
    """
    result = {
        "valid": False,
        "fingerprint_valid": _fingerprint_valid(document),
        "checked": 0,
        "recommendations": [],
    }
    if not result["fingerprint_valid"]:
        result["reason"] = "plan fingerprint does not match its contents"
        return result

    # Git's clean-HEAD result is intentionally refreshed at verification time.
    regret._repo_cache.clear()
    for item in document["recommendations"]:
        reasons = []
        kind = item.get("kind")
        path = item.get("path")
        if kind not in ACTION or not isinstance(path, str):
            reasons.append("unsupported recommendation")
        else:
            changed = _identity_check(path, item.get("observed_identity", {}),
                                      "candidate")
            if changed:
                reasons.append(changed)
            if kind == "duplicate":
                survivor = item.get("survivor_path")
                if not isinstance(survivor, str):
                    reasons.append("duplicate survivor is missing")
                else:
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
