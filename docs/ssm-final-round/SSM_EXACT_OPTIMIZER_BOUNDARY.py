"""Measure SANCHAY's documented exact target-selection boundary.

Run from the SANCHAY checkout so it imports the selected local source:

    PYTHONDONTWRITEBYTECODE=1 python3 /path/to/SSM_EXACT_OPTIMIZER_BOUNDARY.py

This constructs in-memory, regenerable cache records only. It does not walk,
read, write, delete, move, or transmit endpoint data.
"""

import sys
from pathlib import Path
from time import perf_counter, time


SOURCE_ROOT = Path.cwd()
if not (SOURCE_ROOT / "sanchay").is_dir():
    raise SystemExit("run this verifier from the SANCHAY repository root")
sys.path.insert(0, str(SOURCE_ROOT))

from sanchay import plan, scan


def main():
    count = plan.EXACT_TARGET_SELECTION_LIMIT
    now = time()
    candidates = [
        scan.FileInfo(
            path=f"/benchmark-root/workspace/node_modules/.cache/item-{index:02d}.bin",
            size=((index * 7919) % 100_003) + 4096,
            atime=now,
            mtime=now - 90 * 86400,
            inode=10_000 + index,
        )
        for index in range(count)
    ]
    target = sum(item.size for item in candidates) // 2

    started = perf_counter()
    document = plan.build(
        candidates,
        [],
        "/benchmark-root",
        now=now,
        target_reclaim_bytes=target,
    )
    elapsed = perf_counter() - started
    selection = document["selection"]
    step = selection["optimizer"]["class_steps"][0]

    if step["strategy"] != "exact_minimum_excess_subset":
        raise SystemExit("unexpected optimizer strategy at exact boundary")
    if not selection["target_met"]:
        raise SystemExit("exact-boundary fixture did not meet its reclaim target")

    print(f"EXACT_CANDIDATE_COUNT={count}")
    print(f"EXACT_TARGET_BYTES={target}")
    print(f"EXACT_SELECTED_BYTES={selection['selected_reclaim_bytes']}")
    print(f"EXACT_STRATEGY={step['strategy']}")
    print(f"EXACT_RUNTIME_SECONDS={elapsed:.6f}")


if __name__ == "__main__":
    main()
