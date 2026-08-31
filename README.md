# SANCHAY

**Evidence-first storage decisions for Linux**

Team Zeros and Ones · C-DAC / MeitY SSM Hackathon 2026 · Track 2: AI at
Application Level · AI-Powered Intelligent Storage Optimizer for Linux OS

[Continuous integration](https://github.com/basithladdu/sanchay/actions)

SANCHAY is a local, review-only storage decision layer. It does not delete or
move files. Instead, it identifies candidates with explicit recovery evidence,
writes an integrity-checked review plan, and rechecks the plan before a human
performs any separate cleanup.

## Problem

Disk-usage explorers and duplicate finders can identify space consumers, but a
space ranking alone does not establish that a specific file is eligible for
human review.

To a naive tool, a 2 GB regenerable build cache (`node_modules/.cache`) and a 2 GB irreplaceable capstone project database dump look identical. When a user runs out of disk space, automated cleaners or hurried users delete unique personal files, causing catastrophic, irrecoverable data loss.

**SANCHAY** (संचय) introduces **Regret-Aware Storage Intelligence**. It models the *cost of recovery* for every candidate file before calculating cleanup priority:
**Priority = reclaimable allocated bytes × unchanged-age × (1 − regret)**

For irreplaceable unique files, regret is 1.00, so priority is 0.0 and they are excluded from SANCHAY's **review-only recommendation plan**.

---

## Recovery-evidence model

| Evidence class | Regret | Review boundary |
| --- | ---: | --- |
| Regenerable cache or build output | 0.02 | Review through its owning tool. |
| Byte-confirmed duplicate | 0.10 | A named evidence peer remains; a human selects retention. |
| Clean Git HEAD file | 0.20 | Confirm the project owner accepts removal. |
| Unique or otherwise unproven file | 1.00 | Excluded from the plan. |

SANCHAY uses allocated bytes where the platform exposes them. A hardlink is
not a reclaimable duplicate because removing one directory entry releases no
physical storage.

---

## Evidence model and safeguards

### 1. Protected-File Gate and Review-Only Plans
Traditional systems ask the user to untick critical files from a massive list.
SANCHAY excludes files classified as unique, untracked, and uncached before
ranking, then writes a JSON plan with typed recovery evidence for every
remaining candidate. Its SHA-256 integrity checksum detects accidental plan
changes; it is not a digital signature. SANCHAY never deletes or moves files
itself.

For a duplicate, SANCHAY names a deterministic byte-matched **evidence peer**
so the relation can be independently rechecked. Matching bytes do not identify
the authoritative copy or prove a backup, so the plan explicitly requires an
operator to choose which copy to retain before any manual removal.

### 2. Two-Stage Runway Measurement
SANCHAY derives an initial storage-growth estimate from the **readable-inventory inode modification-time distribution (`mtime`) on run #1**. It is directional, not a guaranteed exhaustion date. A later local snapshot records the selected mounted filesystem's total, used, and free bytes separately from the readable inventory. Comparisons and local linear trends use only the mounted-filesystem used-byte series; they require complete readable coverage, the same resolved root and filesystem device, and at least a 24-hour first-to-latest observation span. The gate prevents seconds of ordinary background activity from becoming a fictional runway. With three or more snapshots, SANCHAY also reports fit quality. The readable inventory, review plan, and treemap count each physical `(device, inode)` once and use allocated blocks (`st_blocks × 512`) where the filesystem exposes them, so hardlink aliases and sparse logical length do not inflate those diagnostic totals. Schema 6 adds a SHA-256 checksum over each aggregate snapshot; it detects a mismatch against stored aggregate content, but is not a digital signature or device attestation. Earlier inventory-only or unsealed snapshot files are rejected: recapture a fresh baseline rather than mixing metrics.

A mounted-filesystem capacity resize also withholds a runway date. An LVM
provisioning event changes what a historical free-space runway means, even if
the selected path and device remain the same.

#### Runway Projection Gate

A two-snapshot rate is useful evidence of observed filesystem use, but it
cannot expose variation: any two points form a perfect line. SANCHAY therefore
keeps the measured rate visible while withholding a `full in` date until there
are at least three same-root snapshots, a 24-hour first-to-latest span, and an
R² fit of at least 0.80. This is a conservative product gate, not a guarantee
that future storage consumption will remain linear.

#### Capacity-Risk Gate

`--risk-horizon DAYS` adds a separate local capacity-hit probability, rather
than pretending that every workload deserves one exact full-disk date. It uses
a Brownian-motion-with-drift hitting-time model over aggregate mounted-filesystem
used-byte changes and is deliberately stricter than the runway slope: at least
seven complete same-root snapshots spanning seven days, every interval at least
twelve hours, and unchanged mounted filesystem capacity. Otherwise SANCHAY
prints an explicit withheld reason. The probability is conditional on that
local-history model, not a capacity guarantee, root-cause diagnosis, cleanup
instruction, alert, or network call.

### Capacity Boundary Across Mounts

SANCHAY scans one filesystem by default. `--cross-filesystems` is an explicit
multi-mount **inventory** mode: it may show candidates across mounted filesystems,
but it deliberately refuses `--target-reclaim`, snapshots, comparisons, and
history-based forecasts. A byte released on another mount does not create free
space on the filesystem under pressure, so SANCHAY makes no combined capacity or
runway claim. The review plan records this as
`scan_scope: cross_filesystem_inventory` with the same capacity boundary.

### Scan-Coverage Boundary

A secure endpoint can correctly deny an ordinary user access to part of a tree.
SANCHAY records only counts of unreadable directories and files; it does not put
their paths into a plan, snapshot, or shareable report. If any in-scope path
cannot be inspected, the output is explicitly labelled a readable-file
inventory. Candidate evidence remains limited to files actually seen, while
mtime forecasts, comparable snapshots, and trend claims are withheld rather
than treating a partial tree as complete.

### Path-Free Operator Brief

The detailed plan and HTML report are local review artifacts and can contain
relative paths or process context. `--operator-brief OUT.json` produces a
separate aggregate handoff for a secure endpoint or operations review: evidence
class counts, allocated-byte totals, managed-store totals, coverage, mount
source class, deleted-open aggregate, and the capacity-accounting boundary. If
a capacity-risk horizon was explicitly requested and assessed, it adds only the
aggregate probability, horizon, sample evidence, and model metrics. It
intentionally contains no root, paths, file names, process IDs, process names,
mount points, device sources, free-form model rationale, or file content, and
it performs no network transfer. Its SHA-256 checksum detects accidental
changes; it is not a signature, incident log, remediation instruction, or
external submission.

### 3. Tiered Fast Content Hashing
Deduplicating large files can saturate I/O. SANCHAY uses a 3-tier cascade:
1. File size grouping (avoids hashing files whose sizes do not collide)
2. 64 KB header checksum (BLAKE2b-256)
3. Full BLAKE2b-256 digest only for confirmed header collisions
4. Byte-for-byte confirmation before a duplicate enters the review plan
5. On Linux, content is opened descriptor-by-descriptor from the canonical
   scan root with no-follow flags. A symlink component, non-regular file, or
   scan-time identity change yields no duplicate evidence.

### Verified Archive-Copy Gate

`sanchay --verify-archive SOURCE RETAINED_COPY` is a separate, read-only proof
step for an operator-chosen archive destination. It requires two regular,
non-sensitive, non-system-managed files, rejects a hardlink alias as a fake
copy, compares the bytes, and rechecks both identities before reporting a
retained survivor. It never creates, moves, or deletes either file. A verified
copy on the same filesystem can support a manual space-recovery review, but is
explicitly not presented as an independent backup, retention policy, or restore
procedure.

### 4. Interactive Treemap & TUI Reporting
Interactive visualization color-coded by recoverability class rather than raw directory hierarchy alone.

---

### 5. Intent-Aware, Evidence-Bounded Reclamation
When an operator needs a specific amount of space, `--target-reclaim 5G` first
exhausts lower recovery-risk classes. Where one class can meet the remaining
request with 28 or fewer candidates, a bounded exact subset search minimizes
safe excess; a larger class uses a recorded deterministic greedy fallback. If
the recovery-evidence gate cannot meet the target, SANCHAY reports the shortfall
instead of widening scope to protected files.

---

### 6. BOSS-Aware Managed Storage, Not Raw File Cleanup

BOSS is Debian-derived. SANCHAY therefore measures APT archives under
`/var/cache/apt/archives/` and persistent systemd journals under
`/var/log/journal/` separately. If present, it also fences Docker Engine,
containerd, and Flatpak system storage under `/var/lib/`. These paths are
**never** included in a file-level reclaim target or suggested for raw deletion.
It also fences generic system-reserved paths such as `/boot`, `/etc`, `/usr`,
package databases and caches, standard logs, backups, and spool state before
any duplicate-content read. A byte-for-byte match does not establish that an OS
file is disposable. Specific APT, journal, and runtime policies take precedence
over the generic boundary so the report retains the most useful approved review
route.
Instead, the plan shows allocated storage and the owning-tool review route:
`apt-get autoclean` or an approved `apt-get clean` policy; `journalctl
--disk-usage` plus an approved journal-retention decision; `docker system df
-v` before any explicit Docker pruning decision; or `flatpak list` before a
review of unused runtimes. A human retains control over every action.

---

### 7. Linux Process-Held Deleted Storage

A directory scan cannot see a file after its directory entry has been removed,
even when its blocks remain allocated because a Linux process still holds an
open descriptor. SANCHAY inspects visible `/proc/<pid>/fd` entries on the
scanned filesystem and reports these records as a separate operational
advisory. They never enter a reclaim target or cleanup plan: SANCHAY does not
signal, restart, truncate, or delete anything held by a process.

---

### 8. Mount-Root Accounting Gap Diagnostic

`--capacity-audit` is an explicit diagnostic for a complete scan started at the
root of one mounted filesystem. It compares reported filesystem-used blocks
with the readable allocated-file inventory plus visible deleted-open files and
labels the signed remainder an **accounting gap**. It also reads the mounted
filesystem's POSIX `statvfs` block and file-entry/inode counters. It separates
free blocks from blocks available to an unprivileged process, then reports
total, free, and, when reported, available file entries. That catches both the
filesystem-policy boundary where an ordinary user cannot consume all free
blocks and the separate failure mode where Linux cannot create a file despite
free byte space. Neither signal is called reclaimable or unexplained space: protected paths,
filesystem metadata, Btrfs snapshots or shared extents, mount-overlaid data,
and inaccessible state can all contribute. The audit identifies no file to
remove and never runs a filesystem, volume, container, or cleanup command.

---

### 9. Mount-Aware Capacity Boundaries

Secure BOSS is deployed on an LVM-encrypted disk, while Linux installations
may also use Btrfs snapshots or container overlay layers. SANCHAY reads the
selected root's visible `/proc/self/mountinfo` record and records the filesystem
context in its plan. Btrfs, overlay, and device-mapper mounts receive a
read-only caveat explaining why a directory scan is not proof of host-wide,
thin-pool, or snapshot-aware free space. It never runs LVM/Btrfs commands,
resizes a volume, balances a filesystem, or deletes a snapshot.

When a selected root contains visible child mounts, the default one-filesystem
scan prunes them **before** traversal, including same-device bind mounts that
would evade a simple device-number filter. Explicit cross-filesystem inventory
still follows them, but tracks directory device/inode identities so a recursive
bind view is not walked twice. SANCHAY never mounts, unmounts, or remounts a
path to inspect it.

---

## Terminal and browser views

### Rich Terminal Dashboard (`sanchay-ui`)

Install the optional Textual extra, then run `sanchay-ui /path/to/scan` for an
interactive view of reviewable candidates. The dashboard follows the same
review-only policy as the CLI.

### Seeded Browser Explainer

`index.html` (mirrored in `public/index.html`) is a seeded explanatory page,
not a device scan. Its embedded SVG chart summaries render immediately without
a public chart CDN; Plotly is only an optional asynchronous enhancement. Add
`?offline=1` during rehearsal to force the no-CDN state. No visitor filesystem
data is read or transmitted.

### Commands & CLI Subcommands
```bash
# 1. Scan directory and display prioritized reclamation candidates
sanchay /home/user --limit 10

# 2. Write an integrity-checked, review-only cleanup plan
sanchay /home/user --plan cleanup-plan.json

# 3. Ask for enough evidence-backed candidates to reclaim a stated amount
sanchay /home/user --target-reclaim 5G --plan cleanup-plan.json

# Cross mounted filesystems only for inventory; capacity plans stay per filesystem
sanchay /srv --cross-filesystems --plan multi-mount-review.json

# Audit a complete scan only when the selected directory is exactly a mount root
sanchay /mnt/data --capacity-audit

# 4. Recheck that a plan is still valid before any human acts on it
sanchay --verify-plan cleanup-plan.json

# 5. Verify an operator-selected retained archive copy before treating it as a survivor
sanchay --verify-archive /home/user/downloads/ubuntu.iso /mnt/archive/ubuntu.iso

# 6. Save a mount-scoped local snapshot for a later measured-growth comparison.
# It records mounted total/used/free bytes plus a separate readable-inventory
# aggregate. Complete readable-path coverage and a 24-hour comparison span are required.
# Snapshot files are write-once evidence artifacts: use a distinct name for each capture.
sanchay /home/user --snapshot before.json
sanchay --verify-snapshot before.json
sanchay /home/user --compare before.json

# 7. Fit a mounted-filesystem trend once you have multiple earlier snapshots
sanchay /home/user --history day-1.json day-7.json day-14.json

# Or keep the complete local evidence series in one explicit directory. Each
# invocation loads only checksum-matching SANCHAY records and appends a new write-once
# timestamped aggregate snapshot; it never installs a scheduler or sends data.
sanchay /home/user --snapshot-history ~/.local/state/sanchay/home

# Optional: estimate local capacity-hit risk only from strong same-mount history.
# The result is a probability under the local model, not a cleanup instruction.
sanchay /home/user --history day-1.json day-2.json day-3.json day-4.json day-5.json day-6.json day-7.json --risk-horizon 30
sanchay /home/user --snapshot-history ~/.local/state/sanchay/home --risk-horizon 30

# 8. Generate an interactive Plotly HTML report (requires .[viz])
sanchay /home/user --report report.html

# 9. Write a path-free aggregate operator handoff; no network transfer
sanchay /home/user --operator-brief operator-brief.json

# 10. Recheck that the brief has not changed; it never touches endpoint files
sanchay --verify-operator-brief operator-brief.json

# 11. Produce a deterministic local-only narrative for the review set
sanchay /home/user --explain

# Explicit cloud narrative over opaque IDs and fixed metadata only
sanchay /home/user --explain --cloud-narrative

# Optional loopback Ollama narrative over the same opaque metadata only.
# Requires an already-running local Ollama service and an operator-provisioned model.
sanchay /home/user --explain --ollama-narrative --ollama-model gemma3

# 12. Create a harmless, reproducible final-round demo fixture
sanchay-demo /tmp/sanchay-demo

# 13. Run the complete safety rehearsal against a disposable fixture
# It proves the protected, duplicate, hardlink, and fail-closed boundaries.
sanchay-demo --prove

# 14. Rehearse capacity-risk gating from synthetic aggregate snapshots only.
# This proves code gating, never a live endpoint forecast.
sanchay-demo --risk-prove

# 15. Launch interactive Textual Terminal Dashboard
sanchay-ui /home/user
```

If an explicitly supplied snapshot, plan, report, or operator brief lives under
the selected root, SANCHAY excludes that artifact from the readable inventory
and review plan. It does **not** subtract it from the mounted-filesystem usage:
the physical bytes still exist, but SANCHAY must not recommend its own state for
review.

---

## Quickstart

```bash
# Clone the repository
git clone https://github.com/basithladdu/sanchay.git
cd sanchay

# Install the dependency-free core in editable mode
pip install -e .

# Optional: install the interactive terminal dashboard
pip install -e ".[tui]"

# Optional: install self-contained HTML visualization support
pip install -e ".[viz]"

# Run the unit and integration tests
python -m unittest discover tests

# Launch interactive UI
sanchay-ui .
```

---

## Privacy and safety boundaries

* **Local by default**: Analysis, duplicate hashing, and `--explain` narration
  run on-device. No file content or candidate data is transmitted. An optional
  `--cloud-narrative` requires explicit user opt-in and sends only opaque
  candidate IDs, recoverability class, allocated bytes, and unchanged age—never
  raw paths or file contents. `--ollama-narrative` uses the same opaque
  metadata with a fixed `127.0.0.1:11434` loopback endpoint, no proxy, and no
  redirects; SANCHAY makes no direct remote request. The selected local-model
  runtime and its provisioning remain operator policy, and neither model can
  alter the plan or execute a cleanup action.
* **Credential boundary**: Common credential directories, environment files,
  private-key formats, local credential vaults, Docker configuration, and npm
  and Terraform CLI credential files are excluded before metadata collection or
  duplicate hashing. The same known credential/control-path gate is reapplied
  by the content-evidence and plan APIs, so caller-supplied `FileInfo` records
  cannot bypass it.
* **Content-read boundary**: Duplicate evidence is tied to the inode observed
  during the scan. Linux reads are rooted at the canonical scan directory and
  reject symlink components; all platforms reject non-regular files and
  descriptor identity drift before using content as evidence.
* **System-tool boundary**: APT archive, persistent journal, Docker,
  containerd, Flatpak, and generic system-reserved OS paths are reported as
  managed operational storage, not raw file cleanup candidates, duplicate-read
  inputs, or target-reclaim bytes.
* **Scan-coverage boundary**: Unreadable in-scope paths are counted without
  recording their names. An incomplete traversal is labelled readable-file
  inventory only; SANCHAY withholds its mtime forecast and snapshots rather
  than claiming a complete capacity view.
* **Operator-brief boundary**: `--operator-brief` emits only aggregate local
  review facts for a secure-operator handoff. A requested, assessed
  capacity-risk estimate contributes numeric model evidence only. The brief
  excludes roots, paths, file names, process IDs/names, mount/device sources,
  free-form model rationale, and file content; it does not transmit data or
  authorize a cleanup action.
* **Inspectable evidence policy**: Every plan item records its classification,
  logical and reclaimable allocated sizes, observed identity, typed recovery
  evidence with its strength, and frozen decision-model inputs; files
  classified as unique are excluded before ranking.
* **Review gate**: `--verify-plan` rechecks the integrity checksum (not a
  digital signature), candidate identity including link count, duplicate
  survivor, and clean Git HEAD state where applicable. Hardlinked entries are
  never individual cleanup candidates because removing one name releases no
  physical bytes. It never deletes or moves files.
* **Archive proof boundary**: `--verify-archive` verifies an explicitly chosen
  separate retained inode with a byte-for-byte comparison and identity recheck.
  It rejects credential/control and system-managed paths, performs no file
  action, and never represents a same-filesystem copy as an independent backup.
* **Capacity-audit boundary**: `--capacity-audit` works only for a complete
  single-filesystem scan begun at that mount's root. It reports a signed
  accounting gap after readable inventory and visible deleted-open storage,
  alongside usable POSIX block-availability and inode/file-entry capacity
  counters. It never treats any signal as a cleanup target or a complete explanation of
  filesystem use.

---

## Team

* **Shaik Abdul Basith**
* **Shaik Awaiz**
* **Shaik Abdul Muqeeth**

*Developed for the C-DAC / MeitY AI Enabled Operating System Hackathon 2026.*
