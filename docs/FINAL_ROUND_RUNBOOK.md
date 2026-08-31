# SANCHAY final-round runbook

## Confirmed slot from the organizer shortlist

- Team: Zeros and Ones
- Track: Track 2 — AI at Application Level
- Problem statement: AI-Powered Intelligent Storage Optimizer for Linux OS
- Order: Team 13
- Listed time: 14:15 on 4 September 2026

Reconfirm the time and venue in the latest organizer message before travelling
or joining the call.

## Timing: 15 minutes total

| Time | What to show | Evidence on screen |
| --- | --- | --- |
| 0:00–0:45 | The problem: size alone cannot establish recoverability. | One-slide problem framing. |
| 0:45–1:45 | The safety architecture: protected-file gate, duplicate survivor, review-only plan. | Architecture slide or CLI plan fields. |
| 1:45–4:45 | Live, deterministic fixture scan. | Terminal: candidate classes and unique-file exclusion. |
| 4:45–6:15 | Plan integrity checksum and verification pass. | JSON plan plus `--verify-plan` output. |
| 6:15–7:00 | Change only the synthetic fixture and show verification fail closed. | Non-zero verification result; no deletion action exists. |
| 7:00–10:00 | Forecast model, local-only boundary, and BOSS/C-DAC fit. | One concise slide and screenshot of the local dashboard. |
| 10:00–15:00 | Jury questions. | Keep terminal and plan open. |

Do not try to demonstrate cleanup. SANCHAY intentionally has no cleanup
executor; the winning argument is the evidence and control boundary before a
human acts.

## Pre-flight

1. Use a BOSS/Linux machine or a Linux VM with Python 3.9+ and Git available.
2. From the repository root, run `python -m pip install -e .`.
3. For the terminal dashboard only, run `python -m pip install -e ".[tui]"`.
4. Run `python -m unittest discover tests` and keep the passing output in the
   terminal scrollback.
5. Open the public page only as a seeded explanatory walkthrough. State that it
   does not scan the visitor's filesystem.

## Exact live-demo sequence

```bash
DEMO_ROOT="$(mktemp -d /tmp/sanchay-demo.XXXXXX)"
sanchay-demo "$DEMO_ROOT"

sanchay "$DEMO_ROOT" --target-reclaim 600K --limit 10 --plan cleanup-plan.json --snapshot baseline.json --explain
python -m json.tool cleanup-plan.json | less
sanchay --verify-plan cleanup-plan.json
```

Point out these concrete facts, not a generic dashboard:

- `documents/capstone-thesis.txt` is a deliberately unique fixture and is not
  in the plan.
- `downloads/boss-image-copy.iso` is a duplicate candidate only because
  `archive/boss-image.iso` is explicitly named as its retained survivor.
- `hardlinks/source.bin` and `hardlinks/alias.bin` are not reclaimable
  duplicates because they share one `(device, inode)` identity. They count as
  one physical file in the allocated on-disk total, forecast, snapshot, and
  treemap. Where Linux exposes block allocation, sparse-file logical length is
  also not treated as freeable storage.
- `workspace/node_modules/.cache/bundle.bin` is a reviewable regenerable-output
  candidate, not an automatically deleted file.
- `--explain` produces a deterministic local narrative and says no candidate
  data left the machine. Do not use `--cloud-narrative` in the final demo unless
  the team has separately approved it and configured an API key.
- The explicit `600K` reclaim request selects 712 KB of reviewable evidence;
  it does not broaden into the thesis or hardlinked entries to meet a target.
- `cleanup-plan.json` has a SHA-256 integrity checksum (not a signature),
  candidate identity including link count, typed recovery evidence, and a
  human-review requirement. Each recommendation also carries its frozen
  logical-size/allocated-reclaim/age/regret decision trace and computed
  priority.

## Fail-closed proof

Change only the disposable fixture, then recheck the original plan:

```bash
printf 'fixture changed\n' >> "$DEMO_ROOT/workspace/node_modules/.cache/bundle.bin"
sanchay --verify-plan cleanup-plan.json
```

Expected result: verification reports that the candidate identity changed and
exits non-zero. It does not delete, move, or alter any file. This is the most
important fail-closed evidence in the live demonstration.

## Concise jury answers

**Where is the AI?** The decision layer is intentionally explainable: a
recoverability model ranks eligible candidates and a local linear trend learns
bytes/day from aggregate snapshots. The default narration is local. A separate
cloud opt-in receives opaque candidate IDs plus class, allocated bytes, and
unchanged age—not raw paths or file contents—and cannot promote protected files
or execute actions.

**Why is the cloud narrative not automatic?** A storage scan can contain
sensitive path names, and file-derived text is untrusted input for an LLM. The
local narrative is default. `--cloud-narrative` requires separate consent and
transmits only opaque IDs and fixed numeric/class metadata; the decision gate,
plan, verification, and absence of a cleanup executor are enforced outside the
model.

**Why not automate deletion?** The requested problem includes recommendations;
the irreversible step has a different risk profile. SANCHAY supplies an
auditable plan and revalidation gate so an operator retains authority.

**What if an operator needs a stated amount of free space?** `--target-reclaim`
selects from the lowest recovery-risk class first, using the smallest safe
excess within that class, and reports whether the target is met. If it cannot
be met safely, it reports a shortfall rather than recommending protected files.
That capacity claim is deliberately limited to one filesystem. Explicit
cross-filesystem scans are inventory-only; they reject a shared reclaim target,
snapshot comparison, and runway forecast because freeing another mount does not
relieve the filesystem under pressure.

**What if `df` says full but the directory scan does not add up?** Linux can
keep an unlinked file allocated while a process still has it open. SANCHAY
checks visible `/proc/<pid>/fd` records on the scanned filesystem and reports
the PID, descriptor, and allocated bytes separately. This is an advisory, not a
cleanup recommendation: SANCHAY never kills, restarts, truncates, or deletes a
process-held file. Snapshots, reserved blocks, and other filesystem-specific
causes remain separate diagnostic questions.

**Why does SANCHAY show mount context?** C-DAC describes Secure BOSS as
LVM-encrypted, so filesystem-free bytes alone do not establish volume-group or
thin-pool headroom. SANCHAY reads Linux mount metadata and marks Btrfs,
container-overlay, and device-mapper boundaries as read-only advisory evidence.
It does not run `lvs`, resize a volume, balance Btrfs, or delete a snapshot.

**What if the scan cannot read part of the selected tree?** SANCHAY does not
pretend that an unprivileged walk is complete. It records count-only coverage
evidence, labels the result as readable-file inventory, and withholds mtime
forecast and snapshot/history claims. It still permits an operator to review
the evidence-backed candidates it actually saw; it never asks for elevated
access or records inaccessible path names in the plan.

**Why not remove a duplicate under `/usr` or `/etc`?** A content match only
proves matching bytes; it does not establish that a boot component,
configuration file, package-managed file, log, or service state is disposable.
SANCHAY fences those system-reserved paths before duplicate-content reads and
reports their allocated storage separately. More specific APT, journal,
container, and Flatpak policies retain their owning-tool review guidance.

**How do you prove a duplicate is eligible for review?** It uses size bucketing,
prefix hashing, then a full BLAKE2b-256 digest and a byte-for-byte comparison;
the plan names the survivor and verification rechecks both identities and
matching content. On Linux, each read is anchored to the selected root with
no-follow descriptor traversal; a symlink component or identity drift produces
no evidence rather than reading a substituted path. Hardlinks are not counted
as reclaimable copies.

**How reliable is the forecast?** A single scan is labelled as an mtime-based
estimate. Later aggregate snapshots produce a local linear trend with an
explicit slope and, from three observations onward, R-squared, rather than an
invented exact full-disk date.

**Why does this fit a sovereign secure OS?** The core is inspectable,
dependency-light, local by default, and stays on one filesystem unless the
operator explicitly opts into a multi-mount inventory. That inventory does not
make a shared capacity forecast or reclaim-target claim. Common credential paths
are excluded before metadata collection or hashing, and the same known-path gate
is reapplied if a caller supplies file records directly. No file content leaves
the machine through the core workflow. On Debian-derived BOSS, SANCHAY reports
APT archives and persistent journals as tool-owned operational storage. When
they exist, Docker, containerd, and Flatpak stores receive the same treatment;
SANCHAY also fences boot, configuration, package/cache, log, backup, and
service/spool paths before duplicate content reads. It does not convert any of
them into raw file-deletion candidates or target-reclaim bytes. If normal
endpoint policy makes part of the scan unreadable, it reports a count-only
coverage boundary and withholds growth and snapshot claims rather than implying
a whole-tree capacity result.

## What not to claim

- Do not call a first-scan forecast an exact date.
- Do not call the seeded web page a real device scan.
- Do not say SANCHAY deletes files, prevents every possible loss, or is legally
  certified for DPDP compliance.
- Do not say C-DAC has endorsed SANCHAY or that its tender defines hackathon
  scoring.
