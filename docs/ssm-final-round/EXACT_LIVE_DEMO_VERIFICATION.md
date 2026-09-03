# SANCHAY exact final-demo verification

Date: 1 September 2026 (IST)

This record covers one fresh, disposable Linux/WSL rehearsal of the visible
final-demo sequence. It is evidence for a local rehearsal only; it does not
claim a Secure BOSS deployment, a production forecast, a file deletion, or an
organizer acceptance.

## Frozen source and remote check

- Source repository: `C:\Users\basit\Downloads\CODE\sanchay`
- Local HEAD: `70b08e49583b7eb3ba2549672c71ab6f5c2f7db9`
- Worktree: clean before and after the rehearsal.
- Upstream and live `origin/master`: both
  `70b08e49583b7eb3ba2549672c71ab6f5c2f7db9`.
- Latest GitHub Actions run for that SHA: `SANCHAY CI` run `33443090956`,
  completed successfully on 31 August 2026.

No tracked source file, Git history, repository visibility, collaborator role,
or remote branch was changed for this rehearsal.

## Environment and sequence

- Linux environment: WSL Python 3.12.3.
- Fixture and evidence directories: newly created under Linux `/tmp`.
- Python bytecode writing: disabled for the source checkout.
- The sequence used `python3 -m sanchay.demo`, `python3 -m sanchay.cli`, and
  `python3 -m json.tool` from the checked-out source.

The run created a deterministic fixture, then performed these checks:

1. `--verify-archive` accepted the fixture's byte-identical separate inode and
   explicitly reported that it is not an independent backup.
2. A `600K` target-reclaim review plan selected `712.0KB`: `200.0KB`
   regenerable cache first, then `512.0KB` of byte-confirmed alternate-copy
   evidence using the exact minimum-excess subset.
3. The generated snapshot passed its integrity checksum check, and the plan
   parsed as valid JSON.
4. `--verify-plan` passed before the fixture was changed.
5. After appending only to the synthetic cache file, `--verify-plan` rejected
   the plan because the candidate size changed and returned exit `1` as
   intended.
6. `python3 -m sanchay.demo --prove` passed the protected-unique, duplicate,
   hardlink, target-optimizer, and fail-closed checks.
7. `python3 -m sanchay.demo --risk-prove` stated that its data are synthetic
   aggregate mounted-filesystem snapshots, produced a local-model `1.8%`
   seven-day estimate for the qualifying synthetic history, then withheld the
   estimate after a synthetic capacity resize.

Terminal completion marker: `FINAL_RUNBOOK_SEQUENCE=PASS`.

## Run-day preflight verification

After adding the non-mutating platform and submitted-checkout guard, the team
preflight was executed once on 1 September 2026:

```bash
bash SSM_LINUX_PREFLIGHT.sh /mnt/c/Users/basit/Downloads/CODE/sanchay
```

- Platform detected: Ubuntu 24.04.1 LTS on WSL2; Python 3.12.3.
- Source detected: commit `70b08e4`, no tracked content changes. The guard
  normalizes CRLF-only representation differences when a Windows checkout is
  rehearsed through WSL; it still rejects staged or substantive tracked source
  changes.
- Unit/integration suite: 110 tests passed, 5 optional tests skipped.
- Both `sanchay.demo --prove` and `sanchay.demo --risk-prove` completed with
  `PASS` using only disposable synthetic data.
- A separate temporary clone with one deliberate tracked `README.md` change was
  rejected with exit code `2` before the suite or demo could run. The clone was
  removed immediately after the guard test.
- The optional `SANCHAY_EXPECTED_COMMIT` pin accepted the current local SHA and
  rejected an unavailable SHA before any test or demo command. This verifies
  the mechanism only; the current SHA is **not** asserted to be the Stage 1
  submission until the team inspects the portal record or receives written
  organizer confirmation.

This strengthens the rehearsal procedure. It does not convert a WSL rehearsal
into proof of an independent Linux desktop or a Secure BOSS deployment.

## Exact target-optimizer boundary check

The separate read-only verifier `SSM_EXACT_OPTIMIZER_BOUNDARY.py` was run from
the current SANCHAY checkout on 1 September 2026. It constructs 28 in-memory
regenerable-cache records--the documented exact-selection limit--and writes no
endpoint data.

- Target: 704,009 bytes.
- Selected: 704,099 bytes.
- Strategy: `exact_minimum_excess_subset`.
- Measured local runtime: 0.015311 seconds on Ubuntu/WSL.

This validates that the current implementation takes the documented
meet-in-the-middle exact path at its boundary. It is one synthetic local timing
check, not a performance guarantee for all filesystems, workloads, or hardware.

## Large-candidate fallback boundary check

The separate read-only verifier `SSM_OPTIMIZER_SCALABILITY_PROOF.py` was run
from the same current SANCHAY checkout on 1 September 2026. It constructs 29
in-memory regenerable-cache records--one more than the exact-search limit--then
rebuilds the same target after reversing equivalent input order. It writes no
endpoint data.

- Target: 716,920 bytes.
- Selected: 719,724 bytes.
- Strategy: `greedy_fallback_above_exact_limit`.
- Equivalent reversed input order: identical recommendation paths and selected
  byte total (`PASS`).
- Measured local runtime for the first build: 0.001629 seconds on Ubuntu/WSL.

This proves the implementation records and uses its bounded deterministic
fallback instead of silently attempting an unbounded exact search. It does
**not** claim globally minimum excess, general endpoint performance, or a
production scalability benchmark above that boundary.

## Boundaries retained in the demonstration

- The plan is review-only; no file was copied, moved, deleted, transmitted, or
  executed by SANCHAY.
- The archive check proves a retained byte-identical separate inode on the
  fixture filesystem, not destination durability or backup policy.
- The risk demonstration is a transparent synthetic gate check, not endpoint
  telemetry or a live capacity prediction.
- Use a Secure BOSS/Linux system or Linux VM for the actual presentation. This
  WSL result is a rehearsal check, not a platform-certification claim.
