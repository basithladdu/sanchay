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


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="sanchay-demo",
        description="create a disposable SANCHAY demonstration fixture")
    parser.add_argument("root", nargs="?", help="empty directory for the fixture")
    parser.add_argument("--prove", action="store_true",
                        help="run the full safety rehearsal against the disposable fixture")
    args = parser.parse_args(argv)
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
        print("fail-closed check -> a synthetic cache mutation invalidated the plan")
        print("proof -> PASS; no file was deleted, moved, or transmitted")
        return 0
    fixture = create(args.root)
    print(f"fixture -> {fixture}")
    print(f"scan    -> sanchay {fixture} --plan cleanup-plan.json --snapshot baseline.json")
    print("verify  -> sanchay --verify-plan cleanup-plan.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
