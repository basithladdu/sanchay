"""sanchay -- regret-aware storage intelligence for Linux."""
import argparse
import os
import re
import shutil

from . import (dedup, explain, forecast, managed, mounts, plan, processes,
               regret, scan, snapshot, storage)


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
    ap.add_argument("--report", metavar="OUT.html", help="write a shareable HTML report")
    ap.add_argument("--plan", metavar="OUT.json",
                    help="write a review-only cleanup plan; SANCHAY never deletes files")
    ap.add_argument("--target-reclaim", metavar="SIZE", type=parse_reclaim_bytes,
                    help="select enough reviewable candidates to reclaim SIZE (for example 600M); never deletes files")
    ap.add_argument("--snapshot", metavar="OUT.json",
                    help="save aggregate local usage for a later observed-growth comparison")
    forecast_group = ap.add_mutually_exclusive_group()
    forecast_group.add_argument("--compare", metavar="SNAPSHOT.json",
                                help="compare this scan with a prior SANCHAY snapshot")
    forecast_group.add_argument("--history", metavar="SNAPSHOT.json", nargs="+",
                                help="fit a local linear trend to prior snapshots and this scan")
    ap.add_argument("--verify-plan", metavar="PLAN.json",
                    help="recheck a review-only plan; never deletes or moves files")
    ap.add_argument("--tui", action="store_true", help="open the terminal UI")
    args = ap.parse_args(argv)

    if args.cloud_narrative and not args.explain:
        ap.error("--cloud-narrative requires --explain")

    if args.cross_filesystems and any((
            args.target_reclaim is not None, args.snapshot, args.compare,
            args.history)):
        ap.error("--cross-filesystems cannot share a reclaim target or capacity "
                 "history across mounts; scan one filesystem per capacity plan")

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

    free = None if args.cross_filesystems else shutil.disk_usage(args.root).free
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
        from . import report
        print("report -> " + report.build(files, args.root, free, args.report,
                                           target_reclaim_bytes=args.target_reclaim,
                                           cross_filesystems=args.cross_filesystems,
                                           process_held=held_deleted,
                                           filesystem_context=filesystem_context,
                                           scan_coverage=scan_coverage))

    if args.plan:
        print("plan -> " + plan.write(cleanup_plan, args.plan))

    if args.snapshot:
        if current_snapshot is None:
            print("snapshot: not written; complete scan coverage is required")
        else:
            print("snapshot -> " + snapshot.write(current_snapshot, args.snapshot))

    if args.viz:
        from . import viz
        print(f"\ntreemap -> {viz.treemap(files, plan.duplicate_evidence_paths(cleanup_plan), args.viz, root=args.root)}")

    if args.explain:
        print("\n" + explain.explain(rows, allow_cloud=args.cloud_narrative))

    if (not scan_coverage["complete"]
            and (args.snapshot or args.compare or args.history)):
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
