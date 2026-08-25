<div align="center">

# 🗄️ SANCHAY: Regret-Aware Intelligent Storage Optimizer for Linux

**AI-Powered Storage Reclamation with Structural Zero-Deletion Guarantees & Single-Scan Runway Forecasting**

[![CI Status](https://github.com/basithladdu/sanchay/actions/workflows/ci.yml/badge.svg)](https://github.com/basithladdu/sanchay/actions)
[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Vercel Deployment](https://img.shields.io/badge/Vercel-Live%20Demo-black?logo=vercel)](https://sanchay.vercel.app)
[![Privacy: DPDP Act 2023](https://img.shields.io/badge/Privacy-DPDP%20Act%202023%20Compliant-green.svg)](DECLARATION.md)

---

### 🏆 Built for C-DAC / MeitY AI Enabled Operating System Hackathon 2026
**Track 1: AI at Application Level • Problem Statement 2: AI-Powered Storage Optimization**

*Developed by Team: Shaik Abdul Basith, Shaik Awaiz, Shaik Abdul Muqeeth*

---

</div>

## 📌 Executive Summary & Problem Context

Every existing disk cleanup utility (`ncdu`, `bleachbit`, `baobab`) shares the exact same fatal flaw: **they rank files strictly by size**.

To a naive tool, a 2 GB regenerable build cache (`node_modules/.cache`) and a 2 GB irreplaceable capstone project database dump look identical. When a user runs out of disk space, automated cleaners or hurried users delete unique personal files, causing catastrophic, irrecoverable data loss.

**SANCHAY** (संचय) introduces **Regret-Aware Storage Intelligence**. It models the *cost of recovery* for every candidate file before calculating cleanup priority:
$$	ext{Priority} = 	ext{Size} 	imes 	ext{Staleness} 	imes (1 - 	ext{Regret})$$

For irreplaceable unique files, $	ext{Regret} = 1.00$, making $	ext{Priority} = 0.0$ and ensuring they are **permanently excluded from deletion by construction**.

---

## 🏛️ 4-Tier Recoverability Classification Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       RECOVERABILITY SPECTRUM                               │
├─────────────────┬───────────────────┬───────────────────┬───────────────────┤
│   DISPOSABLE    │    DUPLICATE      │    GIT TRACKED    │     UNIQUE        │
│   Regret: 0.02  │    Regret: 0.10   │    Regret: 0.20   │   Regret: 1.00    │
│  e.g. .cache,   │   Identical hash, │  Committed in git │ Capstone thesis,  │
│  node_modules,  │   surviving copies│  history, restore │ production DB,    │
│  __pycache__    │   on filesystem   │  via git checkout │ personal docs     │
├─────────────────┼───────────────────┼───────────────────┼───────────────────┤
│  PRIORITY: HIGH │  PRIORITY: HIGH   │  PRIORITY: MED    │ PRIORITY: ZERO    │
│  Safe to Purge  │  Safe Deduplicate │  Safe Offload     │ LOCKED 🔒 (NEVER) │
└─────────────────┴───────────────────┴───────────────────┴───────────────────┘
```

---

## 🔬 Core Innovations

### 1. Zero-Deletion Guarantee by Construction
Traditional systems ask the user to untick critical files from a massive list. SANCHAY mathematically removes unique single-copy files from the candidate queue before presenting any reclaim options.

### 2. Single-Scan Runway Forecasting
Unlike daemons that consume background CPU to log disk activity over weeks, SANCHAY derives the filesystem's daily consumption rate directly from the **inode modification time distribution (`mtime`) on run #1**. It projects the exact date of disk exhaustion with zero background overhead.

### 3. Tiered Fast Content Hashing
Deduplicating large files can saturate I/O. SANCHAY uses a 3-tier cascade:
1. File size grouping (eliminates 90% of non-duplicates instantly)
2. 64 KB header checksum (Blake2b)
3. Full content hash only for confirmed header collisions

### 4. Interactive Treemap & TUI Reporting
Interactive visualization color-coded by recoverability class rather than raw directory hierarchy alone.

---

## 🖥️ Terminal & Web Visualizations

### Rich Terminal Dashboard (`sanchay-ui`)
![SANCHAY Terminal UI](docs/tui.png)

### Commands & CLI Subcommands
```bash
# 1. Scan directory and display prioritized reclamation candidates
sanchay /home/user --limit 10

# 2. Run single-scan runway forecasting
sanchay /home/user --runway

# 3. Generate interactive Plotly HTML report
sanchay /home/user --html report.html

# 4. Launch interactive Textual Terminal Dashboard
sanchay-ui /home/user
```

---

## 🚀 Quickstart & Installation

```bash
# Clone the repository
git clone https://github.com/basithladdu/sanchay.git
cd sanchay

# Install in editable mode
pip install -e .

# Run unit and integration tests (5/5 tests passing)
python -m unittest discover tests

# Launch interactive UI
sanchay-ui .
```

---

## 🔒 Compliance & DPDP Act 2023 Declaration

* **DPDP Act 2023 Compliant**: 100% on-device processing. No personal identifiers or file contents are transmitted.
* **Deterministic Safety**: All regret classifications are transparent and verifiable.

---

## 👥 Authors & Team Credits

* **Shaik Abdul Basith**
* **Shaik Awaiz**
* **Shaik Abdul Muqeeth**

*Developed for the C-DAC / MeitY AI Enabled Operating System Hackathon 2026.*
