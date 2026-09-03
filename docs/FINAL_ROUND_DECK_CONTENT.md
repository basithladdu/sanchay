# Final-round deck handoff - SANCHAY

`docs/SANCHAY.pptx` is a pre-selection draft and must not be used unchanged.
It contains incorrect Track 1, guarantee, exact-forecast, legal-compliance, and
test-coverage claims. Preserve it as history; move the core content below into
the organizer's template when it arrives.

Use [`FINAL_ROUND_JURY_BRIEF.md`](FINAL_ROUND_JURY_BRIEF.md) for spoken
C-DAC-specific positioning and hostile-Q&A answers; keep that material out of
the visible slides.

## Communication target

By the end, a C-DAC jury should see SANCHAY as a practical Linux storage
optimizer because it optimizes only within explicit recovery evidence and leaves
every irreversible action to a human operator.

## Visual direction for the official template

- Use the SANCHAY evidence-console language: off-white field, ink text,
  restrained green/blue/red evidence accents, and small monospace labels.
- One claim and one visual composition per slide. Do not use a card grid,
  gradient hero, decorative icon set, fake telemetry, or generic AI imagery.
- Put source URLs and technical qualifications in speaker notes, not in the
  visible body copy. Keep the eight core slides to about 9-10 minutes.

## Core deck - 8 slides

### Slide 1 - SANCHAY

**Safer storage decisions for Linux**

- Team Zeros and Ones
- Track 2 - AI at Application Level
- AI-Powered Intelligent Storage Optimizer for Linux OS

Footer: **Recommendations only. No automatic deletion or file movement.**

Visual: title, team, and one compact evidence-chain mark only.

### Slide 2 - Size does not tell us what is safe to remove

Use a two-column contrast, not a list:

| Same size | Different consequence |
| --- | --- |
| Regenerable build cache | Only copy of a thesis, database export, or document |

Visible conclusion: **Disk tools rank bytes. SANCHAY ranks recovery evidence
before anything is recommended.**

Speaker point: a size-only cleaner cannot distinguish a 2 GB cache from a 2 GB
irreplaceable file. SANCHAY treats unknown recoverability as a reason to
withhold a recommendation.

### Slide 3 - Learned recommendations inside a hard safety gate

Visual flow:

`Verified metadata + activity -> local 3-class ML -> deterministic allowed-action gate -> Ollama/API reasoning review -> Keep / Cleanup Review / Archive Review -> human decision`

Show only these three evidence routes:

- byte-confirmed duplicate;
- clean Git HEAD;
- narrow regenerable cache/build-output path.

Visible conclusion: **The model influences recommendations; deterministic
recovery evidence decides which action types are allowed.**

Speaker point: the classifier is a local multiclass logistic regression trained
from a disclosed 38-row synthetic seed CSV. The plan exposes probabilities,
feature contributions, version, and dataset checksum without claiming production
accuracy. Unique files can be Keep or Archive Review, never Cleanup Review.
An optional constrained reasoning stage can use local Ollama or an explicitly
configured OpenAI-compatible API. It receives only opaque IDs, bounded metadata,
local probabilities, allowed actions, and evidence flags. It may confirm an
already-permitted review or change it to Keep; it cannot promote a protected
file, bypass a gate, or execute an action.

### Slide 4 - A reclaim target is optimized inside the safety boundary

Visual: the deterministic fixture target.

`Need 600K -> 204,800 B regenerable cache -> 524,288 B byte-confirmed duplicate -> review plan`

Visible conclusion: **Use the lower-risk class first; minimize excess only
within eligible evidence.**

Speaker point: for a same-risk class of up to 28 candidates, SANCHAY uses a
bounded exact subset search; a larger class records a deterministic greedy
fallback in the plan. It never expands into protected files to satisfy a target.

### Slide 5 - Capacity intelligence refuses false precision

Use a four-stage evidence ladder:

1. First scan: readable-inventory orientation, explicitly not an exact date.
2. Local schema-6 snapshots: observed mount used bytes, write-once artifacts.
3. Runway: same root/device, 24-hour history, at least three snapshots, and
   R-squared >= 0.80.
4. Risk: seven complete same-capacity snapshots across seven days before a local
   horizon probability is shown.

Visible conclusion: **When evidence is weak, SANCHAY withholds the forecast.**

Footer: no file, volume, alert, or network action follows from a forecast.

### Slide 6 - The live proof is controlled and repeatable

Show one terminal capture from the deterministic fixture, in this order:

- `capstone-thesis.txt` is absent from cleanup recommendations;
- a duplicate has a named byte-confirmed evidence peer;
- hardlink aliases are excluded from reclaimable storage;
- the target optimizer prints a lower-risk-first selection trace, while the
  review table is explicitly labelled as priority rather than execution order;
- `--verify-plan` passes, then fails closed after one synthetic cache mutation.

Use the `--target-reclaim 600K` CLI step in `FINAL_ROUND_RUNBOOK.md` for the
visible selection trace. Use `python -m sanchay.demo --prove` from the
repository root as the rehearsal check. It creates a disposable fixture only;
it never deletes, moves, or transmits a file.

### Slide 7 - Designed for a secure Linux operating model

Use four concise proof points:

- local core; no file contents transmitted by the core workflow;
- one filesystem by default; no shared capacity claim across mounts;
- APT, journal, Docker, containerd, Flatpak, boot, config, and service state
  remain tool-owned advisories, never raw file-deletion candidates;
- a path-free aggregate operator brief supports review without exporting roots,
  paths, names, PIDs, mount sources, or content.

Visible conclusion: **Secure BOSS fit, not an unsubstantiated integration claim.**

Speaker point: C-DAC describes Secure BOSS for critical endpoints and
intranet/standalone or ISOC-monitored operation. SANCHAY's local, constrained
workflow is designed to fit that setting; it does not claim C-DAC endorsement,
deployment, or an ISOC API.

### Slide 8 - Close on the decision boundary

**SANCHAY does not ask users to trust a cleanup model. It gives them evidence
to review before an irreversible cleanup step.**

Keep this slide sparse: team name, repository, and one QR code only after it
has been tested from the presentation device.

## Appendix - use only for jury questions

### A. What a duplicate recommendation actually proves

`same size -> 64 KB prefix -> BLAKE2b-256 digest -> byte-for-byte confirmation
-> named evidence peer -> identity recheck`

- A match does not identify the authoritative copy or prove an independent
  backup; the operator selects retention.
- Hardlinks share a `(device, inode)` identity, count once in allocated-byte
  metrics, and are excluded because one unlink releases no physical bytes.
- Linux duplicate reads stay anchored to the selected root and reject symlink
  component swaps or identity drift.
- `--verify-archive SOURCE RETAINED_COPY` verifies separately chosen matching
  files without copying, moving, or deleting either. A same-filesystem match is
  never called a backup.

### B. Capacity and topology assurance points

- Snapshots record mount total/used/free separately from the readable inventory;
  their SHA-256 checksum detects a mismatch against stored content, not a
  signature or device attestation. Writes never replace an artifact.
- `--snapshot-history DIR` keeps a local, operator-chosen history without a
  scheduler, network call, or cleanup action.
- A capacity resize, incomplete scan, mixed root/device, weak fit, or inadequate
  history withholds runway or risk claims as appropriate.
- Btrfs, overlay, device-mapper, nested mounts, reserved blocks, inode
  exhaustion, and visible deleted-open files are labelled operational/accounting
  boundaries, never automatic cleanup instructions.
- `--capacity-audit` reports a mount-level accounting gap, not reclaimable or
  fully explained storage.

### C. Concise jury answers

**Where is the AI?** Stage 1 is a local multiclass logistic-regression classifier
that directly recommends Keep, Cleanup Review, or Archive Review from bounded
metadata and positive usage evidence. Stage 2 is an optional Ollama or
OpenAI-compatible reasoning model that reviews only prefiltered candidates and
returns a structured action, confidence, reason codes, and explanation. The
generated plan records both model stages. Deterministic recovery rules constrain
the action space, and neither model can execute actions.

For a standalone demonstration, use `--ai-provider ollama` or `/ai ollama`.
The fixed local loopback request uses no proxy or redirect. The reasoning stage
may conservatively veto or reprioritize already-permitted reviews, but cannot
add an unsafe candidate, alter verification, or obtain cleanup authority.

**Why not delete the obvious files automatically?** Matching bytes or a cache
path is not proof of business ownership, retention policy, or operator intent.
SANCHAY creates a reviewable plan and verifies it again before a human acts.

**Why probability instead of an exact full-disk date?** Workloads are not
perfectly linear. The risk model is deliberately withheld until strong local
same-mount history exists, and it controls no action.

**Why does this fit a sovereign secure OS?** The core is local and
dependency-light; it contains collection and action boundaries rather than
silently exporting paths or operating on the OS.

## Source-note handoff for the final deck

Add a `[Sources]` block to the speaker notes of every slide that makes an
external claim. Use these sources:

- C-DAC BOSS/FOSS and Secure BOSS facts:
  `docs/FINAL_ROUND_RESEARCH.md` and `docs/CDAC_SECURE_BOSS_FIT.md`.
- Secure OS tender material: use only as context, never as hackathon rules.
- Storage redundancy, forecasting, and practitioner evidence:
  `docs/FINAL_ROUND_RESEARCH.md`.
- Implementation claims: `sanchay/plan.py`, `sanchay/dedup.py`,
  `sanchay/managed.py`, `sanchay/snapshot.py`, `sanchay/demo.py`, and the
  verified test suite.
