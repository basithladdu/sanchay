# SANCHAY live demo — what to type, what to say

Ten steps. Each one has **Type this**, **You'll see**, **Say this**, and **Why it
matters**. Everything here was actually run on the laptop you're presenting from.

**Full run: about 6 minutes.** There's a shorter 3-minute version at the end.

---

## Step 0 — Before anyone walks in

Open the **Ubuntu tab** in Windows Terminal (not PowerShell). You need two of
them — call them A and B.

```bash
cd ~
which sanchay
```

It must say `/home/awaiz/.local/bin/sanchay`.

> **Why this matters:** there's a second copy of SANCHAY inside
> `/mnt/e/sanchay/.venv` with a broken pandas. If you run from there, the report
> command crashes with a wall of red text. Running from `~` avoids it completely.

Set everything up:

```bash
rm -rf ~/sanchay-demo
python3 -m sanchay.demo ~/sanchay-demo
sanchay ~/sanchay-demo --ai-provider ollama --report ~/Downloads/demo.html
```

Open a browser tab at `http://127.0.0.1:8123/demo.html`. It won't load yet —
that's fine, you'll refresh it at the end.

Start SANCHAY in terminal A and stop at the prompt:

```bash
sanchay
```

### The five files you're demoing on

Learn these — every single thing you say points back to one of them.

| File | What it is |
| --- | --- |
| `documents/capstone-thesis.txt` | Someone's only copy of something. Must never be suggested for deletion. |
| `archive/boss-image.iso` and `downloads/boss-image-copy.iso` | The exact same file, twice. |
| `workspace/node_modules/.cache/bundle.bin` | A build cache. Deleting it is fine — the tool rebuilds it. |
| `hardlinks/source.bin` and `alias.bin` | **One** file with two names. Not a copy. |

---

## Step 1 — Show where the AI is (20s)

**Type this:**

```
/ai status
```

**You'll see:**

```
Hybrid AI mode: auto
  usage prediction: sanchay_local_action_classifier v1 (always local)
  Ollama: available; selected qwen2.5-coder:7b; installed qwen2.5-coder:7b, moondream:latest
  OpenAI-compatible API: not configured; API keys are never printed
  safety: reasoning may keep or confirm a review; it cannot delete, promote an unsafe file, or bypass human approval
```

**Say this:**

> Before I scan anything, here's the AI. There are two of them. The first is a
> small model that runs on this laptop and always runs. The second is Qwen 2.5
> through Ollama — also on this laptop. No API key, nothing goes to the internet.
>
> Read that last line. The AI can suggest keeping a file. It cannot delete
> anything.

**Why it matters:** this is a Track 2 "AI at Application Level" project. Answer
"where's the AI?" in the first 20 seconds, before anyone has to ask.

*If it says unavailable:* "That stage is optional — it falls back to the local
model and writes down why." Then carry on. Nothing else breaks.

## Step 2 — Scan (35s)

**Type this:**

```
/scan ~/sanchay-demo
```

**You'll see, straight away:**

```
Background task 1 started: scan ~/sanchay-demo.
```

**Say this:**

> Notice I got my prompt back immediately. The scan runs in the background. On a
> real drive this takes minutes, and you can keep working while it does.

**Type this while it runs:**

```
/ps
```

```
 ID  status   elapsed  kind           details
------------------------------------------------------------------------------
  1  running        3s  scan           scanning and verifying ~/sanchay-demo: scan ~/sanchay-demo
```

**Then the result appears on its own:**

```
Background task 1 complete in 10s.
Scan complete: /home/awaiz/sanchay-demo
  6 entries; 1.3MB allocated storage
  1 duplicate groups; 512.0KB potential reclaim
  2 reviewable; 2 archive reviews; 2 unique files protected from cleanup
  reasoning AI: ollama/qwen2.5-coder:7b; 4 reviewed, 0 changed to keep
  coverage: complete
```

**Say this:**

> Six files. One pair of duplicates. Both AI stages ran.
>
> And the important line: **two files protected from cleanup.** They were taken
> out *before* anything got ranked — not filtered out afterwards.

## Step 3 — What it suggests (30s)

**Type this:**

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

**Say this:**

> Two suggestions. A duplicate, and a build cache.
>
> Now look at what's **missing**. The thesis isn't here. The hardlink isn't here.
> That's the whole point of the project.

**Why it matters:** this is the moment people remember. Pause here. Let them
look at a list that does *not* contain the dangerous file.

## Step 4 — Where the important file went (25s)

**Type this:**

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

**Say this:**

> There's the thesis. Nobody's touched it in 300 days, so the AI says "maybe move
> this somewhere else" — but that's a completely separate list.
>
> A one-of-a-kind file can be suggested for archiving. It can never be suggested
> for deleting.

## Step 5 — The visual view (45s)

Switch to **terminal B**:

```bash
sanchay ~/sanchay-demo --tui
```

A full-screen dashboard opens: four numbers across the top, then a table where
**every row is coloured by how recoverable that file is.**

| Colour | Meaning |
| --- | --- |
| Green | A build tool can regenerate it |
| Light green | An identical copy exists |
| Yellow | It's saved in a git repo |
| **Red** | **Nothing gets it back** |

**Press these keys:**

| Key | Does |
| --- | --- |
| `u` | show only duplicates |
| `d` | show only regenerable files |
| `a` | show everything again |
| `p` | sort by priority |
| `s` | sort by size |
| `q` | quit |

**Say this:**

> Same data, but now you can see it. Red means there is no way to get that file
> back. Green means a tool rebuilds it in seconds.
>
> You don't read a manual to use this. You look at the colours and you decide.

**Why it matters:** it turns your project from "a bunch of commands" into
something a person can actually use. Press `q` to quit when you're done.

## Step 6 — Ask for a specific amount (25s)

Back in **terminal A**:

```
/target 600K
```

```
Target 600.0KB: 712.0KB selected (met).
Run /candidates to review the selection before any action.
```

**Say this:**

> I asked for 600 KB. It found 712.
>
> And the order it picked matters: the cache first, because that's the least
> risky, then the duplicate. It will never grab a protected file just to hit the
> number. Ask it for 9 GB and it just says "I'm short" instead.

## Step 7 — What deleting looks like (30s)

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

**Say this:**

> Nothing happened. It just showed me what *would* happen.
>
> To really do it I need four more things: permission, an explicit execute flag,
> an exact confirmation code, and — because this is a duplicate — I have to name
> which copy survives. It refuses to pick that for me.

## Step 8 — It refuses stale evidence (40s)

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

**Say this:**

> That file is the full reasoning: why each file was picked, plus a checksum.

Now switch to **terminal B** and change one byte of a file that's in the plan:

```bash
printf 'x' >> ~/sanchay-demo/workspace/node_modules/.cache/bundle.bin
```

**Say this:**

> While we were talking, something on the disk changed. That happens all the time
> on a real machine.

Back to **terminal A**:

```
/verify-plan review.json
```

```
Plan is not valid for review; 4 recommendations checked.
```

**Say this:**

> It refuses. Not a warning — it refuses, *before* anyone acts on it. Old
> information isn't proof of anything.

**Why it matters:** this is the strongest 40 seconds you have. Don't rush it.

## Step 9 — Actually delete something (60s)

**This really deletes. Only ever on `~/sanchay-demo`.**

First, try it the way an impatient person would:

```
/delete 1 --execute --confirm DELETE:1
```

```
Delete refused: File actions are disabled; run /permissions enable I_UNDERSTAND_FILE_ACTIONS
```

> Refused. I never turned actions on.

```
/permissions enable I_UNDERSTAND_FILE_ACTIONS
/delete 1 --execute --confirm DELETE:1
```

```
Delete refused: Duplicate deletion requires --retain with the named evidence peer
```

> Refused again. I didn't say which copy gets to live.

```
/permissions enable I_UNDERSTAND_FILE_ACTIONS
/delete 1 --execute --confirm DELETE:1 --retain "/home/awaiz/sanchay-demo/archive/boss-image.iso"
```

```
Deleted verified candidate: /home/awaiz/sanchay-demo/downloads/boss-image-copy.iso
The active scan is now stale; run /refresh before another action.
```

```
/candidates
```

```
The active scan is stale after a file action. Run /refresh first.
```

> It locked itself. I can't do a second thing using information I just made
> out-of-date.

```
/refresh
```

```
Refresh complete: /home/awaiz/sanchay-demo
  5 entries; 800.0KB allocated storage
  0 duplicate groups; 0.0B potential reclaim
  1 reviewable; 2 archive reviews; 2 unique files protected from cleanup
```

> Six files became five. 1.3 MB became 800 KB. The duplicate's gone — and the
> thesis is still protected.

**Two things that will trip you up:**

1. **A refused try uses up your permission.** That's why you see
   `/permissions enable` twice. One permission = one *attempt*, not one success.
   If it says "actions are disabled" right after you enabled it, that's why.
2. **Rebuild the fixture after practising this,** or you'll walk on stage with
   nothing to delete:

   ```bash
   rm -rf ~/sanchay-demo && python3 -m sanchay.demo ~/sanchay-demo
   ```

## Step 10 — The report (45s) — finish here

```
/report demo.html --replace
```

```
Report created: /home/awaiz/Downloads/demo.html
```

```
/serve 8123
```

```
Exact URL for the active scan report: http://127.0.0.1:8123/demo.html
Background task 1 is hosting the report. Use /ps to view it or /stop 1 to close it.
```

**Switch to the browser tab you opened earlier and hit refresh.**

**Say this:**

> Everything you just watched is also a file you can send to someone else.
>
> It's served on 127.0.0.1 only — this machine, nothing outside it. And the page
> has no internet dependencies at all. The charts are built into the file, so it
> opens on a computer with no network.

Point at three things, then stop:

> The treemap is where your storage actually is. Red blocks are files with no way
> to recover them — that's not a delete list, that's the opposite.
>
> The table is the same review list you saw in the terminal.
>
> And at the bottom, a checksum, labelled "not a signature" — because it catches
> accidental changes, not someone deliberately faking a file.

**Finish on:**

> Nothing was deleted, moved, or uploaded that I didn't explicitly authorise —
> and you watched it refuse me twice before it let me.

---

## Timing

| Step | Seconds | Can you cut it? |
| --- | ---: | --- |
| 1 `/ai status` | 20 | No — it's the AI question |
| 2 `/scan` + `/ps` | 35 | Drop `/ps` only |
| 3 `/candidates` | 30 | **Never** |
| 4 `/archives` | 25 | **Never** |
| 5 dashboard | 45 | Yes |
| 6 `/target 600K` | 25 | Yes |
| 7 `/delete` preview | 30 | No |
| 8 fail closed | 40 | **Never** |
| 9 real delete | 60 | Yes — skip to `/refresh` |
| 10 report | 45 | No — it's the ending |

**Short version (3 min 20):** steps 1, 2, 3, 4, 7, 8, then `/refresh`, then 10.
You keep every safety point and still finish on the report.

## Rules

1. **Run from `~`, never `/mnt/e/sanchay`.** The report crashes there.
2. **Type commands one at a time.** If you paste two lines, they arrive as one
   command and you get `Usage: /refresh`.
3. **Only ever use `--execute` on `~/sanchay-demo`.** It deletes for real.
4. **Don't debug on stage.** Ten seconds, then: "I've got this captured on the
   slide."
5. **Never scan a personal folder** — your filenames go up on the projector.
6. **Don't clear the screen.** The output piling up *is* your evidence.
7. **A refusal is the product working.** Say so out loud when one appears.

## If they ask for more

| They ask | You run |
| --- | --- |
| "What didn't it scan?" | `/coverage` |
| "Prove those two are identical" | `/verify-archive <copy> <original>` |
| "Show me the hardlink" | Terminal B: `ls -li ~/sanchay-demo/hardlinks/` — same inode number, link count 2 |
| "What's running?" | `/ps`, then `/stop <id>` |
| "Could it use ChatGPT instead?" | `/ai api` — explain the settings, don't put a key in on stage |
| "What does it call unsafe?" | `/about` |
| "All the commands?" | `/help` |

## If something breaks

| Problem | Say |
| --- | --- |
| Ollama unavailable | "Optional stage — it falls back to the local model and records why." |
| "Actions are disabled" after enabling | A refused try used it up. Run `/permissions enable ...` again. |
| `/report` says already exists | Add `--replace`, and say "files don't get silently overwritten." |
| Browser won't load | Check the port matches `/serve 8123`, or just open `~/Downloads/demo.html`. |
| Fixture missing | `python3 -m sanchay.demo ~/sanchay-demo` while you keep talking. |
| Anything else | Go back to the slides. The screenshots are already there. |
