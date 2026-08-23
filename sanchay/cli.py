"""sanchay -- regret-aware storage intelligence for Linux."""
import argparse
import shutil

from . import dedup, explain, forecast, regret, scan, viz


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sanchay", description=__doc__)
    ap.add_argument("root")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--explain", action="store_true", help="narrate with an LLM")
    ap.add_argument("--viz", metavar="OUT.html", help="write a regret treemap")
    args = ap.parse_args(argv)

    files = scan.scan(args.root)
    total = sum(f.size for f in files)
    print(f"{len(files):,} files, {human(total)}\n")

    groups = dedup.duplicates(files)
    dup_paths = {f.path for g in groups for f in g[1:]}
    print(f"duplicates: {len(groups)} groups, {human(dedup.reclaimable(groups))} reclaimable")

    free = shutil.disk_usage(args.root).free
    days = forecast.days_until_full(files, free)
    print(f"growth:     {human(forecast.rate(files))}/day, "
          + (f"full in {days:.0f} days" if days else "no measurable growth"))

    rows = regret.rank(files, dup_paths, limit=args.limit)
    excluded = sum(1 for f in files if regret.classify(f, f.path in dup_paths) == "unique")
    print(f"candidates: {len(rows)} safe, {excluded:,} irreplaceable files excluded\n")

    print(f"{'size':>10}  {'kind':<11} {'unused':>8}  path")
    print("-" * 78)
    for r in rows:
        print(f"{human(r['size']):>10}  {r['kind']:<11} "
              f"{r['staleness'] * 365:>6.1f}d  {r['path']}")

    if args.viz:
        print(f"\ntreemap -> {viz.treemap(files, dup_paths, args.viz)}")

    if args.explain:
        print("\n" + explain.explain(rows))


if __name__ == "__main__":
    main()
