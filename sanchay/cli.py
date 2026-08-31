"""sanchay -- regret-aware storage intelligence for Linux."""
import argparse
import os
import re
import shutil

from . import (accounting, archive, brief, dedup, explain, forecast, managed, mounts, plan,
               processes, regret, scan, snapshot, storage)


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def parse_reclaim_bytes(value):
    """Parse a human storage target such as 600M or 1.5G."""
    normalized = str(value).strip().upper().replace("IB", "B")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([KMGT]?B?)?", normalized)
    units = {
        "": 1,
        "B": 1,
        "K": 1024,
        "KB": 1024,
        "M": 1024 ** 2,
        "MB": 1024 ** 2,
        "G": 1024 ** 3,
        "GB": 1024 ** 3,
        "T": 1024 ** 4,
        "TB": 1024 ** 4,
    }
    if not match or match.group(2) not in units:
        raise argparse.ArgumentTypeError("use bytes or a K/M/G/T suffix, for example 600M or 1.5G")
    parsed = int(float(match.group(1)) * units[match.group(2)])
    if parsed <= 0:
        raise argparse.ArgumentTypeError("reclaim target must be greater than zero")
    return parsed


def parse_risk_horizon_days(value):
    """Parse a positive whole-day horizon for the local risk model."""
    normalized = str(value).strip()
    if not re.fullmatch(r"\d+", normalized) or int(normalized) <= 0:
        raise argparse.ArgumentTypeError(
            "capacity risk horizon must be a positive whole number of days")
    return int(normalized)


def _visualization_dependency_missing(feature, exc):
    """Print an actionable optional-dependency error when Plotly is absent."""
    missing = exc.name
    if missing not in {"pandas", "plotly"}:
        return False
    print(f"{feature}: visualization support is unavailable; install optional "
          'dependencies with `python -m pip install -e ".[viz]"`')
    return True


def _invocation_artifact_paths(args):
    """Return canonical paths explicitly supplied as SANCHAY artifacts.

    A plan, report, brief, or snapshot saved beneath the selected root must not
    become a future cleanup candidate simply because the same invocation reads
    or rewrites it. The mounted-filesystem measurement remains unchanged: it
    correctly includes every physical byte on that filesystem.
    """
    paths = [args.snapshot, args.compare, args.verify_snapshot, args.plan, args.report,
             args.operator_brief]
    if args.history:
        paths.extend(args.history)
    if args.snapshot_history:
        paths.extend(snapshot.history_paths(args.snapshot_history))
    return frozenset(
        os.path.normcase(os.path.realpath(os.path.abspath(path)))
        for path in paths if path)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sanchay", description=__doc__)
    ap.add_argument("root", nargs="?")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--cross-filesystems", action="store_true",
                    help="include mounted filesystems below ROOT (off by default)")
    ap.add_argument("--explain", action="store_true",
                    help="write a local-only narrative; no scan data leaves this machine")
    ap.add_argument("--cloud-narrative", action="store_true",
                    help="with --explain, explicitly allow an optional cloud narrative over opaque metadata only")
    ap.add_argument("--ollama-narrative", action="store_true",
                    help="with --explain, request an optional opaque-metadata narrative from fixed local Ollama loopback")
    ap.add_argument("--ollama-model", metavar="MODEL",
                    help="with --ollama-narrative, select a model already available to local Ollama")
    ap.add_argument("--viz", metavar="OUT.html", help="write a regret treemap")
    ap.add_argument("--report", metavar="OUT.html",
                    help="write a detailed local HTML review report; contains relative paths")
    ap.add_argument("--operator-brief", metavar="OUT.json",
                    help="write a path-free aggregate local handoff; no network transfer")
    ap.add_argument("--plan", metavar="OUT.json",
                    help="write a review-only cleanup plan; SANCHAY never deletes files")
    ap.add_argument("--target-reclaim", metavar="SIZE", type=parse_reclaim_bytes,
                    help="select enough reviewable candidates to reclaim SIZE (for example 600M); never deletes files")
    ap.add_argument("--capacity-audit", action="store_true",
                    help="compare a complete mount-root readable inventory with filesystem used space; never remediates a gap")
    ap.add_argument("--snapshot", metavar="OUT.json",
                    help="save local mount usage plus inventory aggregates for a later observed-growth comparison")
    ap.add_argument("--snapshot-history", metavar="DIR",
                    help="append a timestamped local aggregate snapshot and use prior checksum-matching records in DIR")
    ap.add_argument("--verify-snapshot", metavar="SNAPSHOT.json",
                    help="verify a stored aggregate snapshot checksum; never scans or changes the endpoint")
    forecast_group = ap.add_mutually_exclusive_group()
    forecast_group.add_argument("--compare", metavar="SNAPSHOT.json",
                                help="compare this mounted filesystem with a prior SANCHAY snapshot")
    forecast_group.add_argument("--history", metavar="SNAPSHOT.json", nargs="+",
                                help="fit a mounted-filesystem linear trend to prior snapshots and this scan")
    ap.add_argument("--risk-horizon", metavar="DAYS", type=parse_risk_horizon_days,
                    help="with --history or --snapshot-history, estimate local capacity-hit risk within DAYS; never changes storage")
    ap.add_argument("--verify-plan", metavar="PLAN.json",
                    help="recheck a review-only plan; never deletes or moves files")
    ap.add_argument("--verify-archive", metavar=("SOURCE", "RETAINED_COPY"),
                    nargs=2,
                    help="verify a separate byte-matching retained copy; never copies, moves, or deletes files")
    ap.add_argument("--verify-operator-brief", metavar="BRIEF.json",
                    help="verify an operator brief checksum; never transmits or changes files")
    ap.add_argument("--tui", action="store_true", help="open the terminal UI")
    args = ap.parse_args(argv)

    if args.cloud_narrative and not args.explain:
        ap.error("--cloud-narrative requires --explain")
    if args.ollama_narrative and not args.explain:
        ap.error("--ollama-narrative requires --explain")
    if args.cloud_narrative and args.ollama_narrative:
        ap.error("choose either --cloud-narrative or --ollama-narrative")
    if args.ollama_model and not args.ollama_narrative:
        ap.error("--ollama-model requires --ollama-narrative")
    if args.snapshot and args.snapshot_history:
        ap.error("use either --snapshot OUT.json or --snapshot-history DIR, not both")
    if args.snapshot_history and (args.compare or args.history):
        ap.error("--snapshot-history cannot combine with --compare or --history")
    if args.risk_horizon is not None and not (args.history or args.snapshot_history):
        ap.error("--risk-horizon requires --history or --snapshot-history")
    if args.snapshot_history:
        try:
            snapshot.history_paths(args.snapshot_history)
        except (OSError, ValueError) as exc:
            ap.error("--snapshot-history is unavailable: " + str(exc))

    if args.verify_plan and args.verify_archive:
        ap.error("use either --verify-plan or --verify-archive, not both")
    if args.verify_operator_brief and (args.verify_plan or args.verify_archive):
        ap.error("use operator brief verification by itself")
    if args.verify_snapshot and (args.verify_plan or args.verify_archive
                                 or args.verify_operator_brief):
        ap.error("use snapshot verification by itself")
    if args.verify_plan and args.capacity_audit:
        ap.error("--capacity-audit requires a scan root, not --verify-plan")
    if args.verify_plan and args.operator_brief:
        ap.error("--operator-brief requires a scan root, not --verify-plan")
    if args.verify_plan and args.snapshot_history:
        ap.error("--snapshot-history requires a scan root, not --verify-plan")

    if args.cross_filesystems and any((
            args.target_reclaim is not None, args.snapshot, args.snapshot_history,
            args.compare,
            args.history, args.risk_horizon is not None, args.capacity_audit)):
        ap.error("--cross-filesystems cannot use a capacity audit, shared reclaim "
                 "target, or capacity history across mounts; scan one filesystem per capacity plan")

    if args.verify_plan:
        try:
            document = plan.read(args.verify_plan)
            result = plan.verify(document)
        except (OSError, ValueError) as exc:
            print(f"plan: unavailable for review ({exc})")
            return 2
        state = "valid for human review" if result["valid"] else "not valid for review"
        print(f"plan: {state}")
        print(f"integrity checksum: {'matches' if result['fingerprint_valid'] else 'does not match'}")
        coverage = document["safety"]["scan_coverage"]
        if coverage["complete"]:
            print("scan coverage: complete; all in-scope, non-sensitive paths were inspected")
        else:
            print("scan coverage: incomplete; "
                  f"{coverage['unreadable_directories']:,} directory(ies) and "
                  f"{coverage['unreadable_files']:,} file(s) were not inspected")
            print("  this plan contains evidence only for readable files; it is not a "
                  "whole-tree capacity result")
        if result.get("reason"):
            print(f"reason: {result['reason']}")
        for item in result["recommendations"]:
            verdict = "ok" if item["valid"] else "; ".join(item["reasons"])
            print(f"- {item['kind']}: {item['path']} — {verdict}")
        return 0 if result["valid"] else 1

    if args.verify_operator_brief:
        if any((args.root, args.cross_filesystems, args.explain, args.viz,
                args.report, args.operator_brief, args.plan,
                args.target_reclaim is not None, args.snapshot, args.snapshot_history,
                args.compare,
                args.history, args.risk_horizon is not None, args.capacity_audit,
                args.tui)):
            ap.error("--verify-operator-brief is a standalone read-only check")
        try:
            document = brief.read(args.verify_operator_brief)
        except (OSError, ValueError) as exc:
            print(f"operator brief: unavailable for review ({exc})")
            return 2
        valid = brief.fingerprint_valid(document)
        print("operator brief: integrity checksum "
              + ("matches" if valid else "does not match"))
        print("action boundary: no file was read from the endpoint, transmitted, or changed")
        return 0 if valid else 1

    if args.verify_snapshot:
        if any((args.root, args.cross_filesystems, args.explain, args.viz,
                args.report, args.operator_brief, args.plan,
                args.target_reclaim is not None, args.snapshot, args.snapshot_history,
                args.compare,
                args.history, args.risk_horizon is not None, args.capacity_audit,
                args.tui)):
            ap.error("--verify-snapshot is a standalone read-only check")
        try:
            document = snapshot.read(args.verify_snapshot)
        except snapshot.SnapshotIntegrityError as exc:
            print(f"snapshot: not valid ({exc})")
            print("action boundary: no endpoint directory was scanned, transmitted, or changed")
            return 1
        except (OSError, ValueError) as exc:
            print(f"snapshot: unavailable for review ({exc})")
            return 2
        print("snapshot: integrity checksum matches")
        print("snapshot evidence: "
              f"{document['readable_file_count']:,} readable file entries; "
              "aggregate mounted-filesystem counters")
        print("integrity boundary: detects a mismatch against the stored checksum; "
              "not a signature or device attestation")
        print("action boundary: no endpoint directory was scanned, transmitted, or changed")
        return 0

    if args.verify_archive:
        if any((args.root, args.cross_filesystems, args.explain, args.viz,
                args.report, args.plan, args.target_reclaim is not None,
                args.snapshot, args.compare, args.history, args.capacity_audit,
                args.snapshot_history,
                args.operator_brief,
                args.verify_operator_brief,
                args.risk_horizon is not None,
                args.tui)):
            ap.error("--verify-archive is a standalone read-only check")
        try:
            result = archive.verify(*args.verify_archive)
        except (OSError, ValueError) as exc:
            print(f"archive: unavailable for review ({exc})")
            return 2
        state = "verified retained copy" if result["verified"] else "not verified"
        print(f"archive: {state}")
        print("comparison: byte-for-byte stream; separate inode: "
              + ("yes" if result["separate_inode"] else "no"))
        print(f"source reclaim on manual review: {human(result['reclaimable_allocated_bytes'])}")
        if result["verified"]:
            print("storage boundary: " + result["storage_boundary"])
        else:
            print("reason: " + result["reason"])
        print("action boundary: no file was copied, moved, or deleted")
        return 0 if result["verified"] else 1

    if not args.root:
        ap.error("ROOT is required unless --verify-plan is used")

    if args.tui:
        if args.cross_filesystems:
            ap.error("--tui supports one filesystem; use the CLI for a "
                     "cross-filesystem inventory")
        from . import tui
        return tui.run(args.root)

    try:
        files, coverage_record = scan.scan_with_coverage(
            args.root, cross_filesystems=args.cross_filesystems)
    except ValueError as exc:
        ap.error(str(exc))
    artifact_paths = _invocation_artifact_paths(args)
    artifact_entries = [
        info for info in files
        if os.path.normcase(os.path.abspath(info.path))
        in artifact_paths
    ]
    if artifact_entries:
        files = [
            info for info in files
            if os.path.normcase(os.path.abspath(info.path))
            not in artifact_paths
        ]
    scan_coverage = coverage_record.as_dict()
    total = storage.physical_bytes(files)
    logical_total = storage.logical_bytes(files)
    aliases = storage.hardlink_alias_count(files)
    filesystem_context = mounts.capacity_context(args.root)
    devices = {getattr(info, "device", None)
               for info in storage.physical_records(files)}
    if args.cross_filesystems and devices:
        count = len(devices)
        storage_scope = f" across {count:,} filesystem{'s' if count != 1 else ''}"
    elif args.cross_filesystems:
        storage_scope = " from a cross-filesystem inventory"
    else:
        storage_scope = ""
    print(f"{len(files):,} file entries, {human(total)} allocated storage{storage_scope}")
    if logical_total != total:
        print(f"{human(logical_total)} logical length; sparse allocation is not overstated")
    if aliases:
        print(f"{aliases:,} hardlink aliases are not double-counted")
    if artifact_entries:
        noun = "file" if len(artifact_entries) == 1 else "files"
        print(f"{len(artifact_entries):,} SANCHAY artifact {noun} supplied to this command "
              "excluded from readable inventory")
    if filesystem_context:
        print(f"filesystem: {filesystem_context['filesystem']} at "
              f"{filesystem_context['mount_point']} "
              f"({filesystem_context['source_class']})")
        if filesystem_context.get("advisory"):
            print(f"capacity: {filesystem_context['advisory']}")
            print(f"  review: {filesystem_context['review_action']}")
        if filesystem_context.get("nested_mount_boundary"):
            print("mount topology: " + filesystem_context["nested_mount_boundary"])
            print("  review: " + filesystem_context["nested_mount_review_action"])
    if not scan_coverage["complete"]:
        print("coverage: incomplete; "
              f"{scan_coverage['unreadable_directories']:,} directory(ies) and "
              f"{scan_coverage['unreadable_files']:,} file(s) could not be inspected")
        print("  inventory and growth claims apply only to readable files; "
              "snapshots are withheld")
    print()

    groups = dedup.duplicates(managed.content_candidates(files), root=args.root)
    print(f"duplicates: {len(groups)} groups, {human(dedup.reclaimable(groups))} potential allocated reclaim")

    process_devices = {device for device in devices if device is not None}
    if not process_devices:
        try:
            process_devices.add(os.stat(args.root).st_dev)
        except OSError:
            pass
    held_deleted = processes.deleted_open_files(process_devices or None)
    if held_deleted:
        print(f"process-held deleted: {human(processes.allocated_total(held_deleted))} "
              f"across {len(held_deleted):,} deleted inode(s); not in file cleanup plan")
        for record in held_deleted[:5]:
            holder = record.holders[0]
            more_holders = (f" (+{len(record.holders) - 1} holder(s))"
                            if len(record.holders) > 1 else "")
            print(f"  {human(record.allocated_size)} pid {holder.pid} "
                  f"({holder.process}) fd {holder.fd}{more_holders}: {holder.path}")
        print("  review the owning service lifecycle; SANCHAY never signals, "
              "restarts, truncates, or deletes process-held storage")

    usage = None if args.cross_filesystems else shutil.disk_usage(args.root)
    free = None if usage is None else usage.free
    capacity_accounting = None
    if args.capacity_audit:
        root_is_mount = mounts.is_mount_root(args.root)
        capacity_accounting = accounting.assess(
            files, usage.used,
            process_held_bytes=processes.allocated_total(held_deleted),
            scan_coverage=scan_coverage,
            root_is_mount=root_is_mount,
            cross_filesystems=args.cross_filesystems,
        )
        capacity_accounting["inode_capacity"] = accounting.assess_inode_capacity(
            args.root,
            scan_coverage=scan_coverage,
            root_is_mount=root_is_mount,
            cross_filesystems=args.cross_filesystems,
        )
        capacity_accounting["block_availability"] = accounting.assess_block_availability(
            args.root,
            scan_coverage=scan_coverage,
            root_is_mount=root_is_mount,
            cross_filesystems=args.cross_filesystems,
        )
        if capacity_accounting["assessed"]:
            gap = capacity_accounting["accounting_gap_bytes"]
            print("capacity audit: filesystem used "
                  f"{human(capacity_accounting['filesystem_used_bytes'])}; "
                  f"readable inventory {human(capacity_accounting['readable_file_allocated_bytes'])}; "
                  f"visible deleted-open {human(capacity_accounting['deleted_open_allocated_bytes'])}")
            print(f"  accounting gap: {'+' if gap >= 0 else '-'}{human(abs(gap))} "
                  f"({capacity_accounting['gap_direction']})")
            print("  boundary: " + capacity_accounting["boundary"])
        else:
            print("capacity audit: not assessed; " + capacity_accounting["reason"])
        inode_capacity = capacity_accounting["inode_capacity"]
        if inode_capacity["assessed"]:
            print("inode capacity: "
                  f"{inode_capacity['total_inodes']:,} file entries; "
                  f"{inode_capacity['free_inodes']:,} free; "
                  f"{inode_capacity['used_percent']:.1f}% used")
            if inode_capacity["available_inodes"] is not None:
                print("  available to an unprivileged process: "
                      f"{inode_capacity['available_inodes']:,} file entries")
            print("  boundary: " + inode_capacity["boundary"])
        else:
            print("inode capacity: not assessed; " + inode_capacity["reason"])
        block_availability = capacity_accounting["block_availability"]
        if block_availability["assessed"]:
            print("block availability: "
                  f"{human(block_availability['free_bytes'])} free; "
                  f"{human(block_availability['available_bytes'])} available to "
                  "an unprivileged process")
            unavailable = block_availability["free_unavailable_to_unprivileged_bytes"]
            if unavailable:
                print("  free but unavailable to an unprivileged process: "
                      + human(unavailable))
            print("  boundary: " + block_availability["boundary"])
        else:
            print("block availability: not assessed; " + block_availability["reason"])
    needs_snapshot = bool(args.snapshot or args.snapshot_history or args.compare or args.history
                          or args.risk_horizon is not None)
    current_snapshot = None
    snapshot_error = None
    snapshot_write_error = None
    snapshot_history_write_error = None
    if needs_snapshot and usage is not None and scan_coverage["complete"]:
        try:
            current_snapshot = snapshot.capture(
                files, args.root,
                filesystem_total_bytes=usage.total,
                filesystem_used_bytes=usage.used,
                filesystem_free_bytes=usage.free,
                filesystem_device=os.stat(args.root).st_dev,
                scan_coverage=scan_coverage)
        except (AttributeError, OSError, ValueError) as exc:
            snapshot_error = str(exc)

    observed = None
    trend = None
    capacity_risk = None
    growth_error = None
    if args.compare and current_snapshot is not None:
        try:
            observed = snapshot.observed_growth(
                snapshot.read(args.compare), current_snapshot)
        except (OSError, ValueError) as exc:
            growth_error = str(exc)
    elif (args.history or args.snapshot_history) and current_snapshot is not None:
        try:
            history = (snapshot.read_history(args.snapshot_history)
                       if args.snapshot_history
                       else [snapshot.read(path) for path in args.history])
            historical_snapshots = history + [current_snapshot]
            trend = snapshot.linear_trend(historical_snapshots)
            if args.risk_horizon is not None:
                capacity_risk = snapshot.capacity_risk(
                    historical_snapshots, args.risk_horizon)
        except (OSError, ValueError) as exc:
            growth_error = str(exc)
    elif (args.compare or args.history) and snapshot_error:
        growth_error = snapshot_error

    if args.cross_filesystems:
        print("growth:     not calculated across multiple filesystems; scan one "
              "filesystem for a capacity forecast")
    elif not scan_coverage["complete"]:
        print("growth:     not calculated; scan coverage is incomplete")
    elif growth_error:
        print("growth:     not calculated; " + growth_error)
    elif trend and trend["bytes_per_day"] is None:
        print("growth:     not calculated; snapshot history spans "
              f"{trend['elapsed_seconds'] / 3600:.1f} hours; wait for at least "
              f"{trend['minimum_span_seconds'] / 3600:.0f} hours")
    elif trend and trend["bytes_per_day"] > 0:
        fit = (f", R² {trend['r_squared']:.2f}"
               if trend["r_squared"] is not None else "")
        readiness = snapshot.runway_readiness(trend)
        if readiness["ready"]:
            days = free / trend["bytes_per_day"]
            print(f"growth:     {human(trend['bytes_per_day'])}/day mounted-filesystem trend from "
                  f"{trend['sample_count']} snapshots{fit}, full in {forecast.runway_label(days)}")
        else:
            print(f"growth:     {human(trend['bytes_per_day'])}/day mounted-filesystem trend from "
                  f"{trend['sample_count']} snapshots{fit}; runway withheld: "
                  + readiness["reason"])
    elif trend:
        print(f"growth:     {human(trend['bytes_per_day'])}/day mounted-filesystem trend from "
              f"{trend['sample_count']} snapshots; no projected exhaustion")
    elif observed and observed["bytes_per_day"] is None:
        print("growth:     not calculated; snapshots are "
              f"{observed['elapsed_seconds'] / 3600:.1f} hours apart; wait for at least "
              f"{observed['minimum_span_seconds'] / 3600:.0f} hours")
    elif observed and observed["bytes_per_day"] > 0:
        print(f"growth:     {human(observed['bytes_per_day'])}/day observed mounted-filesystem use over "
              f"{observed['elapsed_seconds'] / 86400:.1f} days; runway withheld: "
              + snapshot.runway_readiness(observed)["reason"])
    elif observed:
        print(f"growth:     {human(observed['bytes_per_day'])}/day observed mounted-filesystem use over "
              f"{observed['elapsed_seconds'] / 86400:.1f} days; no projected exhaustion")
    else:
        days = forecast.days_until_full(files, free)
        print(f"growth:     {human(forecast.rate(files))}/day readable-inventory mtime orientation; "
              + "not a capacity forecast; "
              + (f"directional full-in indicator {forecast.runway_label(days)}"
                 if days else "no measurable growth")
              + "; save a snapshot to measure future net growth")

    if args.risk_horizon is not None:
        if capacity_risk is not None and capacity_risk["assessed"]:
            print(
                "capacity risk: "
                f"{capacity_risk['risk_probability'] * 100:.1f}% probability of reaching "
                f"current mounted-filesystem capacity within "
                f"{capacity_risk['horizon_days']} days from "
                f"{capacity_risk['sample_count']} local snapshots")
            print(
                "  model: Brownian-motion-with-drift estimate over aggregate "
                f"used-byte changes; drift {human(capacity_risk['drift_bytes_per_day'])}/day, "
                f"volatility {human(capacity_risk['volatility_bytes_per_sqrt_day'])}/sqrt(day)")
            print("  boundary: " + capacity_risk["boundary"])
        elif capacity_risk is not None:
            print("capacity risk: withheld; " + capacity_risk["reason"])
            print("  boundary: " + capacity_risk["boundary"])
        elif growth_error:
            print("capacity risk: withheld; " + growth_error)
        elif not scan_coverage["complete"]:
            print("capacity risk: withheld; complete scan coverage is required")
        else:
            print("capacity risk: withheld; current mounted-filesystem history is unavailable")

    cleanup_plan = plan.build(files, groups, args.root, limit=args.limit,
                              target_reclaim_bytes=args.target_reclaim,
                              cross_filesystems=args.cross_filesystems,
                              filesystem_context=filesystem_context,
                              scan_coverage=scan_coverage)
    rows = cleanup_plan["recommendations"]
    excluded = cleanup_plan["safety"]["protected_unique_files"]
    print(f"candidates: {len(rows)} shown, {cleanup_plan['safety']['candidate_count']:,} eligible, "
          f"{excluded:,} irreplaceable files excluded")
    hardlinks = cleanup_plan["safety"]["excluded_hardlink_entries"]
    if hardlinks:
        print(f"hardlinks: {hardlinks:,} entries excluded; a single link removal releases no physical bytes")
    managed_storage = cleanup_plan["safety"]["managed_operational_storage"]
    if managed_storage:
        print(f"managed: {human(cleanup_plan['safety']['deferred_managed_bytes'])} across "
              f"{cleanup_plan['safety']['deferred_managed_entries']:,} entries deferred "
              "to their owning tools; never selected as file cleanup candidates")
        for item in managed_storage:
            print(f"  {item['label']}: {human(item['allocated_bytes'])} — "
                  f"{item['review_action']}")
    selection = cleanup_plan.get("selection")
    if selection:
        state = "target met" if selection["target_met"] else (
            f"short by {human(selection['shortfall_bytes'])}")
        print(f"intent: reclaim {human(selection['target_reclaim_bytes'])}; "
              f"{human(selection['selected_reclaim_bytes'])} selected ({state})")
    print()

    print(f"{'reclaim':>10}  {'kind':<11} {'unchanged':>9}  path")
    print("-" * 78)
    for r in rows:
        print(f"{human(r['size']):>10}  {r['kind']:<11} "
              f"{r['staleness'] * 365:>7.1f}d  {r['path']}")

    if args.report:
        try:
            from . import report
            report_path = report.build(
                files, args.root, free, args.report,
                target_reclaim_bytes=args.target_reclaim,
                cross_filesystems=args.cross_filesystems,
                process_held=held_deleted,
                filesystem_context=filesystem_context,
                scan_coverage=scan_coverage,
                capacity_accounting=capacity_accounting)
        except ModuleNotFoundError as exc:
            if _visualization_dependency_missing("report", exc):
                return 2
            raise
        print("report -> " + report_path)

    if args.operator_brief:
        operator_brief = brief.build(
            files, cleanup_plan, process_held=held_deleted,
            capacity_accounting=capacity_accounting,
            capacity_risk=capacity_risk,
            capacity_risk_requested=args.risk_horizon is not None)
        print("operator brief -> " + brief.write(operator_brief, args.operator_brief))

    if args.plan:
        print("plan -> " + plan.write(cleanup_plan, args.plan))

    if args.snapshot:
        if current_snapshot is None:
            reason = ("complete scan coverage is required" if not scan_coverage["complete"]
                      else snapshot_error or "mounted filesystem usage is unavailable")
            print("snapshot: not written; " + reason)
        else:
            try:
                written_snapshot = snapshot.write(current_snapshot, args.snapshot)
            except (OSError, ValueError) as exc:
                snapshot_write_error = str(exc)
                print("snapshot: not written; " + snapshot_write_error)
            else:
                print("snapshot -> " + written_snapshot)

    if args.snapshot_history:
        if current_snapshot is None:
            reason = ("complete scan coverage is required" if not scan_coverage["complete"]
                      else snapshot_error or "mounted filesystem usage is unavailable")
            print("snapshot history: not written; " + reason)
        elif growth_error:
            print("snapshot history: not written; existing history is unavailable ("
                  + growth_error + ")")
        else:
            try:
                written_history = snapshot.write_history(
                    current_snapshot, args.snapshot_history)
            except (OSError, ValueError) as exc:
                snapshot_history_write_error = str(exc)
                print("snapshot history: not written; " + snapshot_history_write_error)
            else:
                print("snapshot history -> " + written_history)

    if args.viz:
        try:
            from . import viz
            treemap_path = viz.treemap(
                files, plan.duplicate_evidence_paths(cleanup_plan), args.viz,
                root=args.root)
        except ModuleNotFoundError as exc:
            if _visualization_dependency_missing("treemap", exc):
                return 2
            raise
        print(f"\ntreemap -> {treemap_path}")

    if args.explain:
        print("\n" + explain.explain(
            rows,
            allow_cloud=args.cloud_narrative,
            allow_ollama=args.ollama_narrative,
            ollama_model=args.ollama_model,
        ))

    if (not scan_coverage["complete"]
            and (args.snapshot or args.snapshot_history or args.compare or args.history)):
        return 2
    if (snapshot_error or snapshot_write_error or snapshot_history_write_error
            or growth_error):
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
