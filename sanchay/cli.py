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


def _visualization_dependency_missing(feature, exc):
    """Print an actionable optional-dependency error when Plotly is absent."""
    missing = exc.name
    if missing not in {"pandas", "plotly"}:
        return False
    print(f"{feature}: visualization support is unavailable; install optional "
          'dependencies with `python -m pip install -e ".[viz]"`')
    return True


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
                    help="save aggregate local usage for a later observed-growth comparison")
    forecast_group = ap.add_mutually_exclusive_group()
    forecast_group.add_argument("--compare", metavar="SNAPSHOT.json",
                                help="compare this scan with a prior SANCHAY snapshot")
    forecast_group.add_argument("--history", metavar="SNAPSHOT.json", nargs="+",
                                help="fit a local linear trend to prior snapshots and this scan")
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

    if args.verify_plan and args.verify_archive:
        ap.error("use either --verify-plan or --verify-archive, not both")
    if args.verify_operator_brief and (args.verify_plan or args.verify_archive):
        ap.error("use operator brief verification by itself")
    if args.verify_plan and args.capacity_audit:
        ap.error("--capacity-audit requires a scan root, not --verify-plan")
    if args.verify_plan and args.operator_brief:
        ap.error("--operator-brief requires a scan root, not --verify-plan")

    if args.cross_filesystems and any((
            args.target_reclaim is not None, args.snapshot, args.compare,
            args.history, args.capacity_audit)):
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
                args.target_reclaim is not None, args.snapshot, args.compare,
                args.history, args.capacity_audit, args.tui)):
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

    if args.verify_archive:
        if any((args.root, args.cross_filesystems, args.explain, args.viz,
                args.report, args.plan, args.target_reclaim is not None,
                args.snapshot, args.compare, args.history, args.capacity_audit,
                args.operator_brief,
                args.verify_operator_brief,
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
    if filesystem_context:
        print(f"filesystem: {filesystem_context['filesystem']} at "
              f"{filesystem_context['mount_point']} "
              f"({filesystem_context['source_class']})")
        if filesystem_context.get("advisory"):
            print(f"capacity: {filesystem_context['advisory']}")
            print(f"  review: {filesystem_context['review_action']}")
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
    current_snapshot = (
        snapshot.capture(files, args.root, free, scan_coverage=scan_coverage)
        if free is not None and scan_coverage["complete"] else None)
    observed = None
    trend = None
    if args.compare and current_snapshot is not None:
        observed = snapshot.observed_growth(snapshot.read(args.compare), current_snapshot)
    elif args.history and current_snapshot is not None:
        history = [snapshot.read(path) for path in args.history]
        trend = snapshot.linear_trend(history + [current_snapshot])

    if args.cross_filesystems:
        print("growth:     not calculated across multiple filesystems; scan one "
              "filesystem for a capacity forecast")
    elif not scan_coverage["complete"]:
        print("growth:     not calculated; scan coverage is incomplete")
    elif trend and trend["bytes_per_day"] > 0:
        days = free / trend["bytes_per_day"]
        fit = (f", R² {trend['r_squared']:.2f}"
               if trend["r_squared"] is not None else "")
        print(f"growth:     {human(trend['bytes_per_day'])}/day local linear trend from "
              f"{trend['sample_count']} snapshots{fit}, full in {forecast.runway_label(days)}")
    elif trend:
        print(f"growth:     {human(trend['bytes_per_day'])}/day local linear trend from "
              f"{trend['sample_count']} snapshots; no projected exhaustion")
    elif observed and observed["bytes_per_day"] > 0:
        days = free / observed["bytes_per_day"]
        print(f"growth:     {human(observed['bytes_per_day'])}/day observed over "
              f"{observed['elapsed_seconds'] / 86400:.1f} days, full in {forecast.runway_label(days)}")
    elif observed:
        print(f"growth:     {human(observed['bytes_per_day'])}/day observed over "
              f"{observed['elapsed_seconds'] / 86400:.1f} days; no projected exhaustion")
    else:
        days = forecast.days_until_full(files, free)
        print(f"growth:     {human(forecast.rate(files))}/day mtime estimate, "
              + (f"full in {forecast.runway_label(days)}" if days else "no measurable growth")
              + "; save a snapshot to measure future net growth")

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
            capacity_accounting=capacity_accounting)
        print("operator brief -> " + brief.write(operator_brief, args.operator_brief))

    if args.plan:
        print("plan -> " + plan.write(cleanup_plan, args.plan))

    if args.snapshot:
        if current_snapshot is None:
            print("snapshot: not written; complete scan coverage is required")
        else:
            print("snapshot -> " + snapshot.write(current_snapshot, args.snapshot))

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
        print("\n" + explain.explain(rows, allow_cloud=args.cloud_narrative))

    if (not scan_coverage["complete"]
            and (args.snapshot or args.compare or args.history)):
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
