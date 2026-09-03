# SANCHAY — final-round slide copy

Prepared outside the source repository on 2026-09-01. Transfer this copy into
the official C-DAC template when it is supplied. Do not place a track number on
the title slide until the organizer resolves the conflict between the finalist
email and the guideline annexure.

## Design rule

Use an off-white canvas, near-black text, a thin green line for evidence that
permits review, amber for deferred/managed storage, and red only for withheld
or rejected claims. Use small monospace labels only where they identify a CLI
fact. No dashboard, gradient, fake telemetry, AI brain artwork, badges, or
card grids.

## Slide 1 — SANCHAY

### Safer storage decisions for Linux

**AI-Powered Intelligent Storage Optimizer for Linux OS**  
Team Zeros and Ones

Recommendations only. No automatic deletion or file movement.

**Speaker note**

> C-DAC describes Secure BOSS for critical endpoints with encrypted LVM disks,
> service and port controls, kernel-module restriction, and logging, monitoring,
> and alerts. In that operating context, a full disk is not a request to delete
> the largest file. Before an operator changes storage on an LVM-encrypted
> endpoint, they need evidence that a candidate is recoverable. SANCHAY is a
> local, evidence-first, review-only decision layer: it ranks only files with
> explicit recovery evidence, protects system-owned state, and writes a plan a
> human can verify before any separate cleanup.

`[Sources]`

- Implementation: `sanchay/plan.py`, `sanchay/cli.py`, `sanchay/verify.py`.
- C-DAC Secure BOSS product information:
  https://www.cdac.in/index.aspx?id=product_details&productId=SecureBOSSLinux

## Slide 2 — Size does not establish recoverability

Left side, green:

`2 GB`  
Regenerable build cache  
Recovery route: rebuild

Right side, red:

`2 GB`  
Only copy of a thesis or database export  
Recovery route: unknown

**Disk tools rank bytes. SANCHAY gates on recovery evidence first.**

**Speaker note**

Unknown recoverability is not low risk. A large size is a reason to inspect, not
permission to remove. This is why a generic dashboard or a "clean now" button
is not the product centre.

`[Sources]`

- Implementation: `sanchay/plan.py` recovery-evidence classes and protected
  file gate.

## Slide 3 — The decision path has a hard safety boundary

Use `SANCHAY_EVIDENCE_ARCHITECTURE.svg` as the full-width visual. Do not add a
second architecture graphic, decorative icons, or extra cards around it.

`Local scan` → `typed recovery evidence` → `protected-file gate` →
`review-only plan` → `human decision`

Eligible evidence:

- Regenerable cache or build output
- Byte-confirmed duplicate with a named peer
- Clean Git HEAD file

Withheld before ranking:

`unique` · `untracked` · `credential/control` · `managed OS state` · `hardlink`

**Speaker note**

The key design choice is that model narration, if enabled, is downstream of
this gate. It receives opaque metadata only and cannot add candidates, change
the safety boundary, or execute a file action.

`[Sources]`

- Implementation: `sanchay/plan.py`, `sanchay/dedup.py`, `sanchay/managed.py`.
- Security rationale: [OWASP prompt-injection prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
  (applied as a boundary, not as a claim of OWASP certification).

## Slide 4 — The target optimizer stays inside eligible evidence

`Need 600K`

1. `204,800 B` — regenerable cache — regret `0.02`
2. `524,288 B` — byte-confirmed duplicate — regret `0.10`

`Selected: 729,088 B`  
`Protected unique files: 0 B selected`

**Lower recovery risk first. Exact minimum excess only within the safe class.**

**Speaker note**

Use the disposable fixture. The selection trace is the truth about what was
chosen; the following review table is deliberately labelled a priority list,
not an execution order. For a same-risk class of at most 28 candidates, the
optimizer makes a bounded exact subset selection. Larger classes use a
recorded deterministic fallback. It never expands into protected data to meet a
target.

`[Sources]`

- Implementation and proof: `sanchay/plan.py`, `sanchay/demo.py`,
  `tests/test_plan.py`.

## Slide 5 — Capacity intelligence refuses false precision

`First scan`  
Readable-inventory orientation — no promised date

`Runway`  
Same root/device, at least three snapshots, at least 24 hours, fit quality ≥ 0.80

`Risk`  
Seven complete same-capacity snapshots across seven days

**When the evidence is weak, the forecast is withheld.**

**Speaker note**

The system treats a single scan as context, not a capacity prediction. A mount
resize, mixed filesystem scope, incomplete access, weak fit, or inadequate
history leaves the appropriate forecast blank and explains why. No forecast
triggers deletion, alerting, or a network action.

`[Sources]`

- Implementation: `sanchay/snapshot.py`, `sanchay/risk.py`.
- Kumar and Chamness, [Stochastic Estimated Risk for Storage Capacity](https://arxiv.org/abs/1901.10552): the cited work reframes capacity from a single full-date estimate to a horizon risk; SANCHAY adopts only that conservative framing and does not claim its production accuracy.

## Slide 6 — The demo proves the negative as well as the positive

Show the actual terminal sequence, not a screen recording:

1. `capstone-thesis.txt` absent from the plan
2. Duplicate includes a named byte-confirmed evidence peer
3. Hardlink alias excluded: one unlink would release no blocks
4. `--target-reclaim 600K` prints the selection trace
5. `--verify-plan` passes; mutate one synthetic cache; verification fails closed

**No file is deleted, moved, signalled, or transmitted in this demo.**

**Speaker note**

Run the deterministic fixture from the repository on a prepared Linux machine.
Do not demonstrate against an organizer, personal, or production system. If
interrupted, show this slide's fourth and fifth steps immediately: they give the
jury a reliable audit point.

`[Sources]`

- Implementation and commands: `sanchay/demo.py`,
  `sanchay/docs/FINAL_ROUND_RUNBOOK.md`.

## Slide 7 — A credible fit for a hardened Linux endpoint

Local core  
No required cloud call or cleanup executor

Mount-aware capacity  
One filesystem by default; no false shared-capacity claim across mounts

Managed stores deferred  
APT, journal, containers, Flatpak, boot, configuration, and service state stay
tool-owned

Aggregate handoff only  
Optional operator brief omits roots, paths, names, PIDs, mount sources, and
content

**Secure BOSS fit — not an unproven integration claim.**

**Speaker note**

C-DAC describes Secure BOSS for critical endpoints, with full-disk encryption,
hardening, logging/monitoring, and standalone/intranet or ISOC-monitored use.
Its published setup uses an LVM-encrypted hard disk. SANCHAY's local,
review-only and mount-scoped workflow is a fit for that operating model. It is
not presented as deployed, certified, endorsed, or integrated with Secure BOSS
or ISOC.

It deliberately does not resize an LVM volume, alter encryption or mount state,
restart a service, or transmit an ISOC event. Those are availability and policy
changes that must remain with the platform owner; SANCHAY's contribution is a
reviewable local evidence artifact before that separate decision.

`[Sources]`

- C-DAC, [Secure BOSS Linux product information](https://cdac.in/index.aspx?id=product_details&productId=SecureBOSSLinux).
- C-DAC, [Annual Report 2024-25](https://www.cdac.in/index.aspx?id=pdf_Annual-Report_24-25):
  public Secure BOSS/ISOC context for policy and log management; context only,
  not evidence of an SANCHAY integration.
- Implementation: `sanchay/managed.py`, `sanchay/capacity.py`,
  `sanchay/operator_brief.py`.

## Slide 8 — Evidence before irreversible action

### SANCHAY does not ask a secure endpoint to trust an AI with deletion.

### It gives the operator verifiable evidence before an irreversible decision.

Team Zeros and Ones  
`github.com/basithladdu/sanchay` *(show only if organizer guidance permits)*

**Speaker note**

Do not end on a generic thank-you. Stop on the decision boundary, then keep the
terminal and the verified plan open for questions. The repository URL is kept
off-screen until the team receives organizer guidance on the Stage 1 repository
issue.

`[Sources]`

- Final-round positioning is derived from the implementation and the official
  Stage 2 rubric. C-DAC Secure OS tender context concerns secure/local/distributed
  storage, resilience, AI/ML and observability; it is context only, not the
  hackathon scoring rubric: [C-DAC tender PDF](https://cdac.in/index.aspx?dynamicId=ODI3ODM0MDA%3D&id=tenders_viewpdf).

## Live-demo command sequence

Run from the repository root on a prepared open-source Linux environment:

```bash
python -m sanchay.demo --prove
```

If the jury requests the target-selection output, use the exact command from
`docs/FINAL_ROUND_RUNBOOK.md`. Do not improvise a target against a real device.
