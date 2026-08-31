# Final-round slide content — replace the pre-selection draft

docs/SANCHAY.pptx is a pre-selection draft and must not be used unchanged.
It contains incorrect Track 1, guarantee, exact-forecast, legal-compliance, and
test-coverage claims. Preserve it as history; transfer the content below into
the organizer's PPT template when it arrives.

## Slide 1 — SANCHAY

**Evidence-led storage recommendations for Linux**

- Team Zeros and Ones
- Track 2 — AI at Application Level
- AI-Powered Intelligent Storage Optimizer for Linux OS

Footer: “Recommendations only. No automatic deletion or file movement.”

## Slide 2 — The real problem is recoverability, not size

Two files can be the same size and have radically different consequences:

- a regenerable build cache;
- the only copy of a thesis, database export, or document.

Most disk views can show what is large. SANCHAY asks what evidence exists that
the file can be reconstructed, and preserves the human decision for anything
irreversible.

## Slide 3 — Protected-file gate before ranking

Use one simple left-to-right flow:

local scan → duplicate content match / clean-Git state / cache-path heuristic → protected-file gate
→ review-only plan → human review

Headline: “Unique, untracked, uncached files are excluded from the plan before
priority ranking.”

Call out that the optional LLM narrates an already fenced list. It cannot add a
file, alter an order, or execute an action.

## Slide 4 — Duplicate recommendations need a surviving source

Show the actual proof chain:

same size → same 64 KB prefix → same full BLAKE2b-256 digest → byte-for-byte
confirmation → named survivor → identity recheck

Three claims only:

- hardlinks share a (device, inode) identity and are not reclaimable copies;
- every duplicate recommendation names its retained survivor;
- revalidation rechecks both files and their matching contents.

## Slide 5 — Honest capacity intelligence

Show two stages, not a fake exact date:

1. An initial mtime-based estimate gives immediate orientation.
2. Aggregate local snapshots train an explainable linear trend that reports
   bytes/day and, from the third snapshot onward, R-squared fit quality.

Footer: “A first scan is an estimate; observed history is stronger evidence.”

## Slide 6 — Live proof, not an uncontrolled machine demo

Use the deterministic SANCHAY fixture and terminal output:

- a unique capstone-thesis.txt is absent from the plan;
- a duplicate has a named survivor;
- a hardlink is excluded from reclaimable duplicates;
- a build cache is reviewable, not deleted;
- --verify-plan passes before change and fails closed after a synthetic fixture
  change.

Put the command in small monospace text only:

    sanchay-demo /tmp/sanchay-demo && sanchay /tmp/sanchay-demo --plan cleanup-plan.json && sanchay --verify-plan cleanup-plan.json

## Slide 7 — Fit for a secure, sovereign Linux workflow

- Local core workflow; no file contents transmitted.
- One filesystem by default; cross-filesystem traversal is explicit.
- Dependency-free Python core; TUI, plots, and narrative are optional.
- Inspectable JSON manifest with SHA-256 integrity checksum (not a signature)
  and observed identity.

Phrase this as a product fit inferred from C-DAC's Secure OS context, not a
claim of C-DAC endorsement or scoring criteria.

## Slide 8 — Closing

**SANCHAY does not ask users to trust a cleanup model. It gives them evidence
to review before any irreversible action.**

Keep the final slide sparse: team name, repository, and one QR code only if it
has been independently tested from the presentation device.

## Source-note handoff for the final deck

- C-DAC BOSS/FOSS context: docs/FINAL_ROUND_RESEARCH.md.
- C-DAC Secure OS tender context: docs/FINAL_ROUND_RESEARCH.md; label as
  context, not hackathon rules.
- Storage redundancy and forecasting research: docs/FINAL_ROUND_RESEARCH.md.
- Implementation claims: sanchay/plan.py, sanchay/dedup.py,
  sanchay/snapshot.py, and the verified test suite.
