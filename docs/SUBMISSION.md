# SANCHAY — portal submission fields

Copy each block into the matching field on the SSM portal.

---

## Title

SANCHAY — Regret-Aware Storage Cleanup for Linux

---

## Problem Statement

AI-Powered Intelligent Storage Optimizer for Linux OS — Build an AI assistant
that analyzes file usage, identifies duplicate and unused files, and predicts
future storage needs. The solution should provide intelligent cleanup and
archiving recommendations to help users manage storage efficiently.

---

## Objective

To make storage cleanup recommendations auditable enough that people will
actually review and use them.

Every cleanup tool available today ranks files by how much space they free.
SANCHAY ranks them by how bad it would be if the suggestion turned out to be
wrong. A file that lacks qualifying recovery evidence is never placed in the review plan — no
matter how large it is, and no matter how long it has remained unchanged.

---

## Description

SANCHAY walks the disk once and collects only metadata for each file: logical
size, allocated block count where the filesystem exposes it, last-access time,
last-modified time, and inode number. No file contents are read at this stage.

It then does six things.

Before the scan records metadata, SANCHAY excludes common credential
directories, environment files, private-key formats, local credential vaults,
Docker configuration, and npm and Terraform CLI credential files. They are
never duplicate-hashed or placed in a recommendation.

**1. Finds duplicates cheaply.** Files are grouped by size first. Only groups
that collide get their first 64 KB hashed. Only what still collides after that
gets a full BLAKE2b-256 digest. Before a duplicate becomes reviewable, SANCHAY
also compares that file with its named survivor byte for byte. Files whose
sizes do not collide are never opened.
On Linux, each candidate is opened descriptor-by-descriptor from the canonical
scan root with no-follow flags. A symlink component, non-regular file, or
identity change between scan and read is rejected rather than becoming content
evidence.
Hardlinks pointing at the same inode are not counted as duplicates, because
deleting one of them frees no space. SANCHAY counts that inode once in disk
usage, snapshot, forecast, and treemap metrics, using allocated blocks rather
than sparse logical length where Linux exposes `st_blocks`, and excludes every
individual hardlinked path from the review plan.

**1a. Separates tool-owned system storage.** On Debian-derived BOSS, APT
archives in `/var/cache/apt/archives/` and persistent systemd journals in
`/var/log/journal/` are useful space signals but not loose-file cleanup
candidates. SANCHAY measures them in a separate advisory section, excludes them
from deduplication reads and `--target-reclaim`, and names the owning-tool
review route. APT archives remain under APT policy; journal vacuuming remains
under an approved retention policy because it may affect audit or incident
evidence. When present, Docker Engine, containerd, and Flatpak system stores
under `/var/lib/` receive the same treatment: SANCHAY does not hash, rank, or
turn their individual files into raw cleanup recommendations.

**1b. Surfaces deleted files still held by processes.** On Linux, a directory
walk cannot see a file after unlinking even though its allocated blocks persist
until its final open descriptor closes. SANCHAY reads visible
`/proc/<pid>/fd` entries only for the selected filesystem and reports matching
deleted regular files as operational evidence. They are never added to the
cleanup plan or reclaim target, and SANCHAY never signals, restarts, truncates,
or deletes a process-held file.

**2. Works out how recoverable each file is.** This is the core of the tool.
Every file lands in one of four classes:

- disposable — it lives in a narrow, conventional cache or tool-specific
  build-output path (__pycache__, .cache, target/debug, target/release,
  .next/cache). This is a **path heuristic**, not a recovery proof: SANCHAY
  requires a human to confirm the owning tool before clearing it. Whole
  dependency trees and virtual environments are deliberately not assumed to be
  regenerable from their path alone.
- duplicate — an identical copy exists elsewhere and survives the delete.
- tracked — it is committed inside a git repository.
- unique — none of the above. Nothing gets it back.

Files in the unique class are dropped from consideration entirely, before any
ranking happens.

**3. Ranks what survives.** priority = reclaimable allocated bytes ×
unchanged-age × (1 − regret),
where unchanged-age runs from 0 for a file modified today up to 1 for a file
unchanged for a year, and regret is a fixed weight per class (0.02 disposable,
0.10 duplicate, 0.20 tracked). It deliberately does not claim that a file has
not been read: access timestamps are mount-policy dependent and hashing can
touch them.

An operator can also state a reclaim target such as `--target-reclaim 5G`.
SANCHAY first selects from the lowest recovery-risk class, then uses the
smallest safe excess within that class to meet the request. If the
recovery-evidence gate cannot meet the target, it reports the shortfall rather
than expanding into protected files. This target is intentionally scoped to one
filesystem: explicit cross-filesystem traversal is inventory-only and rejects a
combined target because releasing space on another mount does not relieve the
filesystem under pressure. A plan written in that mode carries an explicit
`cross_filesystem_inventory` scope and capacity-boundary note.

**4. Estimates storage runway.** Normally this needs weeks of snapshots. On a
first run, SANCHAY derives an initial bytes-per-day estimate from the
distribution of modification times across the scan and compares it with current
free space. It reports this as an estimate, not a guaranteed exhaustion date:
later writes, deletes, and workload changes can alter it.

After two or more time-separated aggregate snapshots, SANCHAY can also fit an
explainable local linear trend. It reports the learned bytes-per-day slope; with
three or more snapshots it also reports R-squared fit quality, giving the user
a measurable forecast without uploading file names or contents.
Cross-filesystem inventories do not produce a shared runway or aggregate
snapshot, comparison, or history claim.

**5. Writes a review-only plan.** Each eligible recommendation records its
classification, observed device/inode/logical-size/allocated-size/mtime-nanoseconds/link-count identity, and typed recovery
evidence with a visible strength: direct full-content match for duplicates,
repository-state evidence for clean Git files, or a clearly labelled heuristic
for conventional cache paths. Duplicate candidates name the copy that will
survive. The JSON plan carries a SHA-256 integrity checksum, which detects
accidental plan changes but is not a digital signature. `sanchay --verify-plan
cleanup-plan.json` rechecks the checksum, file identity, retained duplicate,
and clean Git HEAD state where applicable. A changed link count invalidates the
plan, because it changes whether a path can release physical storage. SANCHAY
never deletes or moves files.

The plan also freezes the decision trace for every recommendation: logical
size, reclaimable allocated bytes, unchanged-age factor, regret weight,
formula, and computed priority. A
reviewer can inspect the model inputs instead of accepting an opaque score.

**6. Shows and explains.** A treemap is drawn with one block per physical inode
sized by allocated bytes, coloured by recoverability rather than logical size — green for disposable, red for
irreplaceable — so hardlink aliases do not overstate disk use. The default
plain-language narrative is deterministic and local. An optional cloud
narrative requires a separate explicit flag and receives only opaque candidate
IDs, fixed recoverability class, allocated bytes, and unchanged age—not raw
paths or file contents.

The optional model receives this minimized metadata only after ranking is
complete. It cannot add a file, remove a file, change an order, or invoke an
action. If the model produced a completely wrong answer, the worst outcome is
an awkward description — never an automatic file action.

---

## Novelty

Existing tools split into two groups and neither asks our question.

Duplicate finders (rmlint, fdupes, jdupes, rdfind, Czkawka) find identical
content and stop there. Disk visualisers (Baobab, QDirStat, Filelight, ncdu,
duc) draw a treemap sized by bytes. Both treat a 2 GB build cache and a 2 GB
folder holding someone's only copy of their work as the same object, because by
their measure the two are identical.

SANCHAY introduces a regret model: an estimate of what it costs to be wrong
about a file, derived from whether the system can reproduce that file. This
changes the ranking objective from "how much space" to "how much space has
evidence for review". Files classified as irreplaceable are structurally excluded
from the candidate manifest, regardless of size or age; the tool then requires
human review and never performs deletion itself.

Two smaller original pieces support it. The first scan offers an mtime-derived
runway estimate, while later aggregate snapshots drive an explainable local
linear trend with a visible fit quality. This gives immediate orientation
without pretending a single instant is a guaranteed exhaustion date. The
treemap is coloured by recoverability rather than by logical size and uses
allocated-byte physical-inode accounting, which turns the safety model into something visible
instead of something buried in a table.

---

## Innovation

The safety boundary is structural, not behavioural. Most AI system tools try to
make the model behave safely through careful prompting. We put the model outside
the decision entirely — the ranking is finished before the model is called, and
the model is given only files already judged eligible for review. A hallucination
cannot promote a protected file into the recommendations because the model has no
mechanism to promote anything. SANCHAY itself creates a review-only plan and does
not delete or move user files.

This matters beyond storage. Any AI tool that acts on a user's system faces the
same question, and "prompt the model to be careful" is a weaker answer than
"give the model no way to cause the harm". SANCHAY is a small, complete
demonstration of the second approach.

The practical impact: a ranked review artifact that makes the reason and
evidence for each storage recommendation visible before a person acts.

---

## Data Set Used

No external dataset is used.

SANCHAY operates on the user's own filesystem metadata — paths, sizes, access
and modification timestamps, and inode numbers. File contents are read only to
confirm that two files of identical size are genuinely identical, and those
reads are discarded immediately after hashing.

Nothing leaves the machine for the default `--explain` narrative. A user may
separately opt in to `--cloud-narrative`; it sends only opaque candidate IDs,
recoverability class, allocated bytes, and unchanged age. No raw paths, file
contents, or credential metadata are transmitted. The cloud output cannot add
or act on a candidate.

---

## Tech Stack

Language: Python 3.9+

Core (no third-party dependencies): os and hashlib from the standard library.
blake2b is used for content hashing — faster than SHA-256 and adequate here,
since this is duplicate detection rather than a security boundary.

Optional: plotly (MIT) and pandas (BSD-3) for the treemap; anthropic (MIT) for
the written summary. Both are lazy-loaded, so the core installs and runs with
zero dependencies.

Packaging: pip-installable via pyproject.toml, exposing a sanchay console
command. Licence MIT.

AI-assisted development: Claude was used as a coding assistant during
development. All design decisions, the regret model, and the ranking logic are
the team's own, and the team can explain every line.

---

## Model Type

Inbuilt Model.

The model that makes the decisions — the regret classifier and the ranking
function — was built by us. It is a rule-based, fully inspectable model rather
than a trained one, chosen deliberately: every recommendation traces to a
specific reason ("this is a conventional cache path", "this has a duplicate at that path")
that can be printed and challenged. A trained classifier would need labelled
ground truth and a validation story before it could safely influence this gate.

For capacity forecasting, the tool also learns an on-device linear trend from
the user's aggregate snapshots and reports its slope and R-squared value. This
is deliberately a small, inspectable statistical model: the user can see the
inputs, the fit quality, and the exact limitation of the forecast.

A separate large language model (Claude, accessed via the Anthropic API) is used
only to write findings up in readable English. It takes no part in the
decisions, and the tool runs fully without it.

---

## GitHub Link

https://github.com/basithladdu/sanchay

---

## Deployment Link (optional)

https://sanchay-swart.vercel.app
