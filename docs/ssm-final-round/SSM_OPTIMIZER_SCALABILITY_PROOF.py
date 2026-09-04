"""Verify SANCHAY's documented large-candidate optimizer boundary.

Run from the SANCHAY checkout so this imports the selected local source:

    PYTHONDONTWRITEBYTECODE=1 python3 /path/to/SSM_OPTIMIZER_SCALABILITY_PROOF.py

This constructs in-memory regenerable cache records only. It does not walk,
read, write, delete, move, or transmit endpoint data. It proves the documented
deterministic greedy fallback above the exact-search limit; it does not claim
globally minimum excess at that larger size.
"""

import sys
from pathlib import Path
from time import perf_counter, time


SOURCE_ROOT = Path.cwd()
if not (SOURCE_ROOT / "sanchay").is_dir():
    raise SystemExit("run this verifier from the SANCHAY repository root")
sys.path.insert(0, str(SOURCE_ROOT))

from sanchay import plan, scan


def _recommendation_paths(document):
    return [item["path"] for item in document["recommendations"]]


def main():
    count = plan.EXACT_TARGET_SELECTION_LIMIT + 1
    now = time()
    candidates = [
        scan.FileInfo(
            path=f"/benchmark-root/workspace/node_modules/.cache/item-{index:02d}.bin",
            size=((index * 7919) % 100_003) + 4096,
            atime=now,
            mtime=now - 90 * 86400,
            inode=20_000 + index,
        )
        for index in range(count)
    ]
    target = sum(item.size for item in candidates) // 2

    started = perf_counter()
    baseline = plan.build(
        candidates,
        [],
        "/benchmark-root",
        now=now,
        target_reclaim_bytes=target,
    )
    elapsed = perf_counter() - started
    reordered = plan.build(
        list(reversed(candidates)),
        [],
        "/benchmark-root",
        now=now,
        target_reclaim_bytes=target,
    )

    selection = baseline["selection"]
    step = selection["optimizer"]["class_steps"][0]
    if step["strategy"] != "greedy_fallback_above_exact_limit":
        raise SystemExit("unexpected optimizer strategy above exact boundary")
    if step["candidate_count"] != count:
        raise SystemExit("candidate count was not preserved in optimizer trace")
    if not selection["target_met"]:
        raise SystemExit("fallback-boundary fixture did not meet reclaim target")
    if _recommendation_paths(baseline) != _recommendation_paths(reordered):
        raise SystemExit("fallback selection changed when equivalent input order changed")
    if (selection["selected_reclaim_bytes"]
            != reordered["selection"]["selected_reclaim_bytes"]):
        raise SystemExit("fallback selected-byte total changed when input order changed")

    print(f"FALLBACK_CANDIDATE_COUNT={count}")
    print(f"FALLBACK_TARGET_BYTES={target}")
    print(f"FALLBACK_SELECTED_BYTES={selection['selected_reclaim_bytes']}")
    print(f"FALLBACK_STRATEGY={step['strategy']}")
    print("FALLBACK_INPUT_ORDER_DETERMINISTIC=PASS")
    print(f"FALLBACK_RUNTIME_SECONDS={elapsed:.6f}")


if __name__ == "__main__":
    main()
