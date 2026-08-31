"""sanchay -- regret-aware storage intelligence for Linux."""
import argparse
import shutil

from . import dedup, explain, forecast, plan, regret, scan, snapshot


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sanchay", description=__doc__)
    ap.add_argument("root", nargs="?")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--cross-filesystems", action="store_true",
                    help="include mounted filesystems below ROOT (off by default)")
    ap.add_argument("--explain", action="store_true", help="narrate with an LLM")
    ap.add_argument("--viz", metavar="OUT.html", help="write a regret treemap")
    ap.add_argument("--report", metavar="OUT.html", help="write a shareable HTML report")
    ap.add_argument("--plan", metavar="OUT.json",
                    help="write a review-only cleanup plan; SANCHAY never deletes files")
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

    if args.verify_plan:
        try:
            result = plan.verify(plan.read(args.verify_plan))
        except (OSError, ValueError) as exc:
            print(f"plan: unavailable for review ({exc})")
            return 2
        state = "valid for human review" if result["valid"] else "not valid for review"
        print(f"plan: {state}")
        print(f"integrity checksum: {'matches' if result['fingerprint_valid'] else 'does not match'}")
        if result.get("reason"):
            print(f"reason: {result['reason']}")
        for item in result["recommendations"]:
            verdict = "ok" if item["valid"] else "; ".join(item["reasons"])
            print(f"- {item['kind']}: {item['path']} — {verdict}")
        return 0 if result["valid"] else 1

    if not args.root:
        ap.error("ROOT is required unless --verify-plan is used")

    if args.tui:
        from . import tui
        return tui.run(args.root)

    try:
        files = scan.scan(args.root, cross_filesystems=args.cross_filesystems)
    except ValueError as exc:
        ap.error(str(exc))
    total = sum(f.size for f in files)
    print(f"{len(files):,} files, {human(total)}\n")

    groups = dedup.duplicates(files)
    dup_paths = set(dedup.duplicate_map(groups))
    print(f"duplicates: {len(groups)} groups, {human(dedup.reclaimable(groups))} potential duplicate bytes")

    free = shutil.disk_usage(args.root).free
    current_snapshot = snapshot.capture(files, args.root, free)
    observed = None
    trend = None
    if args.compare:
        observed = snapshot.observed_growth(snapshot.read(args.compare), current_snapshot)
    elif args.history:
        history = [snapshot.read(path) for path in args.history]
        trend = snapshot.linear_trend(history + [current_snapshot])

    if trend and trend["bytes_per_day"] > 0:
        days = free / trend["bytes_per_day"]
        fit = (f", R² {trend['r_squared']:.2f}"
               if trend["r_squared"] is not None else "")
        print(f"growth:     {human(trend['bytes_per_day'])}/day local linear trend from "
              f"{trend['sample_count']} snapshots{fit}, full in {days:.0f} days")
    elif trend:
        print(f"growth:     {human(trend['bytes_per_day'])}/day local linear trend from "
              f"{trend['sample_count']} snapshots; no projected exhaustion")
    elif observed and observed["bytes_per_day"] > 0:
        days = free / observed["bytes_per_day"]
        print(f"growth:     {human(observed['bytes_per_day'])}/day observed over "
              f"{observed['elapsed_seconds'] / 86400:.1f} days, full in {days:.0f} days")
    elif observed:
        print(f"growth:     {human(observed['bytes_per_day'])}/day observed over "
              f"{observed['elapsed_seconds'] / 86400:.1f} days; no projected exhaustion")
    else:
        days = forecast.days_until_full(files, free)
        print(f"growth:     {human(forecast.rate(files))}/day mtime estimate, "
              + (f"full in {days:.0f} days" if days else "no measurable growth")
              + "; save a snapshot to measure future net growth")

    cleanup_plan = plan.build(files, groups, args.root, limit=args.limit)
    rows = cleanup_plan["recommendations"]
    excluded = cleanup_plan["safety"]["protected_unique_files"]
    print(f"candidates: {len(rows)} shown, {cleanup_plan['safety']['candidate_count']:,} eligible, "
          f"{excluded:,} irreplaceable files excluded\n")

    print(f"{'size':>10}  {'kind':<11} {'unchanged':>9}  path")
    print("-" * 78)
    for r in rows:
        print(f"{human(r['size']):>10}  {r['kind']:<11} "
              f"{r['staleness'] * 365:>7.1f}d  {r['path']}")

    if args.report:
        from . import report
        print("report -> " + report.build(files, args.root, free, args.report))

    if args.plan:
        print("plan -> " + plan.write(cleanup_plan, args.plan))

    if args.snapshot:
        print("snapshot -> " + snapshot.write(current_snapshot, args.snapshot))

    if args.viz:
        from . import viz
        print(f"\ntreemap -> {viz.treemap(files, dup_paths, args.viz, root=args.root)}")

    if args.explain:
        print("\n" + explain.explain(rows))


if __name__ == "__main__":
    raise SystemExit(main())
