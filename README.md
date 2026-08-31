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
**Priority = size × unchanged-age × (1 − regret)**

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
SANCHAY derives an initial storage-growth estimate from the **inode modification time distribution (`mtime`) on run #1**. It is directional, not a guaranteed exhaustion date. A later aggregate local snapshot measures actual net growth; with multiple snapshots, an explainable local linear trend reports bytes/day, and with three or more snapshots it also reports fit quality. Usage, snapshots, forecasts, and treemaps count each physical `(device, inode)` once, so a hardlink alias cannot inflate the result.

### 3. Tiered Fast Content Hashing
Deduplicating large files can saturate I/O. SANCHAY uses a 3-tier cascade:
1. File size grouping (avoids hashing files whose sizes do not collide)
2. 64 KB header checksum (BLAKE2b-256)
3. Full BLAKE2b-256 digest only for confirmed header collisions
4. Byte-for-byte confirmation before a duplicate enters the review plan

### 4. Interactive Treemap & TUI Reporting
Interactive visualization color-coded by recoverability class rather than raw directory hierarchy alone.

---

### 5. Intent-Aware, Evidence-Bounded Reclamation
When an operator needs a specific amount of space, `--target-reclaim 5G` selects
only enough already-eligible candidates in deterministic priority order to meet
that target. If the recovery-evidence gate cannot meet it, SANCHAY reports the
shortfall instead of widening scope to protected files.

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

# 4. Recheck that a plan is still valid before any human acts on it
sanchay --verify-plan cleanup-plan.json

# 5. Save an aggregate local snapshot for a later measured-growth comparison
sanchay /home/user --snapshot before.json
sanchay /home/user --compare before.json

# 6. Fit a local trend once you have multiple earlier snapshots
sanchay /home/user --history day-1.json day-7.json day-14.json

# 7. Generate an interactive Plotly HTML report
sanchay /home/user --report report.html

# 8. Create a harmless, reproducible final-round demo fixture
sanchay-demo /tmp/sanchay-demo

# 9. Launch interactive Textual Terminal Dashboard
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

* **Local by default**: Analysis and duplicate hashing run on-device. No file content is transmitted; `--explain` is optional and may send ranked file paths to the configured model provider.
* **Inspectable evidence policy**: Every plan item records its classification,
  observed identity, and typed recovery evidence with its strength; files
  classified as unique are excluded before ranking.
* **Review gate**: `--verify-plan` rechecks the integrity checksum (not a
  digital signature), candidate identity including link count, duplicate
  survivor, and clean Git HEAD state where applicable. Hardlinked entries are
  never individual cleanup candidates because removing one name releases no
  physical bytes. It never deletes or moves files.

---

## 👥 Authors & Team Credits

* **Shaik Abdul Basith**
* **Shaik Awaiz**
* **Shaik Abdul Muqeeth**

*Developed for the C-DAC / MeitY AI Enabled Operating System Hackathon 2026.*
