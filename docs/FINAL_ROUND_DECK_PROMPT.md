# Final-round slide content — SANCHAY (11 slides)

Ready-to-paste copy for the organizer template `TEAM_NAME – TRACK_ID.pptx`,
one block per slide, in template order. The template's nine section titles are
fixed and already on the slides — everything under **Body** is what you type
into the empty area below each title.

Every number quoted here is real output from the deterministic fixture
(`python -m sanchay.demo --prove` and the `--target-reclaim 600K` run in
[`FINAL_ROUND_RUNBOOK.md`](FINAL_ROUND_RUNBOOK.md)). Do not round them up, and
do not generalize them into a performance claim.

**Two fields only you can fill:** the team leader's name and the full team
roster on slide 1, and the contact email on slide 11.

**Never on a visible slide:** Track 1; any guarantee of safety or recovery; an
exact full-disk date; legal or compliance claims; test-coverage percentages;
C-DAC endorsement, deployment, certification, or an ISOC API; any wording that
implies SANCHAY deletes or moves files on its own.

---

## Slide 1 — Title

Fill the bracketed fields:

| Field | Value |
| --- | --- |
| `TEAM NAME` (orange) | **Zeros and Ones** |
| `PROJECT TITLE` | SANCHAY — Evidence-first storage decisions for Linux |
| `TEAM LEADER / PARTICIPANT` | *(fill in)* |
| `TRACK` | Track 2 — AI at Application Level |
| `TEAM MEMBERS` | *(fill in)* |
| `PROBLEM STATEMENT` | AI-Powered Intelligent Storage Optimizer for Linux OS |

Delete the template's own line, "Replace all bracketed fields with your
project-specific information."

**Say (30 s):** SANCHAY is a local, review-first storage decision layer for
Linux. It recommends. It never deletes or moves a file on its own.

---

## Slide 2 — Problem Statement & Objective

**Claim line:** Size tells you what is big. It does not tell you what is safe to remove.

**Body — two columns, same size, opposite consequence:**

| Both are 2 GB | What removal costs |
| --- | --- |
| `node_modules/.cache` build output | Rebuilt by its own tool in minutes |
| The only copy of a thesis or a database export | Unrecoverable |

**Then, three lines:**
- Disk-usage explorers and duplicate finders rank **bytes**.
- A byte ranking never establishes that a specific file is eligible for review.
- When the disk fills, hurried users and automated cleaners delete the wrong 2 GB.

**Objective:** rank **recovery evidence** before anything is recommended, and
leave every irreversible step to a human.

**In scope:** local scan, typed evidence classification, review-only plans,
gated capacity evidence, path-free operator handoff.
**Out of scope:** autonomous deletion, uploading paths or file contents,
cross-mount capacity claims, guaranteed forecasts.

**Visual:** two equal blocks, identical size label, opposite outcome colour.

**Notes:** state the non-goals out loud — the boundary is the contribution.
`[Sources] README.md § Problem`.

---

## Slide 3 — Proposed Solution

**Claim line:** Regret-Aware Storage Intelligence — model the cost of recovery
before calculating priority.

**Body — the formula as the hero:**

```
Priority = reclaimable allocated bytes × unchanged-age × (1 − regret)
```

For an irreplaceable unique file regret is **1.00**, so priority is **0.0** and
it never enters the plan.

**Four evidence classes:**

| Evidence class | Regret | Review boundary |
| --- | ---: | --- |
| Regenerable cache or build output | 0.02 | Review through its owning tool |
| Byte-confirmed duplicate | 0.10 | A named evidence peer remains; a human selects retention |
| Clean Git HEAD file | 0.20 | Confirm the project owner accepts removal |
| Unique or otherwise unproven | 1.00 | **Excluded before ranking** |

SANCHAY counts **allocated** bytes where the platform exposes them. A hardlink
is not a reclaimable duplicate — removing one directory entry releases no
physical storage.

**Visual:** the formula at callout size; the 1.00 row separated below a rule.

**Notes:** regret is the cost of recovery, not a confidence score.

---

## Slide 4 — System Architecture

**Claim line:** Recovery evidence is a gate, not a score.

**Body — the pipeline:**

```
local scan → recovery evidence → protected-file gate → review-only plan → human decision
```

**Three routes admitted through the gate:** byte-confirmed duplicate; clean
Git HEAD; narrow regenerable cache or build-output path.

**Excluded before ranking:** unique, untracked, uncached, credential and
control files, managed OS state, hardlinked entries.

**Four outputs, each a checkable artifact:**

| Artifact | What it proves | What it is not |
| --- | --- | --- |
| Review plan (JSON + SHA-256) | Typed evidence per candidate; accidental change detected | Not a digital signature |
| Mount snapshot (write-once) | Observed mount total/used/free | Not device attestation |
| Path-free operator brief | Aggregates for review | No roots, paths, names, PIDs, or content |
| HTML treemap / Textual dashboard | Where the storage actually sits | Not an execution queue |

**Visual:** single-row flow with the gate drawn as a gate, and a dashed
"excluded" path leaving it downward.

**Notes:** nothing crosses the gate without a typed evidence record.

---

## Slide 5 — AI & Technical Approach

**Claim line:** The decision layer is explainable and evidence-bounded — and it
explains, it never decides.

**Body — three stages:**

1. **Recoverability scoring** from typed evidence, not from filename heuristics.
2. **Constrained target selection.** For a same-risk class of up to 28
   candidates, a bounded exact subset search minimizes excess; a larger class
   records a deterministic greedy fallback inside the plan. It never expands
   into protected files to meet a target.
3. **Local observed-growth models** with hard withholding gates (slide 6).

**Real trace — `--target-reclaim 600K` on the fixture:**

```
intent: reclaim 600.0KB; 712.0KB selected (target met)
  selection 1: regenerable output (regret 0.02); 200.0KB from 200.0KB eligible
  selection 2: byte-confirmed alternate copy (regret 0.10); 512.0KB, exact minimum-excess subset
  table below: deterministic review priority, not an execution order
```

**The language model's boundary.** Narration is separately opt-in — a
deterministic local narrative by default, optionally a cloud model, or a
loopback Ollama model for standalone Linux. It receives **opaque IDs plus fixed
class, size, and age metadata only**. It cannot add a candidate, reorder a
safety gate, or execute an action.

**Visual:** the trace as a real terminal capture; a one-way arrow from plan to
narrator with a blocked return arrow.

**Notes:** this answers "where is the AI?" — say it before the jury asks.

---

## Slide 6 — Innovation & Novelty

**Claim line:** Withholding a recommendation is a feature, not a gap.

**Body — three novelties:**

1. **Regret as a first-class ranking term.** Consequence, not consumption,
   decides priority.
2. **The named evidence peer.** A duplicate is admitted only with a
   deterministic byte-matched peer a human can recheck independently:
   `same size → 64 KB prefix → BLAKE2b-256 → byte-for-byte confirmation → named peer → identity recheck`.
   A match never identifies the authoritative copy and never proves a backup.
3. **Forecasts that refuse false precision.** Runway needs the same root and
   device, ≥ 24 h of history, ≥ 3 snapshots, and R² ≥ 0.80. Capacity risk needs
   7 complete same-capacity snapshots across 7 days. Below that, SANCHAY shows
   nothing.

**How that differs from what exists:**

| | Disk explorers (ncdu, baobab) | Duplicate finders (fdupes) | Cleaners (BleachBit) | **SANCHAY** |
| --- | --- | --- | --- | --- |
| Ranks | Bytes | Byte matches | Known rules | **Recovery evidence** |
| When unsure | Shows it anyway | Shows it anyway | Applies the rule | **Withholds it** |
| Decides | User | User | Tool | **Human, on evidence** |

**Visual:** a four-rung evidence ladder with the top rung greyed out and
labelled *withheld — evidence insufficient*.

**Notes:** name the other tools fairly — they answer a different question.

---

## Slide 7 — Security & Safety

**Claim line:** Fail-closed by default.

**Body — the action gate, in order:**

```
actions disabled by default → temporary permission → explicit execution
→ exact confirmation → fresh evidence recheck → one guarded action
```

Any link that fails stops the chain. In the rehearsal, one synthetic cache
mutation invalidated the plan and `--verify-plan` failed closed.

**Four containment boundaries:**
- Local core; the core workflow transmits no file contents.
- One filesystem by default; no shared capacity claim across mounts.
- APT, journal, Docker, containerd, Flatpak, boot, config, and service state
  stay **tool-owned advisories**, never raw file-deletion candidates.
- The operator brief is path-free — no roots, paths, names, PIDs, mount
  sources, or content leaves the machine.

**Fit:** this local, constrained workflow is **designed to fit** a sovereign
secure Linux operating model for critical endpoints on intranet or standalone
deployment.

**Visual:** the chain with a fail-closed exit drawn at every link; a boundary
diagram with everything outside labelled *not transmitted*.

**Notes:** say *fit*, never endorsement, certification, or deployment.
`[Sources] docs/CDAC_SECURE_BOSS_FIT.md`.

---

## Slide 8 — Implementation & Demonstration

**Claim line:** Dependency-light core, and a proof that is controlled and repeatable.

**Body — what is built:** a Python core with no required third-party
dependency; an interactive `sanchay` shell with a slash-command palette and
background scan jobs; optional Textual dashboard and self-contained Plotly HTML
report; GitHub Actions CI running the full suite plus the final-round rehearsal
on every push.

**The live sequence, in this order:**

1. `documents/capstone-thesis.txt` — a unique file — is **absent** from the plan.
2. `downloads/boss-image-copy.iso` appears only with `archive/boss-image.iso`
   named as its byte-confirmed evidence peer.
3. `hardlinks/source.bin` and `hardlinks/alias.bin` — 2 entries excluded; one
   unlink releases no physical bytes.
4. `--target-reclaim 600K` prints the lower-risk-first selection trace; the
   table is labelled review priority, **not** execution order.
5. `--verify-plan` passes, then **fails closed** after one synthetic cache
   mutation.

**Rehearsal output:**

```
proof -> PASS; no file was deleted, moved, or transmitted
```

**Visual:** one real terminal capture from the fixture — never a mockup.

**Notes:** `python -m sanchay.demo --prove` from the repository root; disposable
fixture only. Do not attempt to demonstrate cleanup — there is no cleanup
executor, and that is the argument.

---

## Slide 9 — Results, Impact & Scalability

**Claim line:** Measured on the deterministic fixture — every number bounded by
evidence.

**Body — the fixture result:**

| Measure | Value |
| --- | --- |
| Scanned | 6 file entries, 1.3 MB allocated |
| Duplicate evidence | 1 group, 512.0 KB potential allocated reclaim |
| Candidates | 2 eligible, **2 irreplaceable files excluded** |
| Hardlinks | 2 entries excluded, 1 alias not double-counted |
| Target 600.0 KB | 712.0 KB selected, target met, 0 protected files touched |
| Reviewable total | 729,088 bytes |

**Impact:** the operator sees why each candidate is eligible, and the files that
matter are gone from the list before a human ever scrolls it.

**Scalability — by boundary, not by cluster:**
- Tiered hashing puts the expensive stage on the smallest set: size → 64 KB
  prefix → BLAKE2b-256 → byte compare.
- Per-mount accounting keeps capacity claims honest at any volume count.
- Snapshot history is local and operator-chosen — no scheduler, service, or
  network call.

**Visual:** three or four large stat callouts with small captions; the hashing
funnel showing survivors per stage.

**Notes:** every figure is fixture-measured. Never generalize it.

---

## Slide 10 — Future Scope & Conclusion

**Claim line:** The roadmap extends evidence, never authority.

**Body — proposed, not implemented:**
- Additional typed evidence classes, each shipped with a published review boundary.
- Packaging for BOSS-family distributions.
- Multi-host aggregation of path-free briefs for a fleet view.
- Operator-tunable regret weights, with the plan recording the weights used.

**Conclusion, set large:**

> **SANCHAY does not ask users to trust a cleanup model. It gives them evidence
> to review before an irreversible step.**

Footer line: *Recommendations only. No automatic deletion or file movement.*

**Visual:** whitespace, one small evidence-chain mark. Nothing else.

**Notes:** be explicit that the roadmap is proposed. Land the closing line, then
stop talking.

---

## Slide 11 — Thank you

- `GitHub: https://github.com/basithladdu/sanchay`
- `Contact: ` *(fill in)*

A QR code only if it has been tested from the presentation machine.

---

## Speaker-note sources

Attach a `[Sources]` block to the notes of every slide making an external claim:

- C-DAC BOSS / Secure BOSS facts → `docs/FINAL_ROUND_RESEARCH.md`, `docs/CDAC_SECURE_BOSS_FIT.md`
- Storage redundancy and forecasting evidence → `docs/FINAL_ROUND_RESEARCH.md`
- Implementation claims → `sanchay/plan.py`, `sanchay/dedup.py`, `sanchay/managed.py`,
  `sanchay/snapshot.py`, `sanchay/demo.py`, and the test suite
- Spoken positioning and hostile Q&A → `docs/FINAL_ROUND_JURY_BRIEF.md` (notes only, never on a slide)
