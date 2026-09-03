"""Explicit, permission-gated file actions for the interactive shell.

Scanning, reporting, and plan creation remain read-only.  This module is the
only place where SANCHAY may change a candidate file, and every entry point
requires a verified active plan plus temporary in-memory authorization.
"""
from dataclasses import dataclass
import hmac
import os
from pathlib import Path
import stat

from . import plan, storage


AUTHORIZATION_PHRASE = "I_UNDERSTAND_FILE_ACTIONS"


class ActionDenied(ValueError):
    """Raised when an action cannot satisfy every safety gate."""


@dataclass
class ActionPermission:
    """Temporary permission that is never persisted across shell sessions."""

    enabled: bool = False

    def enable(self, phrase):
        self.enabled = hmac.compare_digest(str(phrase), AUTHORIZATION_PHRASE)
        return self.enabled

    def disable(self):
        self.enabled = False

    def require(self):
        if not self.enabled:
            raise ActionDenied(
                "File actions are disabled; run /permissions enable "
                + AUTHORIZATION_PHRASE)


def candidate(document, index):
    """Return one one-based recommendation or fail without touching storage."""
    if isinstance(index, bool) or not isinstance(index, int) or index <= 0:
        raise ActionDenied("Candidate number must be a positive integer")
    recommendations = document.get("recommendations", [])
    if index > len(recommendations):
        raise ActionDenied(
            f"Candidate {index} is outside the active plan "
            f"(1-{len(recommendations)})")
    item = recommendations[index - 1]
    if item.get("kind") not in plan.ACTION:
        raise ActionDenied("Candidate does not have a supported review action")
    return item


def expected_confirmation(action, index):
    return f"{action.upper()}:{index}"


def delete(document, index, permission, confirmation, retained_path=None):
    """Permanently unlink one verified recommendation."""
    permission.require()
    permission.disable()
    item = candidate(document, index)
    _require_confirmation("DELETE", index, confirmation)
    if item["kind"] == "duplicate":
        if retained_path is None:
            raise ActionDenied(
                "Duplicate deletion requires --retain with the named evidence peer")
        expected_survivor = os.path.realpath(os.path.abspath(item["survivor_path"]))
        confirmed_survivor = os.path.realpath(os.path.abspath(retained_path))
        if not hmac.compare_digest(
                os.path.normcase(confirmed_survivor),
                os.path.normcase(expected_survivor)):
            raise ActionDenied(
                "Retained path does not match the named evidence peer in the active plan")
    elif retained_path is not None:
        raise ActionDenied("--retain is valid only for duplicate candidates")
    _require_valid_plan(document)
    _unlink_verified(document["root"], item["path"], item["observed_identity"])
    return item


def move(document, index, destination, permission, confirmation):
    """Move one verified file without overwriting or crossing filesystems.

    A same-filesystem hardlink followed by a verified unlink gives the
    destination an atomic no-overwrite creation step.  Cross-filesystem moves
    are refused because copy-then-delete is not a single recoverable action.
    """
    permission.require()
    permission.disable()
    item = candidate(document, index)
    _require_confirmation("MOVE", index, confirmation)
    _require_valid_plan(document)

    source = Path(item["path"])
    destination = Path(destination).expanduser()
    if destination.is_dir():
        destination = destination / source.name
    destination = destination.resolve()
    if not destination.parent.is_dir():
        raise ActionDenied("Move destination parent does not exist")
    if os.path.lexists(str(destination)):
        raise ActionDenied("Move destination already exists; refusing to overwrite it")

    expected = item["observed_identity"]
    try:
        destination_device = os.stat(str(destination.parent)).st_dev
    except OSError as exc:
        raise ActionDenied(f"Cannot inspect move destination: {exc}") from exc
    if destination_device != expected.get("device"):
        raise ActionDenied(
            "Cross-filesystem move refused; use an operator-controlled copy and "
            "the /verify-archive gate")

    _link_verified(document["root"], item["path"], str(destination), expected)

    adjusted = dict(expected)
    adjusted["nlink"] = expected.get("nlink", 1) + 1
    try:
        _require_identity(str(destination), adjusted)
        _unlink_verified(document["root"], item["path"], adjusted)
    except Exception:
        # Roll back the newly created link when the source still exists.  This
        # cleanup only targets the exact destination created above.
        try:
            if os.path.lexists(str(destination)) and os.path.lexists(item["path"]):
                os.unlink(str(destination))
        except OSError:
            pass
        raise
    return item, str(destination)


def disposable_candidates(document):
    return [
        (index, item)
        for index, item in enumerate(document.get("recommendations", []), start=1)
        if item.get("kind") == "disposable"
    ]


def clean(document, permission, confirmation):
    """Permanently unlink only regenerable candidates in the active plan."""
    permission.require()
    permission.disable()
    targets = disposable_candidates(document)
    if not targets:
        raise ActionDenied("The active plan contains no disposable candidates")
    expected = f"CLEAN:{len(targets)}"
    if not hmac.compare_digest(str(confirmation), expected):
        raise ActionDenied(f"Confirmation must exactly match {expected}")
    _require_valid_plan(document)

    # Preflight every target before the first unlink to avoid beginning from a
    # known-stale plan. Runtime I/O failures may still produce a partial clean,
    # and callers report every completed path.
    for _, item in targets:
        _require_identity(item["path"], item["observed_identity"])

    completed = []
    for index, item in targets:
        _unlink_verified(document["root"], item["path"], item["observed_identity"])
        completed.append((index, item))
    return completed


def _require_confirmation(action, index, confirmation):
    expected = expected_confirmation(action, index)
    if not hmac.compare_digest(str(confirmation), expected):
        raise ActionDenied(f"Confirmation must exactly match {expected}")


def _require_valid_plan(document):
    safety = document.get("safety", {})
    coverage = safety.get("scan_coverage", {})
    if coverage.get("complete") is not True:
        raise ActionDenied(
            "Active plan coverage is incomplete; file actions require a complete scan")
    if safety.get("scan_scope") == "cross_filesystem_inventory":
        raise ActionDenied(
            "File actions require a single-filesystem scan, not cross-filesystem inventory")
    result = plan.verify(document)
    if not result["valid"]:
        reason = result.get("reason") or "candidate evidence changed"
        raise ActionDenied("Active plan is no longer valid: " + reason)


def _observed_identity(stat_result):
    return {
        "device": stat_result.st_dev,
        "inode": stat_result.st_ino,
        "size": stat_result.st_size,
        "allocated_size": storage.allocated_bytes_from_stat(stat_result),
        "mtime": stat_result.st_mtime,
        "mtime_ns": getattr(stat_result, "st_mtime_ns", None),
        "nlink": stat_result.st_nlink,
    }


def _require_identity(path, expected):
    try:
        observed = os.lstat(path)
    except OSError as exc:
        raise ActionDenied(f"Candidate cannot be inspected: {exc}") from exc
    if not stat.S_ISREG(observed.st_mode):
        raise ActionDenied("Candidate is no longer a regular file")
    actual = _observed_identity(observed)
    for field in plan.IDENTITY_FIELDS:
        if field not in expected or actual[field] != expected[field]:
            raise ActionDenied(f"Candidate {field} changed since the active scan")
    return observed


def _inside_root(root, path):
    canonical_root = os.path.realpath(os.path.abspath(root))
    absolute_path = os.path.abspath(path)
    try:
        relative = os.path.relpath(absolute_path, canonical_root)
    except ValueError as exc:
        raise ActionDenied("Candidate is outside the active scan root") from exc
    if (relative in {"", os.curdir, os.pardir}
            or relative.startswith(os.pardir + os.sep)
            or os.path.isabs(relative)):
        raise ActionDenied("Candidate is outside the active scan root")
    return canonical_root, relative


def _descriptor_actions_available():
    return (
        hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and os.open in getattr(os, "supports_dir_fd", set())
        and os.stat in getattr(os, "supports_dir_fd", set())
        and os.unlink in getattr(os, "supports_dir_fd", set())
    )


def _descriptor_link_available():
    return _descriptor_actions_available() and os.link in getattr(os, "supports_dir_fd", set())


def _link_verified(root, path, destination, expected):
    canonical_root, relative = _inside_root(root, path)
    if not _descriptor_link_available():
        canonical_target = os.path.realpath(os.path.abspath(path))
        try:
            if os.path.commonpath((canonical_root, canonical_target)) != canonical_root:
                raise ActionDenied("Candidate resolves outside the active scan root")
        except ValueError as exc:
            raise ActionDenied("Candidate resolves outside the active scan root") from exc
        _require_identity(path, expected)
        try:
            os.link(path, destination, follow_symlinks=False)
        except (NotImplementedError, OSError) as exc:
            raise ActionDenied(
                f"Safe no-overwrite move could not create destination: {exc}") from exc
        return

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    try:
        directory_fd = os.open(canonical_root, flags)
    except OSError as exc:
        raise ActionDenied(f"Cannot anchor action at the active scan root: {exc}") from exc
    try:
        parts = relative.split(os.sep)
        for part in parts[:-1]:
            try:
                next_fd = os.open(part, flags, dir_fd=directory_fd)
            except OSError as exc:
                raise ActionDenied(
                    "Candidate parent changed or contains a symlink; action refused") from exc
            os.close(directory_fd)
            directory_fd = next_fd
        try:
            observed = os.stat(parts[-1], dir_fd=directory_fd,
                               follow_symlinks=False)
        except OSError as exc:
            raise ActionDenied(f"Candidate cannot be inspected: {exc}") from exc
        if not stat.S_ISREG(observed.st_mode):
            raise ActionDenied("Candidate is no longer a regular file")
        actual = _observed_identity(observed)
        for field in plan.IDENTITY_FIELDS:
            if field not in expected or actual[field] != expected[field]:
                raise ActionDenied(f"Candidate {field} changed since the active scan")
        try:
            os.link(parts[-1], destination, src_dir_fd=directory_fd,
                    follow_symlinks=False)
        except OSError as exc:
            raise ActionDenied(
                f"Safe no-overwrite move could not create destination: {exc}") from exc
    finally:
        os.close(directory_fd)


def _unlink_verified(root, path, expected):
    canonical_root, relative = _inside_root(root, path)
    if not _descriptor_actions_available():
        canonical_target = os.path.realpath(os.path.abspath(path))
        try:
            if os.path.commonpath((canonical_root, canonical_target)) != canonical_root:
                raise ActionDenied("Candidate resolves outside the active scan root")
        except ValueError as exc:
            raise ActionDenied("Candidate resolves outside the active scan root") from exc
        _require_identity(path, expected)
        os.unlink(path)
        return

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    try:
        directory_fd = os.open(canonical_root, flags)
    except OSError as exc:
        raise ActionDenied(f"Cannot anchor action at the active scan root: {exc}") from exc
    try:
        parts = relative.split(os.sep)
        for part in parts[:-1]:
            try:
                next_fd = os.open(part, flags, dir_fd=directory_fd)
            except OSError as exc:
                raise ActionDenied(
                    "Candidate parent changed or contains a symlink; action refused") from exc
            os.close(directory_fd)
            directory_fd = next_fd
        try:
            observed = os.stat(parts[-1], dir_fd=directory_fd,
                               follow_symlinks=False)
        except OSError as exc:
            raise ActionDenied(f"Candidate cannot be inspected: {exc}") from exc
        if not stat.S_ISREG(observed.st_mode):
            raise ActionDenied("Candidate is no longer a regular file")
        actual = _observed_identity(observed)
        for field in plan.IDENTITY_FIELDS:
            if field not in expected or actual[field] != expected[field]:
                raise ActionDenied(f"Candidate {field} changed since the active scan")
        os.unlink(parts[-1], dir_fd=directory_fd)
    finally:
        os.close(directory_fd)
