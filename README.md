# SANCHAY

**Regret-aware storage intelligence for Linux.** Ranks cleanup candidates by what
it costs to be wrong, not by how big they are.

Built for C-DAC / MeitY *AI Enabled Operating System Hackathon 2026* —
Track: AI at Application Level — Problem Statement:
*AI-Powered Intelligent Storage Optimizer for Linux OS*.

---

## The idea

Every disk cleanup tool ranks by bytes freed. That is the wrong objective.
Freeing 2 GB of package cache and freeing 2 GB containing someone's only copy of
their thesis score identically — and only one of them is recoverable.

SANCHAY ranks by **regret** instead:

```
priority = bytes × staleness × (1 − regret)
```

Regret is estimated from **reproducibility**, not content:

| kind | meaning | regret |
|---|---|---|
| `disposable` | a build or package tool regenerates it | 0.02 |
| `duplicate` | an identical copy survives the delete | 0.10 |
| `tracked` | committed to a git repo | 0.20 |
| `unique` | nothing gets it back | **excluded entirely** |

A file that is unique, untracked and uncached is never recommended, however
large and however stale. That is the safety guarantee the problem statement asks
for, and it is enforced structurally rather than by asking a model to be careful.

## Forecasting without history

Predicting future storage normally needs a series of snapshots. It doesn't:
every file already records the day it was written, so the mtime distribution
*is* the history. One walk of the tree yields bytes-created-per-day, and that
projects forward against current free space.

## Where the model sits

Ranking is decided by the regret model from file metadata. The LLM only narrates
a list that already exists — so a hallucination cannot promote an irreplaceable
file into the recommendations. Explainability is earned by construction.

## Usage

```bash
python -m sanchay.cli ~/                 # scan and rank
python -m sanchay.cli ~/ --explain       # add narrative advice
```

Output:

```
48,213 files, 61.4GB

duplicates: 214 groups, 3.1GB reclaimable
growth:     91.2MB/day, full in 137 days
candidates: 20 safe, 9,847 irreplaceable files excluded
```

## Performance

Duplicate detection is size-bucketed, then head-hashed (64 KB), then fully
hashed — only for buckets that still collide. Hardlinks sharing an inode are not
counted as duplicates because they already share their bytes. Naive tools hash
every file; this reads a small fraction of the tree.

## Requirements

Python 3.9+, no mandatory third-party dependencies.
`ANTHROPIC_API_KEY` only for `--explain`.

## Third-party components

| Component | Licence | Use |
|---|---|---|
| anthropic | MIT | narration layer (optional) |

Scanner, duplicate detector, regret model and forecaster are original to this
project.

## Datasets

No external dataset. The tool operates on the user's own filesystem metadata
(paths, sizes, timestamps, inodes) and reads file contents only to confirm
duplicate candidates. Nothing is transmitted anywhere unless `--explain` is
passed, which sends only the ranked path list.

## Licence

MIT — see [LICENSE](LICENSE).
