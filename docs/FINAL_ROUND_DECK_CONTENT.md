# Final-round slide content — replace the pre-selection draft

docs/SANCHAY.pptx is a pre-selection draft and must not be used unchanged.
It contains incorrect Track 1, guarantee, exact-forecast, legal-compliance, and
test-coverage claims. Preserve it as history; transfer the content below into
the organizer's PPT template when it arrives.

## Slide 1 — SANCHAY

**Evidence-led storage recommendations for Linux**

- Team Zeros and Ones
- Track 2 — AI at Application Level
- AI-Powered Intelligent Storage Optimizer for Linux OS

Footer: “Recommendations only. No automatic deletion or file movement.”

## Slide 2 — The real problem is recoverability, not size

Two files can be the same size and have radically different consequences:

- a regenerable build cache;
- the only copy of a thesis, database export, or document.

Most disk views can show what is large. SANCHAY asks what evidence exists that
the file can be reconstructed, and preserves the human decision for anything
irreversible.

## Slide 3 — Protected-file gate before ranking

Use one simple left-to-right flow:

local scan → duplicate content match / clean-Git state / cache-path heuristic → protected-file gate
→ optional reclaim target → review-only plan → human review

Headline: “Unique, untracked, uncached files are excluded from the plan before
priority ranking.”

Each recommendation records the exact size, unchanged-age, regret weight, and
computed priority behind its decision; the model is inspectable rather than a
black box.

Call out that the default narrative is local. A separately opt-in cloud
narrative receives opaque candidate IDs plus class, allocated bytes, and age—no
raw paths or file contents—and cannot add a file, alter an order, or execute an
action.

## Slide 4 — Duplicate recommendations need a surviving source

Show the actual proof chain:

same size → same 64 KB prefix → same full BLAKE2b-256 digest → byte-for-byte
confirmation → named survivor → identity recheck

Three claims only:

- hardlinks share a (device, inode) identity, count once in allocated-byte
  metrics, and are not reclaimable copies; sparse logical length is not
  presented as reclaimable allocation where Linux exposes block counts;
- every duplicate recommendation names its retained survivor;
- `--verify-archive SOURCE RETAINED_COPY` rejects hardlink aliases, verifies
  matching bytes and a separate inode, then creates only recovery evidence—not
  a copy, move, or deletion; a same-filesystem result is never called a backup;
- revalidation rechecks both files and their matching contents; on Linux the
  reader is anchored to the selected root and rejects symlink-component swaps
  or identity drift instead of treating changed paths as evidence.

## Slide 5 — Honest capacity intelligence

Show two stages, not a fake exact date:

1. An initial mtime-based estimate gives immediate orientation.
2. Aggregate local snapshots fit an explainable linear trend that reports
   bytes/day and, from the third snapshot onward, R-squared fit quality.
3. If `/proc` shows a deleted regular file still held open, identify its PID and
   allocated bytes as a separate advisory, never as a cleanup recommendation.
4. Record the root mount context. Btrfs, overlay, and device-mapper sources
   change what a free-space figure proves; SANCHAY labels that boundary rather
   than invoking a filesystem or volume-management action.
5. If any in-scope path is unreadable, record only count-level coverage,
   label the output readable-file inventory, and withhold forecast/snapshot
   claims rather than treating a partial scan as complete.

Footer: “A first scan is an estimate; observed history is stronger evidence.”

## Slide 6 — Live proof, not an uncontrolled machine demo

Use the deterministic SANCHAY fixture and terminal output:

- a unique capstone-thesis.txt is absent from the plan;
- a duplicate has a named survivor;
- a hardlink is excluded from reclaimable duplicates and does not inflate the
  disk total;
- a process-held deleted file, when observed, is evidence for an operator to
  review a service lifecycle—not permission for SANCHAY to stop or alter it;
- `--explain` produces a local narrative and explicitly says that no candidate
  data left the machine;
- a 600 KB target is met only with reviewable evidence-backed candidates;
- a build cache is reviewable, not deleted;
- --verify-plan passes before change and fails closed after a synthetic fixture
  change.

Put the command in small monospace text only:

    sanchay-demo /tmp/sanchay-demo && sanchay /tmp/sanchay-demo --target-reclaim 600K --plan cleanup-plan.json && sanchay --verify-plan cleanup-plan.json

## Slide 7 — Fit for a secure, sovereign Linux workflow

- Local core workflow; no file contents transmitted. Known credential/control
  paths are excluded before metadata or content reads, and the same gate repeats
  in direct content and plan APIs.
- One filesystem by default. Explicit cross-filesystem traversal is inventory
  only: SANCHAY refuses a shared reclaim target or capacity forecast across mounts.
- On Debian-derived BOSS, APT archives and persistent journals are measured as
  tool-owned operational storage. When present, Docker, containerd, and Flatpak
  stores receive the same protection—never raw file-deletion candidates.
- Boot, configuration, package/cache, log, backup, and service/spool paths are
  fenced before duplicate-content reads. A content match under `/usr` or `/etc`
  is never treated as permission to remove an OS file.
- Access-denied paths are not hidden: SANCHAY reports count-only incomplete
  coverage and refuses to turn a partial scan into a capacity forecast or
  snapshot history.
- C-DAC describes Secure BOSS as LVM-encrypted. SANCHAY records a visible
  device-mapper boundary but does not infer pool headroom, encryption state, or
  permission to run LVM commands.
- Dependency-free Python core; TUI, plots, and the separately opt-in cloud
  narration are optional. The JSON manifest records observed identity and a
  SHA-256 integrity checksum (not a signature).

Phrase this as a product fit inferred from C-DAC's Secure OS context, not a
claim of C-DAC endorsement or scoring criteria.

## Slide 8 — Closing

**SANCHAY does not ask users to trust a cleanup model. It gives them evidence
to review before any irreversible action.**

Keep the final slide sparse: team name, repository, and one QR code only if it
has been independently tested from the presentation device.

## Source-note handoff for the final deck

- C-DAC BOSS/FOSS context: docs/FINAL_ROUND_RESEARCH.md.
- C-DAC Secure OS tender context: docs/FINAL_ROUND_RESEARCH.md; label as
  context, not hackathon rules.
- Storage redundancy and forecasting research: docs/FINAL_ROUND_RESEARCH.md.
- Implementation claims: sanchay/plan.py, sanchay/dedup.py,
  sanchay/managed.py, sanchay/snapshot.py, and the verified test suite.
