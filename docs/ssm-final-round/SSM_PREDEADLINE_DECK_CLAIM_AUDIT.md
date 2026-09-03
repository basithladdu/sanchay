# Pre-deadline deck claim audit — do not repeat unsafe claims

## Scope

This is a read-only review of `docs/SANCHAY.pptx` extracted from local Git commit
`d20920478f8b1f34077e74b286f8bdd75d749036` (24 August 2026,
20:03:42 +05:30). Its extracted SHA-256 is
`8dfce94529470c66c377f9448642974524779faaef8409320ba9f84c3b58c3b5`.

The commit is a plausible pre-deadline source snapshot, not proof that this
PPTX was the exact portal upload. Do not alter or replace any portal material
on the basis of this audit. Use it to avoid repeating claims that the current
implementation cannot prove.

## What the seven-slide deck says

The extracted text includes claims such as:

- “100% Zero Loss” and “Structural Zero-Deletion Guarantee.”
- “1-Scan Forecast,” “Days-until-full date without daemons,” and an “instant
  disk full date on run #1.”
- “100% test coverage.”
- “DPDP Act 2023 compliant.”
- “The LLM receives only files already verified as 100% regenerable.”
- An explicit track label that conflicts with the finalist e-mail/listing
  terminology.

These are not safe final-round claims. The final narrative must use the
evidence-first language in `SSM_FINAL_ROUND_DECK_COPY.md`,
`SSM_STAGE2_REHEARSAL_CARD.md`, and `SSM_OFFICIAL_REQUIREMENTS_TRACE.md`.

## What the same pre-deadline source snapshot proves

The isolated checkout at `d209204` is clean and its five discovered unit tests
pass under Ubuntu/Python 3.12. It is therefore a real historical snapshot, not
an empty slide package. But it does **not** justify the deck's inflated claims:

- `pyproject.toml` declares `textual>=1.0` as a required dependency, so “zero
  dependencies” does not describe the complete pre-deadline product.
- The source snapshot contains five discovered tests, not a coverage report or
  proof of “100% test coverage.”
- It does not expose `sanchay` through `python -m sanchay`; its documented CLI
  is a package entry point. Do not improvise a live command sequence from this
  snapshot without separately verifying the setup.

This is why the current final-run proof must never be represented as if it were
already present in the historical Stage 1 snapshot. If organisers request an
exact historical demonstration, use the portal-confirmed commit and build it
from that record only.

## Claim-by-claim replacement

| Do not show or say | Why it fails a technical challenge | Say this instead | Proof available live |
| --- | --- | --- | --- |
| “100% Zero Loss” / “guarantee” | SANCHAY cannot guarantee a later human's independent action, an operator's retention policy, storage durability, or absence of every defect. | “SANCHAY has no cleanup executor; unique and hardlinked entries are excluded before its review-plan ranking.” | `python3 -m sanchay.demo --prove` prints that no file was deleted, moved, or transmitted. |
| “1-Scan Forecast” / exact full-disk date | A single inventory cannot establish future net growth. The current model deliberately withholds a runway date until snapshot gates qualify. | “The first scan is directional orientation. Measured runway and capacity risk are withheld when the local history is weak.” | `python3 -m sanchay.demo --risk-prove` shows an assessed synthetic case, then a withheld result after a capacity resize. |
| “100% test coverage” | There is no current coverage artefact proving that percentage. | “The pinned rehearsal ran 110 tests, with five skips, plus two deterministic proof runs.” | `SSM_LINUX_PREFLIGHT.sh` output. |
| “DPDP compliant” | That is a legal/compliance conclusion, not a source-code feature claim. | “The local default workflow does not transmit file content; optional cloud narration requires explicit opt-in and sends only opaque metadata.” | `AI_TECHNICAL_DEFENSE.md`; targeted narrator tests. |
| “The LLM sees only 100% regenerable files” | The current source's optional narration boundary is broader and must be described precisely. “100%” is unjustified. | “Optional narration is downstream of the deterministic gate; it cannot add candidates, change a ranking, or execute cleanup.” | `sanchay/explain.py`; narrator-boundary tests. |
| “Track 1” or “Track 2” on the title slide | The published guideline uses Track 1 for application-level storage, while the finalist message/list labels it Track 2. The contradiction is organizer-owned. | Put only the problem statement: “AI-Powered Intelligent Storage Optimizer for Linux OS.” | `ORGANIZER_CLARIFICATION_DRAFT.md`. |
| “AI decides what is safe to delete” | It contradicts the design and creates an avoidable safety challenge. | “Interpretable, constrained storage decision intelligence; the operator retains irreversible authority.” | Review plan's evidence and target-selection trace. |

## Visual direction: reject the old hackathon-dashboard tone

The old deck's extracted copy is KPI-heavy and absolute: large numeric claims,
“guarantees,” and generic AI-versus-traditional-tool framing. It is exactly the
kind of surface that invites jury pushback rather than demonstrating mastery.

The final deck should be deliberately restrained:

- one claim per slide, backed by a terminal trace or a single architecture
  visual;
- no hero metrics, gauges, badges, fake telemetry, dashboard grids, gradients,
  “AI brain” imagery, or unsupported percentages;
- show failure/withholding as a strength: the mutated plan is rejected and a
  resized-capacity forecast is withheld;
- use the C-DAC operating model as context, never a logo-driven integration
  claim.

## What a jury should remember instead

> A full disk is not permission for AI to delete the largest file. SANCHAY
> proves a recovery route, records a reviewable decision, and fails closed when
> that evidence changes.

## Verification boundary

The present review is source/deck text evidence. Rendering of the extracted
PPTX was not available in this workspace because the slide renderer lacks its
image dependency and neither PowerPoint nor LibreOffice is installed. Do not
claim a pixel-level review of that old deck from this audit.
