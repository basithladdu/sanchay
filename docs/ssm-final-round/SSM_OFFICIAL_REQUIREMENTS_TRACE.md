# SANCHAY — official requirement-to-proof trace

Prepared for Team Zeros and Ones' Stage 2 technical presentation. This is a
rehearsal aid, not a change to the Stage 1 submission or a claim of organizer
approval.

## The requirement that controls the story

The official problem statement asks for a storage solution that analyzes file
usage patterns, identifies duplicate and unused files, predicts future storage
requirements, and gives intelligent cleanup and archival recommendations while
remaining safe and explainable.

Source: [C-DAC/SSM official guidelines, Annexure I](https://ssm.cdac.in/guidelines/view).

Linux access-time caveat: the [Linux kernel pathname-lookup documentation](https://www.kernel.org/doc/html/latest/filesystems/path-lookup.html)
describes `relatime` as generally limiting access-time updates on unchanged
files, and Linux mount options can also disable access-time updates. That is why
`atime` is not treated as proof of user intent.

SANCHAY should show exactly what it implements. Do not inflate “unused” into a
claim that it knows a user's intent or that it can infer human use from a single
filesystem timestamp.

| Official need | What SANCHAY demonstrably does | Evidence to show | Exact boundary to say aloud |
| --- | --- | --- | --- |
| Analyze file patterns | Performs a local, mount-scoped regular-file inventory; captures file identity, allocated bytes, link count, modification time, and accessible coverage. | One terminal scan plus the plan/report scope. | “The inventory is local and mount-scoped; unreadable paths are counted rather than silently treated as absent.” |
| File usage / stale evidence | Uses unchanged age from `mtime` only as a ranking factor after recovery evidence. It records `atime` but deliberately does **not** use it to claim a file was unused, because Linux mount policy can make access time misleading. | The decision trace's `unchanged_age` input and `sanchay/regret.py`. | “Unchanged is not unused. We use it as a weak ordering signal, never as deletion permission.” |
| Identify duplicates | Hashes colliding regular-file candidates and names a byte-confirmed peer; hardlink aliases are excluded because they do not free physical blocks. | Named duplicate peer and excluded hardlink in the disposable demo. | “A duplicate proves matching bytes, not which copy is authoritative or that either is a backup.” |
| Identify unused candidates | Identifies only narrow, recoverability-backed candidates: known regenerable cache/build paths, clean Git HEAD files, and byte-confirmed duplicates. | Recovery-evidence class in the plan. | “We do not label arbitrary old user files ‘unused’; unknown recovery remains protected.” |
| Predict future storage | Starts with a clearly directional first-scan orientation. It withholds an exhaustion date until three complete same-root/same-capacity local snapshots span at least 24 hours with sufficient fit. A separate capacity-risk estimate requires seven complete snapshots over seven days and unchanged capacity. | `--risk-prove` shows an assessed synthetic history, then a withheld result after a synthetic capacity resize. | “A forecast is conditional on local history. Weak evidence produces a withheld result, not fake certainty.” |
| Intelligent cleanup recommendation | Optimizes a requested reclaim target within eligible evidence, lowest recovery risk first. It uses an exact minimum-excess subset selection for up to 28 same-risk candidates and records the strategy. | The `600K` target trace and selected allocated bytes. | “The optimizer chooses what to put in a review plan, never what to delete.” |
| Archival recommendation | `--verify-archive` proves an operator-chosen retained copy is a separate inode with matching bytes and stable identity. It does not copy, move, or delete. | A source walkthrough of `sanchay/archive.py`; use only if asked unless a prepared fixture is available. | “It verifies archive evidence; it does not manufacture an archive or call a same-filesystem copy a backup.” |
| Safety and explainability | Fences credential/control and system-managed paths; writes an integrity-checked review plan; rechecks it before a separate human action; optional narration cannot change a decision. | The protected thesis, managed-store advisory, plan verification, and fail-closed mutation. | “Recovery evidence and the frozen decision trace are visible before any irreversible human action.” |

## The 70-second problem-statement answer

> The brief asks for duplicate and unused-file identification, storage
> prediction, and safe, explainable recommendations. SANCHAY handles those as
> separate evidence problems. It confirms duplicates byte-for-byte, excludes
> hardlinks that would not release blocks, and only treats narrow regenerable or
> Git-restorable material as review candidates. A file merely being old is not
> called unused: Linux timestamps do not establish user intent. For capacity it
> measures local mount usage over time and withholds forecasts when history is
> weak or capacity changes. The result is a review plan with its exact evidence
> and target-selection trace; it never executes cleanup.

## Answers to expect

**“You collect `atime`; why not use it to detect unused files?”**

`atime` can be disabled or coarsened by filesystem mount policy, and reading a
file for duplicate verification can itself affect it on some systems. SANCHAY
keeps it as observed metadata but bases recommendation ordering on stable
unchanged age plus recovery evidence. It never asserts “not accessed means safe
to remove.”

**“Then are you really meeting the unused-file requirement?”**

Yes, within a defensible scope: known regenerable cache/build paths, clean Git
files, and verified duplicate content are candidates with recovery evidence.
It refuses to turn arbitrary old personal data into an “unused” deletion target.
That is the safety distinction the brief explicitly requires.

**“Where is the AI rather than rules?”**

The core is an interpretable constrained decision model: recovery evidence,
physical reclaimable bytes, unchanged age, and a regret weight feed a target
optimizer. Capacity risk is a separate, evidence-gated probabilistic model.
Optional LLM narration is downstream and lacks both decision and execution
authority.

**“Why not automatically clean?”**

On a Secure BOSS-style critical endpoint, volume changes, service lifecycle,
retention, and cleanup authority belong to the platform policy. SANCHAY does
not resize LVM, remount filesystems, restart services, or transmit an ISOC
event. It gives the operator the evidence required for that separate decision.

## Minimum visible proof in a 15-minute slot

1. Show the official problem statement on slide one in paraphrase, not a long
   quotation.
2. Show the evidence gate before the optimizer: duplicate/cache/Git proof in;
   unique, credential, and managed OS state out.
3. Run the `600K` fixture. Point out the protected thesis, the named duplicate
   peer, the hardlink exclusion, and the selection trace.
4. Mutate only the disposable fixture and show `--verify-plan` fail closed.
5. If asked about prediction, show the withheld-after-resize result rather than
   a visually impressive but weak forecast.

## Do not say

- “We know which user files are unused.”
- “Old means safe to delete.”
- “A duplicate is a backup.”
- “We have deployed on or integrated with Secure BOSS or ISOC.”
- “The LLM decides what to remove.”
- “The risk number is a production capacity guarantee.”

## Source map at the pinned local commit

- `sanchay/scan.py` — mount-scoped scan and observed metadata.
- `sanchay/regret.py` — recovery classes and `mtime`-based unchanged-age
  boundary.
- `sanchay/dedup.py` — descriptor-rooted duplicate verification.
- `sanchay/plan.py` — review plan, decision trace, and bounded target
  selection.
- `sanchay/snapshot.py` — snapshot and capacity-risk evidence gates.
- `sanchay/archive.py` — retained-copy proof only.
- `sanchay/managed.py` — system-owned storage is advisory, not raw cleanup.

Fresh local evidence at commit `70b08e49583b7eb3ba2549672c71ab6f5c2f7db9`:
the Ubuntu preflight passed 110 tests (5 skipped), a disposable safety rehearsal,
and a capacity-risk gate rehearsal. This is local test evidence, not a
deployment or organizer acceptance claim.
