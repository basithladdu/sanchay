# Zeros and Ones - SSM Stage 2 rehearsal card

Use this with the final deck and the existing SANCHAY final-round runbook. It is
a presentation aid only. Do not use it to imply approval, deployment, or a
feature that the repository cannot prove.

Track-label note: the finalist email says Track 2 - AI at Application Level,
while the official guidelines PDF labels the same problem Track 1. Use the team
name and exact problem statement on the title slide; omit the track number until
the organizer resolves the mismatch.

## Timing rule

The organizer email gives the team 15 minutes including demo and jury Q&A.
Aim to finish the prepared story by 9:00. Keep the remaining six minutes for
questions, interruptions, and a terminal recovery buffer.

## C-DAC-specific opening - 25 seconds

> C-DAC describes Secure BOSS for critical endpoints with full-disk encryption,
> service and port controls, kernel-module restriction, and logging, monitoring,
> and alerts. In that operating context, a full filesystem is not permission
> for an AI to delete the biggest file. Before an operator changes storage on an
> LVM-encrypted endpoint, they need evidence that a candidate is recoverable.
> SANCHAY is a local, evidence-first, review-only decision layer: it shows what
> is recoverable, what must stay protected, and why a human must retain
> irreversible authority.

This is a capability-fit framing, not an integration claim. Do not say SANCHAY
is deployed on Secure BOSS, connected to ISOC, approved by C-DAC, or governed
by a C-DAC policy.

## Nine-minute prepared story

| Time | Jury criterion | What to say and show |
| --- | --- | --- |
| 0:00-0:30 | Impact & Alignment | Deliver the C-DAC-specific opening above; land on "a full disk is not permission for an AI to delete the biggest file." Show the title and problem statement. |
| 0:30-1:25 | Explainability | Contrast an equally large regenerable cache with a unique thesis. State that SANCHAY ranks recovery evidence before it recommends anything. |
| 1:25-2:20 | Technical Depth | Show the gate: local scan -> evidence class -> protected-file gate -> review-only plan -> human decision. Name the three evidence routes: byte-confirmed duplicate, clean Git HEAD, narrow cache/build path. |
| 2:20-3:05 | Explainability | Show the 600K target: 204,800 B regenerable cache first, then 524,288 B byte-confirmed duplicate. Explain that the on-screen selection trace is lower-risk-first; the following table is review priority, not execution order. |
| 3:05-4:00 | Scalability & Security | State the boundaries: credentials and system-managed stores are fenced; one filesystem by default; no cleanup executor; model narration cannot change a decision. |
| 4:00-6:40 | Live Demonstration | Run the deterministic fixture sequence from `sanchay/docs/FINAL_ROUND_RUNBOOK.md`. Point out the absent thesis, named duplicate peer, excluded hardlink, target trace, and valid plan. |
| 6:40-7:25 | Live Demonstration | Mutate only the synthetic cache and run `--verify-plan`. Stop after the non-zero fail-closed result. Say explicitly that SANCHAY deleted, moved, and transmitted nothing. |
| 7:25-8:20 | Technical Depth | Explain forecasting discipline: first scan is orientation only; runway and risk are withheld until local same-mount snapshot gates qualify. Do not volunteer the synthetic risk rehearsal unless asked. |
| 8:20-9:00 | Presentation Quality / Impact | Close: "SANCHAY does not ask a secure endpoint to trust an AI with deletion. It gives the operator verifiable evidence before an irreversible decision." Keep the terminal and verified plan visible. |

## What each Stage 2 criterion should see

The official Annexure II lists these six criteria but does not publish an
individual weight for each. Do not invent a marks split; make a concrete proof
visible for every criterion instead.

| Official criterion | Evidence to make visible | Never say |
| --- | --- | --- |
| Live Demonstration | Reproducible fixture, target selection, valid plan, synthetic mutation, failed verification. | "This automatically cleans a real machine." |
| Technical Depth (Q&A) | Recovery classes, allocated bytes, hardlink identity, byte-for-byte confirmation, mount scope, snapshot gates. | "The model decides what to delete." |
| Scalability & Security | Bounded exact selection up to 28 candidates, deterministic fallback, credential fences, managed-store deferral, no network requirement. | "A duplicate is an independent backup." |
| Explainability | Typed evidence, fixed decision inputs, local narrative, selection trace, withheld forecast reasons. | "Our AI is a trained production model" unless one is actually supplied and documented. |
| Presentation Quality | Sparse slides, one claim per slide, readable terminal font, no dashboard tour, direct answers. | "C-DAC has deployed or endorsed us." |
| Impact & Alignment | Safer decisions for local Linux storage, auditability, no forced cloud dependency, Secure BOSS fit only. | "We are integrated with Secure BOSS or ISOC." |

## Key answers to rehearse verbatim

**Why not delete the obvious cache automatically?**

Because a cache convention is recovery evidence, not permission. SANCHAY proves
what it can, records it for review, and keeps irreversible authority with the
operator.

**Where is the AI?**

The AI capability is constrained decision intelligence: recoverability-aware
ranking, bounded target selection, and evidence-gated capacity risk. Optional
model narration cannot add candidates, change gates, or execute a cleanup.

**What data trained it?**

No external training dataset and no trained decision classifier. SANCHAY
analyzes local metadata at run time; demo data are synthetic and labelled.
Optional narration is separately opt-in and cannot change or execute a
decision.

**Why is this better than `du` or `ncdu`?**

Those tools are useful for locating visible paths. They do not establish
recoverability, and they cannot make a `df`/`du` disagreement a safe deletion
instruction. SANCHAY attaches a recovery basis, applies protected-path gates,
scopes a reclaim claim to one mount, and revalidates a plan before a human
acts. If reported use and readable inventory disagree, it reports an accounting
boundary--including visible deleted-open storage where available--rather than
inventing a reclaim target.

**Do you identify unused files?**

Only within a defensible recovery-evidence scope. SANCHAY does not call an
arbitrary old user file “unused”: Linux access time can be disabled or coarsened
by mount policy, and age does not establish user intent. It treats a narrow
regenerable cache/build path, a clean Git HEAD file, or byte-confirmed duplicate
as a review candidate; unchanged age is only a ranking factor after that gate.

**How do you know a duplicate is safe?**

We do not call it safe. We prove matching bytes and name a deterministic peer.
The operator still decides which copy to retain; a same-filesystem peer is not
presented as a backup.

**Can it scale?**

The scan avoids reading content until size collisions occur, uses a bounded
exact optimizer for normal same-risk classes, and records a deterministic
fallback above that bound. System-managed storage is deferred to its owning
tool rather than raw file deletion. The 29-candidate synthetic boundary proof
shows the fallback strategy and identical results after equivalent input order
is reversed; it is a determinism check, not a general performance benchmark.

**Why not show an exact full-disk date?**

One scan is not enough evidence. SANCHAY shows first-run orientation, then
withholds runway and capacity-risk claims until local snapshot, time-span, fit,
and capacity-stability gates have passed.

**Why is this relevant to Secure BOSS?**

C-DAC describes Secure BOSS for hardened critical endpoints, including
LVM-encrypted disks and standalone or intranet use. SANCHAY is a local,
review-only storage decision layer that fits that operating model. We do not
claim C-DAC integration, certification, deployment, or ISOC connectivity.

**Why does it not fix a full encrypted LVM volume automatically?**

Because changing a volume, mount, encryption state, or service lifecycle is an
availability and policy decision. SANCHAY only reads local storage state and
writes review artifacts; it deliberately does not resize LVM, remount a
filesystem, restart a service, or transmit an ISOC event. The platform owner
retains those actions after reviewing the evidence.

**Can it send a recommendation to ISOC?**

No ISOC integration is claimed. If an operator needs a handoff, SANCHAY can
write a local, checksum-bearing aggregate brief with counts and allocated bytes
by evidence class. It excludes paths, file names, process IDs/names, mount
sources, and content; it performs no network transmission. Any actual ISOC
interface, policy, approval, or delivery channel remains a C-DAC/operator
decision.

## Research-backed lines for Q&A only

Use these only when a jury member asks for rationale. Keep citations in speaker
notes or available locally; do not turn a slide into a literature review.

- Practitioners can usually find space with tools such as `ncdu`, but the harder
  question is what is safe to remove. SANCHAY addresses that decision gap with
  explicit recovery evidence rather than a larger-file list.
- A removed pathname can continue consuming space while a process keeps the
  file open. SANCHAY reports visible deleted-open storage as an advisory and
  never pretends it is a normal cleanup candidate.
- Filesystem-visible free space and a directory walk can disagree because of
  mounts, Btrfs shared extents, container layers, or access limitations. The
  product calls this an accounting boundary, not a fictional reclaim target.
- This is a practitioner failure mode, not a theoretical edge case: a
  [Linux-admin discussion of a full `df` but small `du` result](https://www.reddit.com/r/linuxadmin/comments/1ks0y98)
  includes deleted-open handles and mounted-over paths among the investigation
  routes; an older [Linux-admin thread](https://www.reddit.com/r/linuxadmin/comments/bkbexd/freeup_disk_space/)
  separately flags inode exhaustion and Btrfs. These are anecdotal reports,
  not population evidence or an automatic remediation recipe.
- A recent [Linux-admin discussion of filesystem shrinking](https://www.reddit.com/r/linuxadmin/comments/1tp568r/shrinking_filesystems_still_feels_way_too_painful/)
  illustrates the operational tradeoff: emergency growth can be easy while a
  later reduction may require data movement, downtime, and a service cutover.
  Treat it as anecdotal practitioner context, not a benchmark; it reinforces
  SANCHAY's choice not to autonomously manipulate capacity or volumes.
- Capacity research treats the useful question as risk within a horizon rather
  than a precise calendar date under a single simplistic growth line. SANCHAY
  borrows that local, explainable framing only after strict history gates pass;
  see Kumar and Chamness, [Stochastic Estimated Risk for Storage Capacity](https://arxiv.org/abs/1901.10552).

Source map: `sanchay/docs/FINAL_ROUND_RESEARCH.md` contains the direct C-DAC,
POSIX, Linux, Debian, Docker, Flatpak, OWASP, academic, and clearly labelled
Reddit links. Do not claim that an anecdotal Reddit report is population data.
`SSM_OFFICIAL_REQUIREMENTS_TRACE.md` maps the official storage-optimizer brief
to the proof and wording to use in a jury answer.

## Room and device checklist

- Use the team slot in the organizer email, not a guessed time.
- On the Linux presentation machine, run `bash SSM_LINUX_PREFLIGHT.sh
  /path/to/sanchay` from this folder before the final. It verifies the 110-test
  suite, disposable safety rehearsal, and synthetic capacity-risk gate without
  modifying the repository.
- Run the disposable fixture once before the presentation and keep its terminal
  output in scrollback.
- Use the exact final-runbook commands from a Linux/BOSS machine or a prepared
  Linux VM. Do not run the demo against a real personal or organizer system.
- Current local rehearsal evidence is Ubuntu 24.04.1 under terminal-only WSL2.
  It proves command behaviour, not an independent Linux desktop environment;
  prepare a Linux VM/live system for the final unless the organizer explicitly
  confirms that WSL is acceptable.
- The official guidelines require the final demonstration to run on an
  open-source-based OS. Do not present the live workflow from Windows.
- Disable unnecessary notifications; keep source, terminal, and plan file open.
- Do not rely on a cloud model, a deployment, or the public explanatory page.
- If the jury interrupts, skip slides and demonstrate the evidence gate and
  fail-closed verification immediately.
