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
2. Run the exact module commands below from the repository root; they work
   without installing console scripts. `python -m pip install -e .` is optional
   if the team prefers the shorter `sanchay` and `sanchay-demo` commands.
3. For the terminal dashboard only, run `python -m pip install -e ".[tui]"`.
4. Run `python -m unittest discover tests` and keep the passing output in the
   terminal scrollback.
5. Open the public page only as a seeded explanatory walkthrough. State that it
   does not scan the visitor's filesystem.
6. The page renders embedded offline chart summaries first. During rehearsal,
   append `?offline=1` to prove its no-CDN state before the optional Plotly
   enhancement is allowed to load.
7. Before the final, run `python -m sanchay.demo --prove`. It creates only a disposable
   fixture, checks the protected/duplicate/hardlink boundaries, then changes
   only the synthetic cache and confirms that the plan fails closed. The command
   is a rehearsal check, not a substitute for the visible live sequence below.
8. If the jury asks how capacity-risk withholding works, run
   `python -m sanchay.demo --risk-prove`. Its first line explicitly identifies synthetic
   aggregate snapshots, not endpoint telemetry. It proves the seven-snapshot
   and changed-capacity gates, not a forecast for the demo machine.
9. The bundled recommendation classifier is the always-available first AI stage.
   When a pre-provisioned local model is available, enable the constrained
   second stage with `--ai-provider ollama`; keep the deterministic gate and
   local fallback visible in the demo.

## Exact live-demo sequence

```bash
PYTHON=python3
DEMO_ROOT="$(mktemp -d /tmp/sanchay-demo.XXXXXX)"
EVIDENCE_ROOT="$(mktemp -d /tmp/sanchay-evidence.XXXXXX)"
"$PYTHON" -m sanchay.demo "$DEMO_ROOT"

"$PYTHON" -m sanchay.cli --verify-archive "$DEMO_ROOT/downloads/boss-image-copy.iso" "$DEMO_ROOT/archive/boss-image.iso"
"$PYTHON" -m sanchay.cli "$DEMO_ROOT" --target-reclaim 600K --limit 10 --plan "$EVIDENCE_ROOT/cleanup-plan.json" --snapshot "$EVIDENCE_ROOT/baseline.json" --explain
"$PYTHON" -m sanchay.cli --verify-snapshot "$EVIDENCE_ROOT/baseline.json"
"$PYTHON" -m json.tool "$EVIDENCE_ROOT/cleanup-plan.json"
"$PYTHON" -m sanchay.cli --verify-plan "$EVIDENCE_ROOT/cleanup-plan.json"
```

Keep the two temporary directories open through questions, then remove them
manually. They contain only the disposable fixture and its generated evidence.
The commands use fresh paths on purpose: SANCHAY refuses to replace an existing
review plan or snapshot. An operator can deliberately refresh a plan only with
the explicit `--replace-plan` flag.

Point out these concrete facts, not a generic dashboard:

- `documents/capstone-thesis.txt` is a deliberately unique fixture and is not
  in the plan.
- `downloads/boss-image-copy.iso` is a duplicate candidate only because it
  byte-matches `archive/boss-image.iso`, which is named as a deterministic
  evidence peer. The separate archive verification uses an operator-chosen
  retained copy; the duplicate plan itself does not infer source of truth.
- `--verify-archive` first proves those files are byte-for-byte equal and
  separate inodes. The fixture puts them on the same filesystem, so SANCHAY
  deliberately calls this recovery evidence for a manual space review, **not**
  an independent backup.
- `hardlinks/source.bin` and `hardlinks/alias.bin` are not reclaimable
  duplicates because they share one `(device, inode)` identity. They count as
  one physical file in the readable allocated-inventory total and treemap;
  mount-scoped forecast snapshots separately measure filesystem-used bytes.
  Where Linux exposes block allocation, sparse-file logical length is also not
  treated as freeable storage.
- `workspace/node_modules/.cache/bundle.bin` is a reviewable regenerable-output
  candidate, not an automatically deleted file.
- `--explain` produces a deterministic local narrative and says no candidate
  data left the machine. Do not use `--cloud-narrative` in the final demo unless
  the team has separately approved it and configured an API key.
- `python -m sanchay.demo --risk-prove` is available only as a transparent synthetic
  aggregate rehearsal: it demonstrates that a qualifying seven-snapshot model
  result is withheld after a capacity resize. It is not a live-device forecast.
- The explicit `600K` reclaim request first uses the 204,800-byte regenerable
  cache, then uses the 524,288-byte duplicate as the exact minimum-excess choice
  for the remaining target. The plan records that optimizer strategy; it does
  not broaden into the thesis or hardlinked entries to meet a target.
- The CLI prints those two selection steps before the candidate table. The table
  is a deterministic review-priority view, explicitly not an execution order.
- `cleanup-plan.json` has a SHA-256 integrity checksum (not a signature),
  candidate identity including link count, typed recovery evidence, and a
  human-review requirement. Each recommendation also carries its frozen
  logical-size/allocated-reclaim/age/regret decision trace and computed
  priority.

## Fail-closed proof

Change only the disposable fixture, then recheck the original plan:

```bash
printf 'fixture changed\n' >> "$DEMO_ROOT/workspace/node_modules/.cache/bundle.bin"
"$PYTHON" -m sanchay.cli --verify-plan "$EVIDENCE_ROOT/cleanup-plan.json"
```

Expected result: verification reports that the candidate identity changed and
exits non-zero. It does not delete, move, or alter any file. This is the most
important fail-closed evidence in the live demonstration.

## Concise jury answers

**Where is the AI?** A local three-class logistic-regression model predicts Keep,
Cleanup Review, or Archive Review from bounded metadata and positive activity
evidence. A constrained Ollama or explicitly configured OpenAI-compatible model
then reviews only the locally prefiltered candidates. It receives opaque IDs,
metadata, probabilities, allowed actions, and evidence flags—not raw paths or
file contents—and returns structured action/confidence/reason fields. It may
confirm a permitted review or change it to Keep; it cannot promote protected
files or execute actions.

`--ai-provider ollama` sends those opaque records to a fixed loopback Ollama
endpoint only: no proxy or redirect is used. `--ai-provider auto` prefers that
local path and falls back to an API only when `SANCHAY_AI_API_*` is explicitly
configured. Invalid or unavailable model output retains the local classifier
result. Deterministic gates still decide every permitted action class.

**Why show capacity risk rather than an exact date?** Storage use can be
non-linear. With strong local history, `--risk-horizon DAYS` estimates the
probability of reaching current mounted capacity within that horizon using a
Brownian-motion-with-drift model. It is deliberately withheld without seven
complete same-root snapshots spanning seven days, twelve-hour minimum
intervals, and unchanged mount capacity. The probability is conditional on
that model; it is not a capacity guarantee, diagnosis, alert, cleanup command,
or volume action.

**Why is a model narrative not automatic?** A storage scan can contain
sensitive path names, and file-derived text is untrusted input for an LLM. The
local narrative is default. `--cloud-narrative` requires separate consent and
transmits only opaque IDs and fixed numeric/class metadata; the decision gate,
plan, verification, and guarded action permissions are enforced outside the
language model.

`--ollama-narrative` is a separately requested loopback call; the default
remains the deterministic local narrative. Neither narration path can alter the
plan, verification, or guarded action executor.

**Why not automate deletion?** The requested problem includes recommendations;
the irreversible step has a different risk profile. SANCHAY supplies an
auditable plan and revalidation gate so an operator retains authority.

**What about archiving?** The local classifier can place cold unique files in
Archive Review, but never cleanup. `--verify-archive SOURCE RETAINED_COPY` is a
read-only gate for an operator-chosen copy. It rejects credential and
system-managed paths, a hardlink alias posing as a second copy, mismatched
bytes, and identity changes during the check. A verified separate inode then
becomes a named survivor for review. Same-filesystem equivalence is not called
a backup; destination durability, retention, and restoration remain operator
policy.

**What if an operator needs a stated amount of free space?** `--target-reclaim`
exhausts lower recovery-risk classes before it considers a higher-risk class.
For a class of 28 or fewer candidates that can meet the remaining request, a
bounded exact subset search minimizes excess; a larger class records a
deterministic greedy fallback. It reports whether the target is met and never
widens scope to protected files. That capacity claim is deliberately limited to
one filesystem. Explicit cross-filesystem scans are inventory-only; they reject
a shared reclaim target, snapshot comparison, and runway forecast because
freeing another mount does not relieve the filesystem under pressure.

**What if `df` says full but the directory scan does not add up?** On an
explicit `--capacity-audit`, SANCHAY first requires a complete scan started at
the root of one mounted filesystem. It then shows filesystem-used blocks,
readable allocated inventory, and visible deleted-open bytes separately. The
remainder is labelled an **accounting gap**, never an automatic cleanup target
or a claimed root cause. Linux can keep an unlinked file allocated while a
process still has it open, so SANCHAY checks visible `/proc/<pid>/fd` records
and reports PID, descriptor, and allocated bytes separately. It never kills,
restarts, truncates, or deletes a process-held file; snapshots, metadata,
protected paths, mount overlays, and filesystem-specific state remain separate
diagnostic questions. The same audit also reports POSIX `statvfs` inode/file-
entry capacity where the filesystem exposes it: total entries, free entries,
and entries available to an unprivileged process. This catches the distinct
case where byte space remains but no file entry can be created. It does not
identify a file to remove or claim a cause when the counters are unavailable.
It also distinguishes free blocks from blocks actually available to the
unprivileged operator, so a filesystem policy/reservation boundary is visible
without recommending a change to that policy. SANCHAY also counts nested mount
points under the selected root: its default one-filesystem scan prunes those
visible child mounts before traversal, including same-device bind views that a
device-number check would miss. The active namespace can obscure older entries
beneath a child mount, so that topology is called out as a possible contributor
to an accounting gap. It never unmounts or remounts a path to inspect it.

**Why does SANCHAY show mount context?** C-DAC describes Secure BOSS as
LVM-encrypted, so filesystem-free bytes alone do not establish volume-group or
thin-pool headroom. SANCHAY reads Linux mount metadata and marks Btrfs,
container-overlay, and device-mapper boundaries as read-only advisory evidence.
It does not run `lvs`, resize a volume, balance Btrfs, or delete a snapshot.

**How can an operator hand this to an ISOC or support team?** The detailed
plan and HTML report stay local because they can include relative paths and
process context. `--operator-brief operator-brief.json` creates a separate,
aggregate-only handoff: counts and allocated bytes by evidence class, managed
storage totals, coverage, mount source class, deleted-open aggregate, capacity
boundary, and, when requested and assessed, the capacity-risk probability,
horizon, sample evidence, and model metrics. It excludes roots, paths, names,
PIDs, process names, mount/device sources, free-form model rationale, and
content; it does not transmit anything, sign an event, or authorize a cleanup.
It is write-once by default, so a new handoff must use a new path unless an
operator explicitly supplies `--replace-operator-brief`.
Use `"$PYTHON" -m sanchay.cli --verify-operator-brief operator-brief.json`
to check its checksum only; it does not reread endpoint files or contact a
service.

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
the plan names a deterministic evidence peer and verification rechecks both
identities and matching content. Matching bytes do not establish source of
truth, so an operator must choose which copy to retain before a manual removal.
On Linux, each read is anchored to the selected root with
no-follow descriptor traversal; a symlink component or identity drift produces
no evidence rather than reading a substituted path. Hardlinks are not counted
as reclaimable copies.

**How reliable is the forecast?** A single scan is labelled as a
readable-inventory mtime estimate. Later schema-6 snapshots compare the same
mounted filesystem's reported used bytes, require the same root/device, and
require a 24-hour first-to-latest history before producing a local linear trend
with an explicit slope and, from three observations onward, R-squared—rather
than turning seconds of background activity into an invented full-disk date.
A two-point slope remains visible as an observation, but SANCHAY withholds a
runway date until at least three captures expose an R² of 0.80 or higher. That
conservative product gate does not make the forecast a guarantee; it prevents
a perfect-looking two-point line or a weak fit from becoming an invented
full-disk date. Each aggregate snapshot has a SHA-256 checksum, so a
checksum-mismatched history artifact is rejected before it can influence the
comparison. That checksum is not a signature or device attestation. Legacy
inventory-only or unsealed snapshots are rejected and must be recaptured.
Snapshot writing also refuses to replace an existing evidence file; choose a
new timestamped output name for each capture.
For an operator-managed recurring record, `--snapshot-history DIR` reads only
SANCHAY's timestamped checksum-matching history artifacts and appends one new
write-once aggregate record. It installs no scheduler and makes no network or
cleanup action.

**What happens if the filesystem was resized?** SANCHAY still shows its
observed mounted-use rate, but withholds a `full in` runway date and withholds
the capacity-risk probability. An LVM or provisioning change makes historical
capacity assumptions ambiguous; SANCHAY does not infer that resized capacity,
run LVM, or issue an operational alert.

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

For C-DAC-specific framing, say **fit**, not integration: Secure BOSS is
described for critical end nodes, ISOC-monitored clients, and
intranet/standalone systems. SANCHAY's local workflow and path-free operator
brief are designed for that environment, but do not send data, call an ISOC
API, or claim C-DAC deployment or endorsement. See
`docs/CDAC_SECURE_BOSS_FIT.md` for the source-bound mapping.

## What not to claim

- Do not call a first-scan forecast an exact date.
- Do not call the seeded web page a real device scan.
- Do not say SANCHAY deletes files, prevents every possible loss, or is legally
  certified for DPDP compliance.
- Do not say C-DAC has endorsed SANCHAY or that its tender defines hackathon
  scoring.
