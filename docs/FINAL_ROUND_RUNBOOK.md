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
2. From the repository root, run `python -m pip install -e .`.
3. For the terminal dashboard only, run `python -m pip install -e ".[tui]"`.
4. Run `python -m unittest discover tests` and keep the passing output in the
   terminal scrollback.
5. Open the public page only as a seeded explanatory walkthrough. State that it
   does not scan the visitor's filesystem.

## Exact live-demo sequence

```bash
DEMO_ROOT="$(mktemp -d /tmp/sanchay-demo.XXXXXX)"
sanchay-demo "$DEMO_ROOT"

sanchay "$DEMO_ROOT" --limit 10 --plan cleanup-plan.json --snapshot baseline.json
python -m json.tool cleanup-plan.json | less
sanchay --verify-plan cleanup-plan.json
```

Point out these concrete facts, not a generic dashboard:

- `documents/capstone-thesis.txt` is a deliberately unique fixture and is not
  in the plan.
- `downloads/boss-image-copy.iso` is a duplicate candidate only because
  `archive/boss-image.iso` is explicitly named as its retained survivor.
- `hardlinks/source.bin` and `hardlinks/alias.bin` are not reclaimable
  duplicates because they share one `(device, inode)` identity.
- `workspace/node_modules/.cache/bundle.bin` is a reviewable regenerable-output
  candidate, not an automatically deleted file.
- `cleanup-plan.json` has a SHA-256 integrity checksum (not a signature),
  candidate identity, typed recovery evidence, and a human-review requirement.

## Fail-closed proof

Change only the disposable fixture, then recheck the original plan:

```bash
printf 'fixture changed\n' >> "$DEMO_ROOT/workspace/node_modules/.cache/bundle.bin"
sanchay --verify-plan cleanup-plan.json
```

Expected result: verification reports that the candidate identity changed and
exits non-zero. It does not delete, move, or alter any file. This is the most
important fail-closed evidence in the live demonstration.

## Concise jury answers

**Where is the AI?** The decision layer is intentionally explainable: a
recoverability model ranks eligible candidates and a local linear trend learns
bytes/day from aggregate snapshots. The optional LLM only narrates an already
fenced candidate list and cannot promote protected files or execute actions.

**Why not automate deletion?** The requested problem includes recommendations;
the irreversible step has a different risk profile. SANCHAY supplies an
auditable plan and revalidation gate so an operator retains authority.

**How do you prove a duplicate is eligible for review?** It uses size bucketing,
prefix hashing, then a full BLAKE2b-256 digest and a byte-for-byte comparison;
the plan names the survivor and verification rechecks both identities and
matching content. Hardlinks are not counted as reclaimable copies.

**How reliable is the forecast?** A single scan is labelled as an mtime-based
estimate. Later aggregate snapshots produce a local linear trend with an
explicit slope and, from three observations onward, R-squared, rather than an
invented exact full-disk date.

**Why does this fit a sovereign secure OS?** The core is inspectable,
dependency-light, local by default, and stays on one filesystem unless the
operator explicitly opts into crossing that boundary. No file content leaves
the machine through the core workflow.

## What not to claim

- Do not call a first-scan forecast an exact date.
- Do not call the seeded web page a real device scan.
- Do not say SANCHAY deletes files, prevents every possible loss, or is legally
  certified for DPDP compliance.
- Do not say C-DAC has endorsed SANCHAY or that its tender defines hackathon
  scoring.
