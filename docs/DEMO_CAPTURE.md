# Demo capture runbook — slides 8 and 9

Exact commands to produce the screenshots and the measured numbers for
**Implementation & Demonstration** and **Results, Impact & Scalability**, plus
what to put on each slide. Every output below is a real run against the bundled
fixture; rerun them and your own capture will match.

Run everything from the repository root on the machine you will present from.

---

## Setup (once, before the session)

```bash
rm -rf ~/sanchay-demo
python -m sanchay.demo ~/sanchay-demo
```

The builder refuses to write into a non-empty directory, so the `rm -rf` is what
lets you rebuild. It creates six entries: a duplicate ISO pair, a regenerable
bundle cache, a hardlink pair, and one unique document.

---

## Capture 1 — the whole safety proof, in one command

```bash
python -m sanchay.demo --prove
```

```
rehearsal fixture -> /tmp/sanchay-demo-4nxr34rk
protected unique -> documents/capstone-thesis.txt stayed out of the review plan
duplicate proof   -> downloads/boss-image-copy.iso matched archive/boss-image.iso as a named evidence peer
retention boundary -> matching bytes do not identify the authoritative copy
hardlink boundary -> 2 entries excluded
reclaim evidence  -> 729,088 bytes selected for review
target optimizer -> lower-risk candidates first; exact minimum-excess subset used for the remaining target
fail-closed check -> a synthetic cache mutation invalidated the plan
proof -> PASS; no file was deleted, moved, or transmitted
```

**This one screenshot already proves live-sequence steps 1 through 5.** It is the
strongest single image in the deck: nine lines, each an evidence boundary, ending
in a pass that names what was not done.

---

## Capture 2 — the selection trace

The lower-risk-first trace is printed by the **CLI**, not by the shell's
`/target`. Use this command when the slide promises a trace:

```bash
python -m sanchay.cli ~/sanchay-demo --target-reclaim 600K --limit 10 --plan ~/evidence/plan.json
```

```
6 file entries, 1.3MB allocated storage
1 hardlink aliases are not double-counted

duplicates: 1 groups, 512.0KB potential allocated reclaim
candidates: 2 shown, 2 eligible, 2 irreplaceable files excluded
hardlinks: 2 entries excluded; a single link removal releases no physical bytes
intent: reclaim 600.0KB; 712.0KB selected (target met)
  selection 1: regenerable output (regret 0.02); 200.0KB selected from 200.0KB eligible (all lower-risk candidates)
  selection 2: byte-confirmed alternate copy (regret 0.10); 512.0KB selected from 512.0KB eligible (exact minimum-excess subset)
  table below: deterministic review priority, not an execution order

   reclaim  kind        unchanged  path
------------------------------------------------------------------------------
   512.0KB  duplicate     120.1d  ~/sanchay-demo/downloads/boss-image-copy.iso
   200.0KB  disposable     44.9d  ~/sanchay-demo/workspace/node_modules/.cache/bundle.bin
```

The shell equivalent, `/target 600K`, prints only the one-line summary
`Target 600.0KB: 712.0KB selected (met).` — accurate, but not a trace.

---

## Capture 3 — fail-closed verification

```bash
python -m sanchay.cli --verify-plan ~/evidence/plan.json
printf 'x' >> ~/sanchay-demo/workspace/node_modules/.cache/bundle.bin
python -m sanchay.cli --verify-plan ~/evidence/plan.json
```

In the shell the same pair is `/plan review.json` then `/verify-plan review.json`:

```
Plan is valid for human review; 4 recommendations checked.
```

```
Plan is not valid for review; 4 recommendations checked.
```

Show both in one frame. The refusal happens *before* a human acts, which is the
whole argument.

---

## Capture 4 — the hybrid AI stage

```bash
sanchay
```

```
/ai status
/ai ollama qwen2.5-coder:7b
/scan ~/sanchay-demo
/candidates
/archives
```

`/ai status` on a machine with a local model:

```
Hybrid AI mode: ollama
  usage prediction: sanchay_local_action_classifier v1 (always local)
  Ollama: available; selected qwen2.5-coder:7b; installed qwen2.5-coder:7b, moondream:latest
  OpenAI-compatible API: not configured; API keys are never printed
  safety: reasoning may keep or confirm a review; it cannot delete, promote an unsafe file, or bypass human approval
```

**Rehearse this on the presentation machine.** With no Ollama service the same
command prints `Ollama: unavailable; <reason>` and the scan falls back to the
local classifier. That fallback is correct behaviour and safe to explain, but
decide in advance whether you want it on screen.

The two listings prove the cleanup/archive split visually: `capstone-thesis.txt`
appears in `/archives` and never in `/candidates`.

---

## Capture 5 — scale (optional, for slide 9)

```bash
sanchay
```

```
/analyze ~/Downloads
/ps
```

Use a real directory to show the tool outside a toy fixture. Label the capture
as a live run so it is never confused with the fixture measurements.

---

## Measured hybrid result (run 03 September 2026, fixture)

One real hybrid scan, `provider=ollama`, `model=qwen2.5-coder:7b`:

| Field | Value |
| --- | --- |
| status | `completed`, `applied: true` |
| candidates sent | 4 |
| reviewed | 4 |
| confirmed | 4 |
| changed to Keep | 0 |
| fallback | no |
| scan wall time | ~21 s |

Per-candidate agreement between the local classifier and the reasoning stage:

| File | Local action | Reasoning action | Confidence |
| --- | --- | --- | ---: |
| `downloads/boss-image-copy.iso` | cleanup_review | cleanup_review | 0.95 |
| `workspace/node_modules/.cache/bundle.bin` | cleanup_review | cleanup_review | 0.93 |
| `archive/boss-image.iso` | archive_review | archive_review | 0.76 |
| `documents/capstone-thesis.txt` | archive_review | archive_review | 0.81 |

**How to say "0 changed to Keep" without it sounding like the AI did nothing:**
the fixture contains four unambiguous cases, so agreement is the expected
result. The claim is not that the model corrects the classifier often; it is that
the model *can* downgrade a review to Keep and *cannot* promote anything into a
riskier class, and that every decision is recorded with its confidence. If it
disagreed, the deterministic gates would still own the permitted action set.

---

## What to put on slide 8

Keep the "what is built" paragraph — it is accurate: the base package requires
`prompt-toolkit`, with pandas/Plotly and Textual optional, and CI runs the suite
plus the rehearsal on Python 3.9 through 3.12 on every push and pull request.

Five corrections:

1. **Pick one surface for the live sequence.** Steps currently span three:
   `demo --prove` for 1–3, CLI flags for 4–5, shell commands for 6. Recommended
   split — Capture 1 proves steps 1–5 in a single frame, then the shell for the
   AI stage.
2. **Step 4's claim only matches the CLI.** `--target-reclaim 600K` prints the
   selection trace; the shell's `/target` does not. Either run the CLI for that
   step or reword the claim.
3. **Fix the proof box order.** The command comes first, then its output, and
   the output is a single line:

   ```
   $ python -m sanchay.demo --prove
   proof -> PASS; no file was deleted, moved, or transmitted
   ```

   As drawn, `proof -> PASS;` sits above the command and the rest below it,
   which contradicts "one real terminal capture, never a mockup" on the same
   slide.
4. **Match the screenshot to the claims.** The current capture is a `~/Downloads`
   scan; a juror looking for `capstone-thesis.txt` will not find it. Use
   Capture 1, or Capture 4's `/candidates` + `/archives` pair.
5. **Decide the Ollama step deliberately.** `FINAL_ROUND_RUNBOOK.md` rule 9 says
   not to make the local model part of the core demo; the content audit asks for
   `/ai status` and `/ai ollama qwen2.5-coder:7b` on this slide. Both cannot
   stand. Recommended: keep `/ai status` (it degrades gracefully and always
   prints the safety line) and treat the provider switch as optional, then
   update the runbook rule to match.

## What to put on slide 9

1. **Fill the placeholder line** with the measured run:

   > **Hybrid run (Ollama, qwen2.5-coder:7b):** 4 reviewed · 4 confirmed ·
   > 0 changed to Keep · fallback no.

2. **712.0 KB and 729,088 bytes are the same number** (712 × 1024). They are
   currently presented as two separate findings — a stat tile and a "reviewable
   total". Keep one, or write `712.0 KB (729,088 bytes)`.
3. **Add the live run beside the fixture.** Every figure on the slide comes from
   six files and 1.3 MB, which invites "does it scale?". Capture 5 answers it
   with a labelled second row: entries scanned, allocated storage, duplicate
   groups, potential reclaim, and elapsed time.
4. **Use the empty lower third.** The hashing pipeline and the per-mount note
   can move down and grow; the slide currently stops around two thirds of the
   way down.
