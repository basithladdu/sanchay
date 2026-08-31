<div align="center">

# SANCHAY: Regret-Aware Intelligent Storage Optimizer for Linux

**AI-Assisted Storage Reclamation with Review-Only Cleanup Plans & Mtime-Based Runway Estimates**

[![CI Status](https://github.com/basithladdu/sanchay/actions/workflows/ci.yml/badge.svg)](https://github.com/basithladdu/sanchay/actions)
[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Vercel Deployment](https://img.shields.io/badge/Vercel-Live%20Demo-black?logo=vercel)](https://sanchay-swart.vercel.app)

---

### Built for C-DAC / MeitY SSM Hackathon 2026
**Track 2: AI at Application Level • AI-Powered Intelligent Storage Optimizer for Linux OS**

*Developed by Team: Shaik Abdul Basith, Shaik Awaiz, Shaik Abdul Muqeeth*

---

</div>

## 📌 Executive Summary & Problem Context

Disk-usage explorers and duplicate finders can identify space consumers, but a
space ranking alone does not establish that a specific file is eligible for
human review.

To a naive tool, a 2 GB regenerable build cache (`node_modules/.cache`) and a 2 GB irreplaceable capstone project database dump look identical. When a user runs out of disk space, automated cleaners or hurried users delete unique personal files, causing catastrophic, irrecoverable data loss.

**SANCHAY** (संचय) introduces **Regret-Aware Storage Intelligence**. It models the *cost of recovery* for every candidate file before calculating cleanup priority:
**Priority = reclaimable allocated bytes × unchanged-age × (1 − regret)**

For irreplaceable unique files, regret is 1.00, so priority is 0.0 and they are excluded from SANCHAY's **review-only recommendation plan**.

---

## 🏛️ 4-Tier Recoverability Classification Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       RECOVERABILITY SPECTRUM                               │
├─────────────────┬───────────────────┬───────────────────┬───────────────────┤
│   DISPOSABLE    │    DUPLICATE      │    GIT TRACKED    │     UNIQUE        │
│   Regret: 0.02  │    Regret: 0.10   │    Regret: 0.20   │   Regret: 1.00    │
│  e.g. .cache,   │   Identical hash, │  Committed in git │ Capstone thesis,  │
│  __pycache__,   │   surviving copies│  history, restore │ production DB,    │
│  target/debug,  │   on filesystem   │  via git checkout │ personal docs     │
│  .next/cache    │                   │                   │                   │
├─────────────────┼───────────────────┼───────────────────┼───────────────────┤
│  REVIEW FIRST   │  REVIEW FIRST     │  REVIEW FIRST     │ EXCLUDED FROM PLAN│
│  Owning tool    │  Named survivor   │  Clean Git HEAD   │ No recommendation │
└─────────────────┴───────────────────┴───────────────────┴───────────────────┘
```

---

## 🔬 Core Innovations

### 1. Protected-File Gate and Review-Only Plans
Traditional systems ask the user to untick critical files from a massive list.
SANCHAY excludes files classified as unique, untracked, and uncached before
ranking, then writes a JSON plan with typed recovery evidence for every
remaining candidate. Its SHA-256 integrity checksum detects accidental plan
changes; it is not a digital signature. SANCHAY never deletes or moves files
itself.

### 2. Two-Stage Runway Measurement
SANCHAY derives an initial storage-growth estimate from the **inode modification time distribution (`mtime`) on run #1**. It is directional, not a guaranteed exhaustion date. A later aggregate local snapshot measures actual net growth; with multiple snapshots, an explainable local linear trend reports bytes/day, and with three or more snapshots it also reports fit quality. Usage, snapshots, forecasts, and treemaps count each physical `(device, inode)` once, and use allocated blocks (`st_blocks × 512`) where the filesystem exposes them, so neither hardlink aliases nor sparse logical length inflate the result.

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
When an operator needs a specific amount of space, `--target-reclaim 5G` selects
from the lowest recovery-risk class first, using the smallest safe excess within
that class. If the recovery-evidence gate cannot meet the target, SANCHAY
reports the shortfall instead of widening scope to protected files.

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

### 8. Mount-Aware Capacity Boundaries

Secure BOSS is deployed on an LVM-encrypted disk, while Linux installations
may also use Btrfs snapshots or container overlay layers. SANCHAY reads the
selected root's visible `/proc/self/mountinfo` record and records the filesystem
context in its plan. Btrfs, overlay, and device-mapper mounts receive a
read-only caveat explaining why a directory scan is not proof of host-wide,
thin-pool, or snapshot-aware free space. It never runs LVM/Btrfs commands,
resizes a volume, balances a filesystem, or deletes a snapshot.

---

## 🖥️ Terminal & Web Visualizations

### Rich Terminal Dashboard (`sanchay-ui`)

Install the optional Textual extra, then run `sanchay-ui /path/to/scan` for an
interactive view of reviewable candidates. The dashboard follows the same
review-only policy as the CLI.

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

# 4. Recheck that a plan is still valid before any human acts on it
sanchay --verify-plan cleanup-plan.json

# 5. Verify an operator-selected retained archive copy before treating it as a survivor
sanchay --verify-archive /home/user/downloads/ubuntu.iso /mnt/archive/ubuntu.iso

# 6. Save an aggregate local snapshot for a later measured-growth comparison
# This requires complete readable-path coverage; SANCHAY reports and withholds
# the snapshot if an in-scope path cannot be inspected.
sanchay /home/user --snapshot before.json
sanchay /home/user --compare before.json

# 7. Fit a local trend once you have multiple earlier snapshots
sanchay /home/user --history day-1.json day-7.json day-14.json

# 8. Generate an interactive Plotly HTML report
sanchay /home/user --report report.html

# 9. Produce a deterministic local-only narrative for the review set
sanchay /home/user --explain

# Explicit cloud narrative over opaque IDs and fixed metadata only
sanchay /home/user --explain --cloud-narrative

# 10. Create a harmless, reproducible final-round demo fixture
sanchay-demo /tmp/sanchay-demo

# 11. Launch interactive Textual Terminal Dashboard
sanchay-ui /home/user
```

---

## 🚀 Quickstart & Installation

```bash
# Clone the repository
git clone https://github.com/basithladdu/sanchay.git
cd sanchay

# Install the dependency-free core in editable mode
pip install -e .

# Optional: install the interactive terminal dashboard
pip install -e ".[tui]"

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
  raw paths or file contents.
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

---

## 👥 Authors & Team Credits

* **Shaik Abdul Basith**
* **Shaik Awaiz**
* **Shaik Abdul Muqeeth**

*Developed for the C-DAC / MeitY AI Enabled Operating System Hackathon 2026.*
