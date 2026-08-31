"""Create a harmless fixture for a real, repeatable SANCHAY demonstration."""
import argparse
import contextlib
import io
import os
from pathlib import Path
import tempfile
import time


_DUPLICATE_BYTES = bytes(range(256)) * 2048
_CACHE_BYTES = b"regenerable-build-output\n" * 8192


def _write(path, content, age_days):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    when = time.time() - age_days * 86400
    os.utime(path, (when, when))


def create(root=None):
    """Create a disposable fixture and return its resolved root path.

    The caller may provide an empty directory. Refusing non-empty directories
    prevents a demo command from being mistaken for a cleanup command.
    """
    if root is None:
        fixture = Path(tempfile.mkdtemp(prefix="sanchay-demo-"))
    else:
        fixture = Path(root).expanduser().resolve()
        if fixture.exists() and not fixture.is_dir():
            raise ValueError(f"Demo root is not a directory: {fixture}")
        if fixture.exists() and any(fixture.iterdir()):
            raise ValueError(f"Refusing to write into non-empty directory: {fixture}")
        fixture.mkdir(parents=True, exist_ok=True)

    _write(fixture / "workspace" / "node_modules" / ".cache" / "bundle.bin",
           _CACHE_BYTES, age_days=45)
    _write(fixture / "archive" / "boss-image.iso", _DUPLICATE_BYTES, age_days=120)
    _write(fixture / "downloads" / "boss-image-copy.iso", _DUPLICATE_BYTES,
           age_days=120)
    _write(fixture / "documents" / "capstone-thesis.txt",
           b"This is a unique demonstration document.\n", age_days=300)

    hardlink_source = fixture / "hardlinks" / "source.bin"
    _write(hardlink_source, b"one physical file, two directory entries\n" * 2048,
           age_days=90)
    os.link(hardlink_source, fixture / "hardlinks" / "alias.bin")
    return fixture


def rehearse(root=None):
    """Exercise the final-round safety proof against a disposable fixture.

    The rehearsal deliberately changes only the synthetic cache entry after a
    valid plan has been created.  It proves that plan verification fails closed
    when an eligible candidate changes; it never deletes, moves, or transmits a
    file.  The temporary plan is kept outside the fixture so it cannot affect
    the scan or become a recommendation.
    """
    # Import lazily so fixture creation stays usable without the CLI entrypoint.
    from . import cli, plan

    fixture = create(root)
    cache = fixture / "workspace" / "node_modules" / ".cache" / "bundle.bin"
    thesis = fixture / "documents" / "capstone-thesis.txt"
    duplicate = fixture / "downloads" / "boss-image-copy.iso"
    survivor = fixture / "archive" / "boss-image.iso"
    hardlink_paths = {
        str(fixture / "hardlinks" / "source.bin"),
        str(fixture / "hardlinks" / "alias.bin"),
    }

    with tempfile.TemporaryDirectory(prefix="sanchay-rehearsal-") as evidence_dir:
        plan_path = Path(evidence_dir) / "cleanup-plan.json"
        with contextlib.redirect_stdout(io.StringIO()):
            scan_status = cli.main([
                str(fixture), "--target-reclaim", "600K", "--limit", "10",
                "--plan", str(plan_path),
            ])
            archive_status = cli.main([
                "--verify-archive", str(duplicate), str(survivor),
            ])
            before_status = cli.main(["--verify-plan", str(plan_path)])

        if scan_status not in (None, 0):
            raise RuntimeError("SANCHAY could not create the disposable rehearsal plan")
        if archive_status not in (None, 0):
            raise RuntimeError("SANCHAY could not verify the disposable retained survivor")
        if before_status not in (None, 0):
            raise RuntimeError("A freshly created rehearsal plan did not verify")

        document = plan.read(plan_path)
        recommendation_paths = {item["path"] for item in document["recommendations"]}
        duplicate_items = [
            item for item in document["recommendations"]
            if item["kind"] == "duplicate" and item["path"] == str(duplicate)
        ]
        if str(thesis) in recommendation_paths:
            raise RuntimeError("The unique demonstration document entered the review plan")
        if hardlink_paths & recommendation_paths:
            raise RuntimeError("A hardlink entry entered the review plan")
        if not duplicate_items or duplicate_items[0].get("survivor_path") != str(survivor):
            raise RuntimeError("The duplicate recommendation did not name its evidence peer")
        retention = duplicate_items[0].get("retention_boundary", {})
        if (retention.get("source_of_truth_inferred") is not False
                or retention.get("operator_retention_confirmation_required") is not True):
            raise RuntimeError("The duplicate recommendation inferred a retention decision")
        if not document.get("selection", {}).get("target_met"):
            raise RuntimeError("The disposable evidence set did not meet its reclaim target")
        target_steps = document["selection"].get("optimizer", {}).get("class_steps", [])
        target_strategies = tuple(step.get("strategy") for step in target_steps)
        if target_strategies != (
                "all_lower_risk_candidates", "exact_minimum_excess_subset"):
            raise RuntimeError("The disposable target did not preserve its optimizer boundary")

        with cache.open("ab") as changed_fixture:
            changed_fixture.write(b"rehearsal mutation: verification must fail closed\n")
        with contextlib.redirect_stdout(io.StringIO()):
            after_status = cli.main(["--verify-plan", str(plan_path)])
        if after_status != 1:
            raise RuntimeError("The changed synthetic candidate did not invalidate its review plan")

    return {
        "fixture": fixture,
        "protected_relative_path": thesis.relative_to(fixture).as_posix(),
        "duplicate_relative_path": duplicate.relative_to(fixture).as_posix(),
        "survivor_relative_path": survivor.relative_to(fixture).as_posix(),
        "excluded_hardlink_entries": document["safety"]["excluded_hardlink_entries"],
        "selected_reclaim_bytes": document["selection"]["selected_reclaim_bytes"],
    }


def rehearse_capacity_risk():
    """Exercise the capacity-risk evidence gate with synthetic aggregates.

    This does not create a fixture, scan a root, or query an endpoint. The
    empty file list and supplied accounting values create schema-valid, wholly
    in-memory snapshots so a final-round rehearsal can show the model's
    evidence threshold and its capacity-change withholding behavior honestly.
    """
    from . import snapshot

    total_bytes = 35_000_000
    days = (0, 1, 2, 3, 4, 5, 7)
    used_bytes = (20_000_000, 21_100_000, 22_000_000, 23_300_000,
                  24_100_000, 25_400_000, 26_500_000)
    synthetic_root = "sanchay-synthetic-capacity-risk-fixture"
    records = [
        snapshot.capture(
            [], synthetic_root,
            filesystem_total_bytes=total_bytes,
            filesystem_used_bytes=used,
            filesystem_free_bytes=total_bytes - used,
            filesystem_device=42,
            now=100 + day * 86400)
        for day, used in zip(days, used_bytes)
    ]
    estimate = snapshot.capacity_risk(records, 7)
    if (not estimate["assessed"]
            or not 0 <= estimate["risk_probability"] <= 1):
        raise RuntimeError("Synthetic capacity-risk evidence did not assess safely")

    resized_records = [dict(record) for record in records]
    resized_records[-1]["filesystem_total_bytes"] += 4096
    resized_records[-1]["filesystem_free_bytes"] += 4096
    withheld = snapshot.capacity_risk(resized_records, 7)
    if (withheld["assessed"]
            or "capacity changed" not in withheld["reason"]):
        raise RuntimeError("A synthetic capacity resize did not withhold risk")

    return {
        "horizon_days": estimate["horizon_days"],
        "sample_count": estimate["sample_count"],
        "elapsed_seconds": estimate["elapsed_seconds"],
        "risk_probability": estimate["risk_probability"],
        "model": estimate["model"],
        "withheld_reason": withheld["reason"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="sanchay-demo",
        description="create a disposable SANCHAY demonstration fixture")
    parser.add_argument("root", nargs="?", help="empty directory for the fixture")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prove", action="store_true",
                      help="run the full safety rehearsal against the disposable fixture")
    mode.add_argument("--risk-prove", action="store_true",
                      help="rehearse capacity-risk gates with synthetic aggregate snapshots")
    args = parser.parse_args(argv)
    if args.risk_prove:
        if args.root:
            parser.error("--risk-prove does not accept a fixture root")
        result = rehearse_capacity_risk()
        print("risk telemetry -> synthetic aggregate mounted-filesystem snapshots; not endpoint data")
        print("risk evidence -> "
              f"{result['sample_count']} complete same-capacity snapshots over "
              f"{result['elapsed_seconds'] / 86400:.0f} days")
        print("risk estimate -> "
              f"{result['risk_probability'] * 100:.1f}% capacity-hit probability within "
              f"{result['horizon_days']} days under the local model")
        print("risk guard -> a synthetic capacity resize withheld the risk estimate")
        print("proof -> PASS; no endpoint file, alert, volume, or network was changed")
        return 0
    if args.prove:
        result = rehearse(args.root)
        print(f"rehearsal fixture -> {result['fixture']}")
        print(f"protected unique -> {result['protected_relative_path']} stayed out of the review plan")
        print("duplicate proof   -> "
              f"{result['duplicate_relative_path']} matched "
              f"{result['survivor_relative_path']} as a named evidence peer")
        print("retention boundary -> matching bytes do not identify the authoritative copy")
        print(f"hardlink boundary -> {result['excluded_hardlink_entries']} entries excluded")
        print(f"reclaim evidence  -> {result['selected_reclaim_bytes']:,} bytes selected for review")
        print("target optimizer -> lower-risk candidates first; exact minimum-excess "
              "subset used for the remaining target")
        print("fail-closed check -> a synthetic cache mutation invalidated the plan")
        print("proof -> PASS; no file was deleted, moved, or transmitted")
        return 0
    fixture = create(args.root)
    print(f"fixture -> {fixture}")
    print(f"scan    -> python -m sanchay.cli {fixture} --plan cleanup-plan.json --snapshot baseline.json")
    print("verify  -> python -m sanchay.cli --verify-plan cleanup-plan.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
