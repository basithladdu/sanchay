# SANCHAY live demonstration — stage script

Every keystroke, in order, with what to say while it runs and the output you
should see. Core demo runs **3 to 4 minutes**. An extended set at the end covers
whatever the jury asks for.

All output below is real, captured from the bundled fixture.

---

## Before you start

**Two terminals.** Terminal A runs SANCHAY. Terminal B stays at a plain shell —
you need it once, to change a file while SANCHAY is watching.

```bash
# both terminals: same directory
cd ~/sanchay

# terminal A only: build the fixture
rm -rf ~/sanchay-demo
python -m sanchay.demo ~/sanchay-demo
```

Font size 18+, dark background, terminal maximised. Then launch:

```bash
sanchay
```

Press Enter past the splash screen. Leave it sitting at `sanchay>`.

**What the fixture holds** — know this cold, because every claim points at it:

| File | Why it is there |
| --- | --- |
| `documents/capstone-thesis.txt` | Unique. Must never appear in cleanup. |
| `archive/boss-image.iso` + `downloads/boss-image-copy.iso` | Byte-identical pair. |
| `workspace/node_modules/.cache/bundle.bin` | Regenerable cache. |
| `hardlinks/source.bin` + `alias.bin` | One physical file, two names. |

---

## Step 1 — Show where the AI is (20s)

```
/ai status
```

```
Hybrid AI mode: auto
  usage prediction: sanchay_local_action_classifier v1 (always local)
  Ollama: available; selected qwen2.5-coder:7b; installed qwen2.5-coder:7b, moondream:latest
  OpenAI-compatible API: not configured; API keys are never printed
  safety: reasoning may keep or confirm a review; it cannot delete, promote an unsafe file, or bypass human approval
```

> Before I scan anything — this is the AI. Stage one is a local classifier that
> always runs. Stage two is an optional local model, here Qwen 2.5 running
> through Ollama on this machine. No API key, nothing leaves the laptop.
>
> Read the last line. The reasoning model may keep or confirm a review. It
> cannot delete, cannot promote an unsafe file, cannot bypass approval.

*If it says `Ollama: unavailable`* — keep going and say: "The reasoning stage is
optional; it falls back to the local classifier and records why. You will see
that recorded in the plan."

## Step 2 — Scan (30s)

```
/scan ~/sanchay-demo
```

The prompt returns immediately and an animated `Working` strip reports progress.

> Notice the prompt came straight back. Scans run in the background — on a real
> filesystem this takes minutes, and you can keep working. Esc interrupts it.

Then the result:

```
Scan complete: ~/sanchay-demo
  6 entries; 1.3MB allocated storage
  1 duplicate groups; 512.0KB potential reclaim
  2 reviewable; 2 archive reviews; 2 unique files protected from cleanup
  reasoning AI: ollama qwen2.5-coder:7b
  coverage: complete
```

> Six files. One duplicate group. And the line that matters — **two unique files
> protected from cleanup**. They were excluded before ranking, not filtered out
> afterwards.

## Step 3 — The cleanup list (30s)

```
/candidates
```

```
Candidates from active scan: ~/sanchay-demo
 #  reclaim   kind         AI clean  unchanged  relative path
------------------------------------------------------------------------------------------
 1   512.0KB  duplicate       95%     120.1d  downloads/boss-image-copy.iso
 2   200.0KB  disposable      93%      44.9d  workspace/node_modules/.cache/bundle.bin
```

> Two candidates. A byte-confirmed duplicate and a build cache.
>
> Now look at what is **not** here. The thesis file is not in this list. Neither
> is the hardlink alias. This is a review list, ranked by priority — not an
> execution order.

**This is the moment the demo is built around. Do not rush it.**

## Step 4 — Where the protected file went (25s)

```
/archives
```

```
AI archive reviews from active scan: ~/sanchay-demo
 #  allocated  confidence  unchanged  relative path
------------------------------------------------------------------------------------------
 1    512.0KB        76%     120.1d  archive/boss-image.iso
 2      41.0B        81%     300.0d  documents/capstone-thesis.txt
Archive is a recommendation only: choose a destination, copy separately, then verify it with /verify-archive.
```

> There is the thesis. Untouched for 300 days, so the model suggests you may
> want to archive it — but archive is a *separate list* with a different
> boundary. A unique file can be suggested for archive. It can never be
> suggested for cleanup.

## Step 5 — Why the duplicate is safe to review (25s)

```
/duplicates
```

```
Duplicates from active scan: ~/sanchay-demo
1 groups; 512.0KB potential allocated reclaim.
1. 2 physical copies; about 512.0KB reviewable
     archive/boss-image.iso
     downloads/boss-image-copy.iso
Every duplicate recommendation is byte-confirmed again when its plan is built.
```

> Two physical copies — and note it says physical. The hardlink pair is not
> here, because unlinking one name frees zero bytes.
>
> We do not stop at a hash. Same size, then a 64 KB prefix, then BLAKE2b, then a
> full byte-for-byte compare. And it is confirmed again when the plan is built.

## Step 6 — Ask it for a specific amount (30s)

```
/target 600K
```

```
Target 600.0KB: 712.0KB selected (met).
Run /candidates to review the selection before any action.
```

> I asked for 600 KB. It found 712 and told me the target is met.
>
> The order matters: it takes the regenerable cache first — regret 0.02 — and
> only then the duplicate at 0.10. Lowest consequence first. And it will never
> reach into the protected files to hit a number. Ask for 9 GB and it says
> "short by" rather than touching the thesis.

*Optional, if you want to prove that:* `/target 9G` →
`Target 9.0GB: 712.0KB selected (short by 9.0GB).` Then `/target clear`.

## Step 7 — Write the evidence (25s)

```
/plan review.json
```

```
Review plan created: ~/sanchay/review.json
```

```
/verify-plan review.json
```

```
Plan is valid for human review; 4 recommendations checked.
```

> The plan is JSON with typed evidence for every candidate and a SHA-256
> checksum. It records the model version, the probabilities, and the training
> data checksum — so a reviewer can audit the recommendation, not just accept it.

## Step 8 — Fail closed (35s) — the strongest moment

**Switch to terminal B** and change one byte of a file the plan recorded:

```bash
printf 'x' >> ~/sanchay-demo/workspace/node_modules/.cache/bundle.bin
```

> While we were talking, something on disk changed. That happens constantly on a
> live machine.

**Back to terminal A:**

```
/verify-plan review.json
```

```
Plan is not valid for review; 4 recommendations checked.
```

> The plan is refused. Not a warning — refused, **before** a human acts on it.
> Evidence that is stale is not evidence.

## Step 9 — The action gate (30s)

```
/permissions status
```

```
File actions are disabled.
Enable for one action command with: /permissions enable I_UNDERSTAND_FILE_ACTIONS
```

```
/refresh
/delete 1
```

```
PREVIEW only: permanently delete candidate 1, 512.0KB duplicate: downloads/boss-image-copy.iso
To execute: authorize actions, then rerun with --execute --confirm DELETE:1
Duplicate retention confirmation required: --retain "~/sanchay-demo/archive/boss-image.iso"
```

> This is what deleting looks like. A preview.
>
> To actually run it I need four more things: one-use permission, an explicit
> `--execute`, an exact confirmation token, and — because this is a duplicate —
> I must name which copy survives. The tool refuses to choose that for me.
>
> I am not going to run it. There is no automatic executor in this product.

**Do not execute a delete on stage.** The preview is the argument.

## Step 10 — Close with the rehearsal (20s)

**Terminal B:**

```bash
python -m sanchay.demo --prove
```

```
protected unique -> documents/capstone-thesis.txt stayed out of the review plan
duplicate proof   -> downloads/boss-image-copy.iso matched archive/boss-image.iso as a named evidence peer
retention boundary -> matching bytes do not identify the authoritative copy
hardlink boundary -> 2 entries excluded
reclaim evidence  -> 729,088 bytes selected for review
target optimizer -> lower-risk candidates first; exact minimum-excess subset used for the remaining target
fail-closed check -> a synthetic cache mutation invalidated the plan
proof -> PASS; no file was deleted, moved, or transmitted
```

> Everything you just watched me do by hand runs in CI on every push, on four
> Python versions. That is the last line: no file was deleted, moved, or
> transmitted.

---

## Timing

| Step | Seconds | Cut if short on time? |
| --- | ---: | --- |
| 1 `/ai status` | 20 | No — this is Track 2 |
| 2 `/scan` | 30 | No |
| 3 `/candidates` | 30 | **Never** |
| 4 `/archives` | 25 | **Never** |
| 5 `/duplicates` | 25 | Yes |
| 6 `/target 600K` | 30 | Yes |
| 7 `/plan` + `/verify-plan` | 25 | No |
| 8 mutate + verify | 35 | **Never** |
| 9 `/delete` preview | 30 | No |
| 10 `--prove` | 20 | Yes, if step 8 landed |

Full run ~4:30. Cutting steps 5, 6 and 10 gives a 3-minute version that keeps
every safety claim.

## Extended — only if the jury asks

| They ask | You run |
| --- | --- |
| "Show me the report" | `/report demo.html` then `/serve`, open the printed URL |
| "What did it not scan?" | `/coverage` |
| "Prove those two files are identical" | `/verify-archive <copy> <original>` |
| "What is running?" | `/ps`, then `/stop <id>` |
| "Can it use a cloud model?" | `/ai api` — explain the env vars; do not configure a key on stage |
| "What does it consider unsafe?" | `/about` |
| "Full command list" | `/help` |

## Rules for the stage

1. **Never run an action command with `--execute`.** Preview only.
2. **Never debug live.** Ten seconds of trouble, then: "I have this captured on
   the slide."
3. **Do not scan a real personal folder** — someone will read your file names
   off the projector. Use the fixture.
4. **Do not clear the screen between steps.** The accumulated output *is* the
   evidence trail; let it build.
5. If a command is refused, say so plainly — a refusal is the product working.

## One-line recovery

| Problem | Say |
| --- | --- |
| Ollama unavailable | "Optional stage, falls back to the local classifier, and records why in the plan." |
| Fixture missing | `python -m sanchay.demo ~/sanchay-demo` while you keep talking. |
| Plan already exists | Add `--replace`, and say "plans are write-once by default." |
| Scan looks stuck | "It runs in the background — Esc interrupts it." Then move to the slide. |
| Anything else | Switch to the deck. The captures are already there. |
