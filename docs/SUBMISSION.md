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
never duplicate-hashed or placed in a recommendation. The same path boundary is
reapplied by the content-evidence and plan APIs when a caller supplies records
directly.

**1. Finds duplicates cheaply.** Files are grouped by size first. Only groups
that collide get their first 64 KB hashed. Only what still collides after that
gets a full BLAKE2b-256 digest. Before a duplicate becomes reviewable, SANCHAY
also compares that file with its named evidence peer byte for byte. Matching
bytes do not establish source of truth, so an operator chooses retention. Files whose
sizes do not collide are never opened.
On Linux, each candidate is opened descriptor-by-descriptor from the canonical
scan root with no-follow flags. A symlink component, non-regular file, or
identity change between scan and read is rejected rather than becoming content
evidence.
Hardlinks pointing at the same inode are not counted as duplicates, because
deleting one of them frees no space. SANCHAY counts that inode once in disk
inventory and treemap metrics, using allocated blocks rather than sparse logical
length where Linux exposes `st_blocks`, and excludes every individual hardlinked
path from the review plan. Snapshots retain that inventory as a diagnostic, but
their observed-growth and trend calculations use a separate mounted-filesystem
used-byte series.

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

**1c. Records filesystem capacity context.** C-DAC states that Secure BOSS is
installed on an LVM-encrypted hard disk. SANCHAY reads the selected root's
visible Linux mount record and freezes the filesystem/source class in the plan.
If it sees Btrfs, an overlay layer, or a device-mapper source, it explains the
capacity boundary instead of pretending that a directory walk proves
snapshot-aware, host-wide, or logical-volume-pool headroom. It never runs LVM
or Btrfs commands, resizes a volume, balances a filesystem, or deletes a
snapshot.

**1d. Makes a capacity gap visible without calling it reclaimable.** On an
explicit `--capacity-audit`, SANCHAY requires one mounted filesystem root and
complete readable-path coverage. It compares reported filesystem-used blocks
with the readable allocated inventory and visible deleted-open bytes, then
labels any signed remainder an accounting gap. It does not claim that the gap
has one cause or can be freed: protected paths, filesystem metadata, snapshots
or shared extents, mount-overlaid data, and inaccessible state can contribute.
The same read-only audit distinguishes free filesystem blocks from blocks
available to the unprivileged operator, then reports POSIX inode/file-entry
capacity (total, free, and, when reported, unprivileged availability). It can
therefore distinguish a filesystem-policy boundary and the separate inability
to create a new file from an ordinary byte-capacity shortage. It identifies no
file to remove and runs no filesystem, LVM, container, or cleanup action.

**1e. Fences system-reserved OS paths before content reads.** A duplicated byte
sequence under `/usr` or `/etc` is not evidence that it is safe to remove.
SANCHAY separately measures, but never hashes, ranks, or recommends individual
files in boot, configuration, package/cache, log, backup, and service/spool
paths. The narrow APT, journal, Docker, containerd, and Flatpak policies still
win first so the operator receives the relevant owning-tool review route.

**1f. Makes partial scan coverage visible.** Secure endpoints can intentionally
withhold access to part of the selected tree. SANCHAY counts unreadable
directories and files without serialising their paths. If any occur, it labels
the output a readable-file inventory and withholds the mtime forecast and
snapshot/history operations. It can still show review-only evidence for files
actually inspected, but never presents that partial view as whole-tree capacity
evidence.

**1g. Creates a path-free operator brief.** The detailed review plan and HTML
report stay local because they can contain relative paths or process context.
`--operator-brief` writes a distinct aggregate-only JSON handoff for a secure
operations or ISOC review: evidence-class counts, allocated-byte totals,
managed-store totals, coverage, mount source class, deleted-open aggregate, and
capacity boundary. It excludes roots, paths, file names, process IDs/names,
mount/device sources, and file content; it does not transmit data, sign an
event, or authorize cleanup.

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
distribution of modification times across the readable inventory and compares
it with current free space. It reports this as an estimate, not a guaranteed
exhaustion date: later writes, deletes, and workload changes can alter it.

Each schema-5 snapshot records the selected mounted filesystem's total, used,
and free bytes, its filesystem device, and a separate readable-inventory
aggregate. After two or more time-separated snapshots from the same resolved
root and filesystem device, SANCHAY fits its explainable local linear trend to
the **mounted-filesystem used-byte** series. It reports the learned bytes-per-day
slope; with three or more snapshots it also reports R-squared fit quality,
giving the user a measurable forecast without uploading file names or contents.
Older inventory-only snapshots are rejected with a recapture instruction rather
than being mixed into a capacity forecast. SANCHAY also withholds a rate until
the first and latest snapshots are at least 24 hours apart, so seconds of
ordinary background filesystem activity do not become a fictional exhaustion
forecast.
When an explicitly supplied snapshot, plan, report, or operator brief is stored
under the selected root, SANCHAY fences it out of the readable inventory and
review plan on that invocation. Its physical bytes remain in the mounted
filesystem measurement; only the self-referential cleanup candidate is removed.
Cross-filesystem inventories do not produce a shared runway or aggregate
snapshot, comparison, or history claim.

**5. Writes a review-only plan.** Each eligible recommendation records its
classification, observed device/inode/logical-size/allocated-size/mtime-nanoseconds/link-count identity, and typed recovery
evidence with a visible strength: direct full-content match for duplicates,
repository-state evidence for clean Git files, or a clearly labelled heuristic
for conventional cache paths. Duplicate candidates name a deterministic
evidence peer but do not infer the authoritative copy or retention decision.
The JSON plan carries a SHA-256 integrity checksum, which detects
accidental plan changes but is not a digital signature. `sanchay --verify-plan
cleanup-plan.json` rechecks the checksum, file identity, duplicate evidence peer,
and clean Git HEAD state where applicable. A changed link count invalidates the
plan, because it changes whether a path can release physical storage. SANCHAY
never deletes or moves files.

The plan also freezes the decision trace for every recommendation: logical
size, reclaimable allocated bytes, unchanged-age factor, regret weight,
formula, and computed priority. A
reviewer can inspect the model inputs instead of accepting an opaque score.

**Archive-copy proof is separate from archiving action.** An operator may run
`sanchay --verify-archive SOURCE RETAINED_COPY` before treating a chosen archive
copy as a named survivor. The read-only check rejects credential/control and
system-managed paths, hardlink aliases, byte mismatches, and identity drift;
it compares regular-file bytes and rechecks both identities. It does not copy,
move, or delete either path. A same-filesystem result establishes a separate
survivor for a manual space-recovery review, not an independent backup,
retention promise, or restore procedure.

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

Two smaller original pieces support it. The first scan offers a
readable-inventory mtime-derived runway estimate, while later mount-scoped
snapshots drive an explainable local linear trend from filesystem-used bytes
with a visible fit quality. This gives immediate orientation without pretending
a single instant is a guaranteed exhaustion date. The treemap is coloured by
recoverability rather than by logical size and uses allocated-byte
physical-inode accounting, which turns the safety model into something visible
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
the user's mounted-filesystem snapshots and reports its slope and R-squared
value. It preserves the readable inventory separately and rejects a legacy or
different-filesystem snapshot rather than combining unlike inputs. This is
deliberately a small, inspectable statistical model: the user can see the
inputs, the fit quality, and the exact limitation of the forecast.

An optional separate large language model (Claude, accessed via the Anthropic
API) can write findings up in readable English only after ranking is complete.
It takes no part in decisions, and the tool runs fully without it.

---

## GitHub Link

https://github.com/basithladdu/sanchay

---

## Deployment Link (optional)

https://sanchay-swart.vercel.app
