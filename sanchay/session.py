"""Reusable in-memory state for the interactive SANCHAY shell.

The one-shot CLI remains useful for scripts.  A human-driven shell should not
walk and hash the same tree again for every follow-up command, so this module
owns one point-in-time scan and the evidence derived from it.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
import shutil
from pathlib import Path

from . import (dedup, intelligence, managed, mounts, plan, processes, report,
               scan, storage)
from .paths import scan_target


DEFAULT_RECOMMENDATION_LIMIT = 50


@dataclass
class ScanSession:
    """Hold one scan and reuse it for reports and review artifacts."""

    root: str = None
    cross_filesystems: bool = False
    files: list = field(default_factory=list)
    coverage: dict = None
    groups: list = field(default_factory=list)
    filesystem_context: dict = None
    held_deleted: list = field(default_factory=list)
    free_bytes: int = None
    scanned_at: datetime = None
    default_plan: dict = None
    active_plan: dict = None
    last_report: str = None
    last_plan: str = None
    stale: bool = False
    activity_profiles: dict = field(default_factory=dict)
    advisor_config: object = None

    @property
    def ready(self):
        return self.root is not None and self.active_plan is not None

    def scan(self, root, cross_filesystems=False,
             limit=DEFAULT_RECOMMENDATION_LIMIT, cancel_event=None,
             advisor_config=None):
        """Scan *root* once, then byte-confirm and retain its review evidence.

        State is assigned only after every stage succeeds.  A failed or
        interrupted refresh therefore leaves the preceding completed session
        available for review.
        """
        root = scan_target(root)
        canonical_root = os.path.realpath(os.path.abspath(os.path.expanduser(root)))
        files, coverage_record = scan.scan_with_coverage(
            canonical_root, cross_filesystems=cross_filesystems,
            cancel_event=cancel_event)
        coverage = coverage_record.as_dict()
        groups = dedup.duplicates(
            managed.content_candidates(files), root=canonical_root,
            cancel_event=cancel_event)
        filesystem_context = mounts.capacity_context(canonical_root)

        devices = {
            getattr(info, "device", None)
            for info in storage.physical_records(files)
            if getattr(info, "device", None) is not None
        }
        if not devices:
            try:
                devices.add(os.stat(canonical_root).st_dev)
            except OSError:
                pass
        held_deleted = processes.deleted_open_files(devices or None)
        usage = None if cross_filesystems else shutil.disk_usage(canonical_root)
        free_bytes = None if usage is None else usage.free
        activity_profiles = intelligence.update_activity_profiles(
            self.files if self.ready else (), files,
            self.activity_profiles if self.ready else None,
        )
        cleanup_plan = plan.build(
            files, groups, canonical_root, limit=limit,
            cross_filesystems=cross_filesystems,
            filesystem_context=filesystem_context,
            scan_coverage=coverage,
            activity_profiles=activity_profiles,
            cancel_event=cancel_event,
            advisor_config=advisor_config)

        self.root = canonical_root
        self.cross_filesystems = cross_filesystems
        self.files = files
        self.coverage = coverage
        self.groups = groups
        self.filesystem_context = filesystem_context
        self.held_deleted = held_deleted
        self.free_bytes = free_bytes
        self.scanned_at = datetime.now(timezone.utc)
        self.default_plan = cleanup_plan
        self.active_plan = cleanup_plan
        self.last_report = None
        self.last_plan = None
        self.stale = False
        self.activity_profiles = activity_profiles
        self.advisor_config = advisor_config
        return self.summary()

    def summary(self):
        self._require_scan()
        safety = self.active_plan["safety"]
        return {
            "root": self.root,
            "scanned_at": self.scanned_at,
            "file_entries": len(self.files),
            "allocated_bytes": storage.physical_bytes(self.files),
            "logical_bytes": storage.logical_bytes(self.files),
            "hardlink_aliases": storage.hardlink_alias_count(self.files),
            "duplicate_groups": len(self.groups),
            "duplicate_reclaimable_bytes": dedup.reclaimable(self.groups),
            "candidate_count": safety["candidate_count"],
            "archive_candidate_count": safety.get("archive_candidate_count", 0),
            "protected_unique_files": safety["protected_unique_files"],
            "excluded_hardlink_entries": safety["excluded_hardlink_entries"],
            "coverage": self.coverage,
            "cross_filesystems": self.cross_filesystems,
            "stale": self.stale,
            "reasoning_model": self.active_plan.get("reasoning_model", {}),
        }

    def candidates(self, limit=20):
        self._require_fresh_scan()
        if limit <= 0:
            raise ValueError("Candidate limit must be greater than zero")
        return self.active_plan["recommendations"][:limit]

    def archive_candidates(self, limit=20):
        """Return AI-ranked archive reviews without making or moving a copy."""
        self._require_fresh_scan()
        if limit <= 0:
            raise ValueError("Archive candidate limit must be greater than zero")
        return self.active_plan.get("archive_recommendations", [])[:limit]

    def target(self, target_reclaim_bytes):
        self._require_fresh_scan()
        if self.cross_filesystems:
            raise ValueError(
                "A cross-filesystem inventory cannot use a shared reclaim target")
        self.active_plan = plan.build(
            self.files, self.groups, self.root,
            target_reclaim_bytes=target_reclaim_bytes,
            cross_filesystems=False,
            filesystem_context=self.filesystem_context,
            scan_coverage=self.coverage,
            activity_profiles=self.activity_profiles,
            advisor_config=self.advisor_config)
        return self.active_plan["selection"]

    def clear_target(self):
        self._require_fresh_scan()
        self.active_plan = self.default_plan

    def write_plan(self, out, overwrite=False):
        self._require_fresh_scan()
        written = plan.write(self.active_plan, out, overwrite=overwrite)
        self.last_plan = str(Path(written).resolve())
        return self.last_plan

    def write_report(self, out, cancel_event=None):
        self._require_fresh_scan()
        written = report.build(
            self.files, self.root, self.free_bytes, out,
            cross_filesystems=self.cross_filesystems,
            process_held=self.held_deleted,
            filesystem_context=self.filesystem_context,
            scan_coverage=self.coverage,
            duplicate_groups=self.groups,
            cleanup_plan=self.active_plan,
            cancel_event=cancel_event)
        self.last_report = str(Path(written).resolve())
        return self.last_report

    def _require_scan(self):
        if not self.ready:
            raise RuntimeError("Run /scan <path> first")

    def _require_fresh_scan(self):
        self._require_scan()
        if self.stale:
            raise RuntimeError("The active scan is stale; run /refresh first")

    def mark_stale(self):
        self._require_scan()
        self.stale = True
