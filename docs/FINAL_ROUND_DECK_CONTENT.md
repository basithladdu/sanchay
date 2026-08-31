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
confirmation → named evidence peer → identity recheck

Three claims only:

- hardlinks share a (device, inode) identity, count once in allocated-byte
  metrics, and are not reclaimable copies; sparse logical length is not
  presented as reclaimable allocation where Linux exposes block counts;
- every duplicate recommendation names a deterministic evidence peer, but an
  operator chooses which copy to retain;
- `--verify-archive SOURCE RETAINED_COPY` rejects hardlink aliases, verifies
  matching bytes and a separate inode, then creates only recovery evidence—not
  a copy, move, or deletion; a same-filesystem result is never called a backup;
- revalidation rechecks both files and their matching contents; on Linux the
  reader is anchored to the selected root and rejects symlink-component swaps
  or identity drift instead of treating changed paths as evidence.

## Slide 5 — Honest capacity intelligence

Show two stages, not a fake exact date:

1. An initial readable-inventory mtime estimate gives immediate orientation.
2. Schema-5 local snapshots record mounted filesystem total, used, and free
   bytes separately from the readable inventory. The explainable trend uses the
   mounted-filesystem used-byte series, requires the same root/device, and
   waits for a 24-hour first-to-latest span before reporting bytes/day or
   R-squared from the third snapshot onward.
3. If `/proc` shows a deleted regular file still held open, identify its PID and
   allocated bytes as a separate advisory, never as a cleanup recommendation.
4. Record the root mount context. Btrfs, overlay, and device-mapper sources
   change what a free-space figure proves; SANCHAY labels that boundary rather
   than invoking a filesystem or volume-management action.
5. On an explicit `--capacity-audit`, compare filesystem-used blocks with a
   complete mount-root readable inventory plus visible deleted-open bytes. Call
   the result an accounting gap, not reclaimable or unexplained storage.
6. In the same explicit audit, distinguish free blocks from blocks available to
   the unprivileged operator, rather than guessing that every free byte is
   usable.
7. Show the mount's POSIX inode/file-entry counters (total, free, and
   unprivileged availability where reported), so `ENOSPC` with free byte space
   is surfaced without recommending a deletion.
8. If any in-scope path is unreadable, record only count-level coverage,
   label the output readable-file inventory, and withhold forecast/snapshot
   claims rather than treating a partial scan as complete.
9. Explicitly supplied SANCHAY snapshots, plans, reports, and briefs are
   excluded from the readable inventory if stored beneath the root; their bytes
   remain in the mount metric, but they cannot become self-referential cleanup
   candidates.
10. Count nested mount points below the selected root. In default
    one-filesystem mode, prune each visible child mount before traversal,
    including a same-device bind mount; older entries covered by a child mount
    may be absent from the readable inventory. Cross-filesystem inventory uses
    directory identity guards against recursive bind walks. SANCHAY calls this
    a topology boundary and never unmounts or remounts a path to inspect it.
11. Show a measured mounted-filesystem rate after 24 hours, but withhold a
    runway date until three snapshots expose an R² fit of at least 0.80. This
    is a conservative product gate, not a promise that the date is certain.
12. On an explicit `--risk-horizon DAYS`, report a local probability of
    reaching current mounted capacity within that horizon rather than a false
    exact date. The Brownian-motion-with-drift estimate is withheld unless
    there are seven complete same-root snapshots spanning seven days, each at
    least twelve hours apart, with unchanged mount capacity. It changes no
    file, volume, alert, or network state.

Footer: “A first scan is an inventory estimate; same-mount observed history is stronger evidence.”

## Slide 6 — Live proof, not an uncontrolled machine demo

Use the deterministic SANCHAY fixture and terminal output:

- a unique capstone-thesis.txt is absent from the plan;
- a duplicate has a named evidence peer, not an inferred source of truth;
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
- C-DAC also positions Secure BOSS for critical end nodes, ISOC-monitored
  clients, and intranet/standalone systems. SANCHAY fits that context through a
  local core and a path-free aggregate operator brief; it makes no ISOC API,
  deployment, or C-DAC-endorsement claim.
- Dependency-free Python core; TUI, plots, and the separately opt-in cloud
  narration are optional. The seeded browser explainer renders embedded offline
  summaries first, then uses Plotly only as an optional enhancement. The JSON
  manifest records observed identity and a SHA-256 integrity checksum (not a
  signature).
- For an ISOC or support handoff, `--operator-brief` emits aggregate counts and
  byte totals only. If a capacity-risk horizon was requested, it can also carry
  only the aggregate probability, horizon, sample evidence, and model metrics.
  It excludes roots, paths, file names, process IDs/names, mount/device
  sources, and file content; it does not transmit anything.

Phrase this as a product fit inferred from C-DAC's Secure OS context, not a
claim of C-DAC endorsement or scoring criteria.

## Slide 8 — Closing

**SANCHAY does not ask users to trust a cleanup model. It gives them evidence
to review before any irreversible action.**

Keep the final slide sparse: team name, repository, and one QR code only if it
has been independently tested from the presentation device.

## Source-note handoff for the final deck

- C-DAC BOSS/FOSS context: docs/FINAL_ROUND_RESEARCH.md.
- Secure BOSS capability-to-SANCHAY mapping: docs/CDAC_SECURE_BOSS_FIT.md.
- C-DAC Secure OS tender context: docs/FINAL_ROUND_RESEARCH.md; label as
  context, not hackathon rules.
- Storage redundancy and forecasting research: docs/FINAL_ROUND_RESEARCH.md.
- Implementation claims: sanchay/plan.py, sanchay/dedup.py,
  sanchay/managed.py, sanchay/snapshot.py, and the verified test suite.
