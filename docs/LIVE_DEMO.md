# SANCHAY live demonstration — stage script

Ten steps through the interactive shell, ending on the HTML report in a browser.
Every keystroke, what to say while it runs, and the output you will see.

**Core run: about 4 minutes 45 seconds.** Every output below was captured from a
real run on the WSL machine this demo is presented from.

---

## Step 0 — Setup, before the jury walks in

**Two terminals.** Terminal A runs SANCHAY. Terminal B stays at a plain shell —
you need it once, in step 8.

```bash
cd ~
deactivate 2>/dev/null
which sanchay
```

`which sanchay` **must** print `/home/awaiz/.local/bin/sanchay`.

> **Never run the demo from `/mnt/e/sanchay`.** That directory has a `.venv`
> whose pandas C extension is not built. The report command crashes the whole
> shell with a traceback. Running from `~` uses the working install, prints
> clean `/home/awaiz/...` paths on the projector, and writes plans to your home
> directory.

Build the fixture and pre-warm the browser:

```bash
rm -rf ~/sanchay-demo
python3 -m sanchay.demo ~/sanchay-demo
sanchay ~/sanchay-demo --report ~/Downloads/demo.html
```

Open a browser tab at `http://127.0.0.1:8123/demo.html`. It will not load yet —
that is fine. The tab is now pre-typed, so in step 10 you only press refresh.

Then launch and stop at the prompt:

```bash
sanchay
```

**What the fixture holds** — know this cold:

| File | Why it is there |
| --- | --- |
| `documents/capstone-thesis.txt` | Unique. Must never appear in cleanup. |
| `archive/boss-image.iso` + `downloads/boss-image-copy.iso` | Byte-identical pair. |
| `workspace/node_modules/.cache/bundle.bin` | Regenerable cache. |
| `hardlinks/source.bin` + `alias.bin` | One inode, two names. |

---

## Step 1 — Where the AI is (20s)

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

> Before I scan anything — this is the AI, and there are two stages. Stage one
> is a local classifier that always runs. Stage two is an optional local model,
> Qwen 2.5 through Ollama, on this laptop. No API key. Nothing leaves the
> machine.
>
> Read the last line: the reasoning model may keep or confirm a review. It
> cannot delete, cannot promote an unsafe file, cannot bypass approval.

*If it says unavailable:* "The reasoning stage is optional — it falls back to
the local classifier and records why in the plan." Then continue.

## Step 2 — Scan (35s)

```
/scan ~/sanchay-demo
```

```
Background task 1 started: scan ~/sanchay-demo.
```

> The prompt came straight back. Scans run in the background — on a real
> filesystem this takes minutes and you keep working. Escape interrupts it.

While it runs, show that:

```
/ps
```

```
 ID  status   elapsed  kind           details
------------------------------------------------------------------------------
  1  running        3s  scan           scanning and verifying ~/sanchay-demo: scan ~/sanchay-demo
```

Then the result arrives on its own:

```
Background task 1 complete in 10s.
Scan complete: /home/awaiz/sanchay-demo
  6 entries; 1.3MB allocated storage
  1 duplicate groups; 512.0KB potential reclaim
  2 reviewable; 2 archive reviews; 2 unique files protected from cleanup
  reasoning AI: ollama/qwen2.5-coder:7b; 4 reviewed, 0 changed to keep
  coverage: complete
```

> Six files, one duplicate group. Both AI stages ran — four candidates reviewed
> by the local model, none overridden by the reasoner.
>
> And the line that matters: **two unique files protected from cleanup.** They
> were excluded before ranking, not filtered out afterwards.

## Step 3 — The cleanup list (30s)

```
/candidates
```

```
Candidates from active scan: /home/awaiz/sanchay-demo
 #  reclaim   kind         AI clean  unchanged  relative path
------------------------------------------------------------------------------------------
 1   512.0KB  duplicate       95%     120.1d  downloads/boss-image-copy.iso
 2   200.0KB  disposable      93%      44.9d  workspace/node_modules/.cache/bundle.bin
```

> Two candidates: a byte-confirmed duplicate and a build cache.
>
> Now look at what is **not** here. The thesis is not in this list. Neither is
> the hardlink alias. This is a review list ranked by priority — not an
> execution order.

**Do not rush this slide of the demo. It is the one they remember.**

## Step 4 — Where the protected file went (25s)

```
/archives
```

```
AI archive reviews from active scan: /home/awaiz/sanchay-demo
 #  allocated  confidence  unchanged  relative path
------------------------------------------------------------------------------------------
 1    512.0KB        76%     120.1d  archive/boss-image.iso
 2      4.0KB        83%     300.0d  documents/capstone-thesis.txt
Archive is a recommendation only: choose a destination, copy separately, then verify it with /verify-archive.
```

> There is the thesis. Unchanged for 300 days, so the model suggests you might
> want to archive it — but archive is a *separate list* with a different
> boundary. A unique file can be suggested for archive. It can never be
> suggested for cleanup.

## Step 5 — Why the duplicate is safe to review (20s)

```
/duplicates
```

```
Duplicates from active scan: /home/awaiz/sanchay-demo
1 groups; 512.0KB potential allocated reclaim.
1. 2 physical copies; about 512.0KB reviewable
     archive/boss-image.iso
     downloads/boss-image-copy.iso
Every duplicate recommendation is byte-confirmed again when its plan is built.
```

> Two **physical** copies. The hardlink pair is not here, because unlinking one
> name frees zero bytes.
>
> We never stop at a hash: same size, then a 64 KB prefix, then BLAKE2b, then a
> full byte-for-byte compare — and it is confirmed again when the plan is built.

## Step 6 — Ask for a specific amount (25s)

```
/target 600K
```

```
Target 600.0KB: 712.0KB selected (met).
Run /candidates to review the selection before any action.
```

> I asked for 600 KB and it found 712.
>
> The order matters: the regenerable cache first at regret 0.02, then the
> duplicate at 0.10. Lowest consequence first. And it will never reach into
> protected files to hit a number — ask for 9 GB and it reports "short by"
> rather than touching the thesis.

## Step 7 — The action gate (30s)

```
/permissions status
```

```
File actions are disabled.
Enable for one action command with: /permissions enable I_UNDERSTAND_FILE_ACTIONS
```

```
/delete 1
```

```
PREVIEW only: permanently delete candidate 1, 512.0KB duplicate: downloads/boss-image-copy.iso
To execute: authorize actions, then rerun with --execute --confirm DELETE:1
Duplicate retention confirmation required: --retain "/home/awaiz/sanchay-demo/archive/boss-image.iso"
```

> This is what deleting looks like: a preview.
>
> To actually run it I need four more things — one-use permission, an explicit
> `--execute`, an exact confirmation token, and, because this is a duplicate, I
> must name which copy survives. The tool refuses to choose that for me.
>
> There is no automatic executor in this product. But let me show you that the
> gate is real, and not just a message.

Step 9 executes it. If you would rather not act on stage, say "I am not going to
run it" here, skip step 9, and run `/refresh` instead.

## Step 8 — Fail closed (40s) — the strongest moment

```
/plan review.json
```

```
Review plan created: /home/awaiz/review.json
```

```
/verify-plan review.json
```

```
Plan is valid for human review; 4 recommendations checked.
```

> The plan is JSON: typed evidence for every candidate, a SHA-256 checksum, the
> model version, and the checksum of the training data.

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

> The plan is refused — not a warning, refused, **before** a human acts on it.
> Evidence that is stale is not evidence.

## Step 9 — Act on it, through the gate (60s)

**This deletes for real. Only ever on the fixture.** Every output below is
verified.

Try it the way a hurried person would — with no permission:

```
/delete 1 --execute --confirm DELETE:1
```

```
Delete refused: File actions are disabled; run /permissions enable I_UNDERSTAND_FILE_ACTIONS
```

> Refusal one. I never turned actions on.

```
/permissions enable I_UNDERSTAND_FILE_ACTIONS
```

```
File actions authorized for one action command. Preview the command before adding --execute.
```

```
/delete 1 --execute --confirm DELETE:1
```

```
Delete refused: Duplicate deletion requires --retain with the named evidence peer
```

> Refusal two. It is a duplicate, and I have not said which copy survives. It
> will not choose that for me.

```
/permissions enable I_UNDERSTAND_FILE_ACTIONS
/delete 1 --execute --confirm DELETE:1 --retain "/home/awaiz/sanchay-demo/archive/boss-image.iso"
```

```
Deleted verified candidate: /home/awaiz/sanchay-demo/downloads/boss-image-copy.iso
The active scan is now stale; run /refresh before another action.
```

> Now it runs — and immediately locks itself.

```
/candidates
```

```
The active scan is stale after a file action. Run /refresh first.
```

> I cannot take a second action on evidence I have just invalidated.

```
/refresh
```

```
Refresh complete: /home/awaiz/sanchay-demo
  5 entries; 800.0KB allocated storage
  0 duplicate groups; 0.0B potential reclaim
  1 reviewable; 2 archive reviews; 2 unique files protected from cleanup
```

> Six entries became five. 1.3 MB became 800 KB. The duplicate group is gone,
> and the thesis is still protected.

**Two things that will trip you up:**

1. **A refused attempt consumes the permission.** That is why `/permissions
   enable` appears twice above. One authorization covers one *attempt*, not one
   *success*. If a command says "actions are disabled" when you think you just
   enabled them, that is why — re-enable and continue.
2. **Rebuild the fixture after rehearsing this**, or your live run starts with no
   duplicate to delete:

   ```bash
   rm -rf ~/sanchay-demo && python3 -m sanchay.demo ~/sanchay-demo
   ```

**The batch form, if asked:** `/clean` previews only regenerable files, then
`/permissions enable ...` and `/clean --execute --confirm CLEAN:1` reports
`Deleted 1 verified regenerable candidates (200.0KB).` Duplicate, tracked,
unique and hardlinked files are excluded by construction.

## Step 10 — The report (45s) — finish here

```
/report demo.html --replace
```

```
HTML report destination: /home/awaiz/Downloads/demo.html
Report created: /home/awaiz/Downloads/demo.html
This report uses the active scan shown by /status. Run /open-report, or /serve for its exact browser URL.
```

```
/serve 8123
```

```
Exact URL for the active scan report: http://127.0.0.1:8123/demo.html
The filename at the end matters; do not open an older server root URL.
Background task 1 is hosting the report. Use /ps to view it or /stop 1 to close it.
```

**Switch to the browser tab you pre-opened and press refresh.**

> Everything you just watched is also an artifact you can hand to someone else.
>
> This is served on loopback only — 127.0.0.1, no external interface. And the
> page is completely self-contained: the charting library is inlined, so there
> is no CDN call and it opens on an air-gapped machine.

Walk three things on the page, then stop:

> The treemap shows where the storage actually sits — allocated bytes, so a
> hardlink is counted once.
>
> The candidate table is the same review list from the terminal, with the
> evidence attached to each row.
>
> And at the bottom, the plan's integrity checksum, labelled *not a signature* —
> because it detects accidental change, not forgery. What actually protects you
> is that verification rechecks every file's identity on disk, which you saw
> fail a minute ago.

Close on:

> No file was deleted, moved, or transmitted during any of that.

Then `/stop 1` if you want the port back.

---

## Timing

| Step | Seconds | Cut if short? |
| --- | ---: | --- |
| 1 `/ai status` | 20 | No — this is Track 2 |
| 2 `/scan` + `/ps` | 35 | Drop `/ps` only |
| 3 `/candidates` | 30 | **Never** |
| 4 `/archives` | 25 | **Never** |
| 5 `/duplicates` | 20 | Yes |
| 6 `/target 600K` | 25 | Yes |
| 7 `/permissions` + `/delete` | 30 | No |
| 8 mutate + verify | 40 | **Never** |
| 9 action gate + `/refresh` | 60 | Yes — run `/refresh` alone (15s) |
| 10 `/report` + `/serve` | 45 | No — this is the finish |

Full run with the action gate is about 5 minutes 45 seconds. Cutting steps 5
and 6, and reducing step 9 to a bare `/refresh`, gives a 3-minute 20-second run
that keeps every safety claim and still ends on the report.

## Rules for the stage

1. **Run from `~`, never `/mnt/e/sanchay`.** The venv there has a broken pandas
   and `/report` will crash the shell.
2. **Type commands one at a time.** Pasting two lines sends them as a single
   input — `/refresh` plus `/delete 1` arrives as `/refresh /delete 1` and you
   get `Usage: /refresh`.
3. **Only ever run `--execute` against `~/sanchay-demo`.** It deletes for
   real. Never point an action command at a personal folder, and rebuild the
   fixture after any rehearsal that deletes from it.
4. **Never debug live.** Ten seconds of trouble, then: "I have this captured on
   the slide."
5. **Do not scan a personal folder** — your filenames go on the projector.
6. **Do not clear the screen.** The accumulated output is the evidence trail.
7. A refusal is the product working. Say so plainly when one appears.

## If the jury asks for more

| They ask | You run |
| --- | --- |
| "What did it not scan?" | `/coverage` |
| "Prove those two are identical" | `/verify-archive <copy> <original>` |
| "Show the hardlink" | In terminal B: `ls -li ~/sanchay-demo/hardlinks/` — same inode, link count 2 |
| "What is running?" | `/ps`, then `/stop <id>` |
| "Can it use a cloud model?" | `/ai api` — explain the env vars, do not configure a key on stage |
| "What does it consider unsafe?" | `/about` |
| "Full command list" | `/help` |

## One-line recovery

| Problem | Say |
| --- | --- |
| Ollama unavailable | "Optional stage — it falls back to the local classifier and records why in the plan." |
| `/report` says already exists | Add `--replace`, and say "artifacts are write-once by default." |
| Browser tab will not load | Check the port matches `/serve 8123`; otherwise open `~/Downloads/demo.html` directly. |
| Fixture missing | `python3 -m sanchay.demo ~/sanchay-demo` while you keep talking. |
| "Actions are disabled" after enabling | A refused attempt consumed it. Re-run `/permissions enable I_UNDERSTAND_FILE_ACTIONS`. |
| Anything else | Switch to the deck. The captures are already there. |
