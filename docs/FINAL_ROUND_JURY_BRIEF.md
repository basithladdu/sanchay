# SANCHAY: C-DAC final-round jury brief

Use this as the speaking brief beside the eight-slide deck. It translates
documented C-DAC Secure BOSS / Secure OS context into claims the team can prove
in the repository. It is **not** a claim that C-DAC has deployed, endorsed, or
specified SANCHAY.

## The 30-second opening

> A full disk is not a request to delete the largest file. On a hardened Linux
> endpoint, the costly mistake is removing the only copy, managed OS state, or
> evidence needed for recovery. SANCHAY is a local storage decision layer: it
> ranks only files with explicit recovery evidence, produces a reviewable plan,
> and verifies that plan again before a human performs any separate cleanup.

Then demonstrate it. Do not lead with an AI buzzword or a dashboard.

## What the C-DAC context makes relevant

| Documented context | SANCHAY response the team can prove | Show this |
| --- | --- | --- |
| Secure BOSS is described for critical end nodes, with hardening, logging, monitoring, alerts, and intranet/standalone or ISOC-monitored use cases. | Local core, no autonomous cleanup, no daemon, no required network call, guarded interactive actions, and an aggregate-only optional operator brief. | Slide 7, then `--operator-brief` only if asked. |
| Secure BOSS is described as installed on an LVM-encrypted disk. | It scopes capacity to the visible mount and labels device-mapper, Btrfs, overlay, reserved-block, inode, and accounting boundaries instead of inventing volume-pool headroom. | `--capacity-audit` explanation; do not run LVM commands. |
| C-DAC's Secure OS tender treats local/distributed/secure storage, fault tolerance, redundancy, disaster recovery, AI/ML integration, autonomous management, and observability as relevant areas. | SANCHAY separates recoverable evidence from managed/system state, preserves duplicate evidence, measures snapshot history locally, and withholds weak forecasts. | Slides 3, 5, and the fail-closed proof. |
| The tender asks domain experts to propose measurable KPIs, test frameworks, and validated PoCs rather than prescribing numeric storage benchmarks. | The repository contains a deterministic fixture, exact-target proof, checksum/identity verification, synthetic risk-gate proof, and automated tests. | `python -m sanchay.demo --prove`; test output; `--verify-plan`. |

Sources: [C-DAC Secure BOSS Linux](https://www.cdac.in/index.aspx?id=product_details&productId=SecureBOSSLinux), [C-DAC Secure OS tender, pp. 35-36](https://www.cdac.in/index.aspx?dynamicId=NjY2MTA5MjE%3D&id=tenders_viewpdf). The tender is context, not the hackathon rubric.

## The product thesis to repeat

**SANCHAY optimizes reclaim only after recovery evidence has made a candidate
eligible.**

That distinction matters more than a generic storage graph:

1. A large, unique file has no recovery proof, so it stays outside cleanup; an
   old preservation-oriented file may appear only in separate archive review.
2. A clean build/cache output or byte-confirmed duplicate can enter a
   human-review plan; a file action requires explicit guarded operator intent.
3. APT, journal, container, Flatpak, boot, configuration, package, log,
   backup, credential, and service paths remain tool-owned or protected
   boundaries.
4. The plan records its recovery evidence, candidate identity, selected bytes,
   decision trace, and SHA-256 integrity checksum. Plan output is write-once
   unless an operator explicitly requests replacement; verification fails
   closed if the fixture changes.

## Why the AI is credible rather than decorative

Say this precisely:

> SANCHAY runs a local three-class logistic-regression model in the real
> recommendation path. It learns Keep, Cleanup Review, and Archive Review from
> a disclosed synthetic expert-labelled seed set and records probabilities and
> feature contributions. Deterministic recovery rules still hold every action
> gate, so the model receives recommendation influence but no cleanup authority.

The research rationale is strong: storage behaviour can be non-linear and
discontinuous, so a single exact "full on Tuesday" prediction is unreliable.
Kumar and Chamness instead frame capacity management as the probability of
reaching capacity within a stated horizon. SANCHAY adopts that *risk framing*,
but withholds it unless its local same-mount history passes stricter product
gates. It does not claim their production accuracy or a Secure BOSS validation.

Source: [Kumar and Chamness, *Stochastic Estimated Risk for Storage Capacity*](https://arxiv.org/abs/1901.10552).

## The proof sequence that wins credibility

| Moment | What the jury should infer | Exact proof |
| --- | --- | --- |
| Unique thesis absent from cleanup | Size is not mistaken for safety. | `documents/capstone-thesis.txt` cannot appear in cleanup; any model suggestion is archive-review only. |
| Duplicate names its evidence peer | A recommendation has a specific recovery basis. | `downloads/boss-image-copy.iso` byte-matches `archive/boss-image.iso`; retention is still human-selected. |
| Hardlink excluded | SANCHAY understands physical allocation, not merely file names. | The aliases share one `(device, inode)` and one unlink would free zero bytes. |
| 600K target is met inside eligible evidence | Optimization never broadens scope into unique/protected files. | First select the low-risk cache; then use a bounded exact choice within the remaining eligible class. |
| Verification passes, then fixture changes | The plan is not a stale recommendation. | `--verify-plan` succeeds, then rejects the altered synthetic cache with non-zero status. |
| Weak history yields no precise forecast | The product refuses fake precision. | First scan is labelled orientation; runway/risk are withheld until their snapshot gates qualify. |

Use the exact commands in [`FINAL_ROUND_RUNBOOK.md`](FINAL_ROUND_RUNBOOK.md).

## High-pressure answers

**"Why not automate the obvious cleanup?"**  Because matching bytes and a
cache convention do not establish business ownership, retention policy, or
operator intent. SANCHAY proves what it can and leaves irreversible authority
where it belongs.

**"Why is this better than `du`, `ncdu`, or a cleanup script?"**  Those tools
locate bytes. SANCHAY combines mount-scoped capacity context with typed
recovery evidence, protected-path gates, deterministic target selection, and
post-plan identity/content revalidation. It does not replace those tools; it
adds a decision boundary before cleanup.

**"What happens when `df` and the scan disagree?"**  The result is an
accounting gap, not a fake candidate list. SANCHAY reports visible
deleted-open bytes and filesystem/topology boundaries as advisories, then does
not kill processes, unmount paths, alter snapshots, or run filesystem tools.

**"Where is the AI?"**  Stage 1 is the local learned classifier that directly
selects and ranks Keep, Cleanup Review, and Archive Review from metadata and
positive usage evidence. Stage 2 is an optional constrained Ollama or
OpenAI-compatible model that reviews only prefiltered candidates and returns a
structured action, confidence, reason codes, and explanation. The plan records
both stages. The 38-row set is synthetic bootstrap data, not a production-
accuracy claim. Deterministic gates and human approval retain cleanup authority.

**"Does this integrate with Secure BOSS or ISOC?"**  No integration is
claimed. It is a fit: local execution, no required cloud dependency,
path-free aggregate handoff, mount-aware accounting, and a human-controlled
workflow suit the documented environment. An actual integration would require
C-DAC's interface, policy, security review, and deployment evidence.

## Claims that lose credibility

- "SANCHAY automatically frees space." It does not.
- "A duplicate is definitely a backup." Same-content files can still be the
  wrong copy or share the same failure domain.
- "The forecast tells the exact full-disk date." It deliberately withholds a
  runway or probability when the evidence gate fails.
- "C-DAC integrated, certified, endorsed, or will deploy SANCHAY." No evidence
  supports this.
- "The C-DAC tender is the hackathon scoring rubric." It is only product
  context.

## One-line close

> SANCHAY does not ask a secure endpoint to trust an AI with deletion; it gives
> the operator verifiable evidence before an irreversible decision.
