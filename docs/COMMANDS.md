# SANCHAY command reference

Every command in the interactive shell, with a runnable example and the real
output it produced. Start the shell by running `sanchay` with no arguments.

## Reproducing these examples

Each transcript below was captured against the bundled disposable fixture, so
you can run the same commands and compare:

```bash
python -m sanchay.demo ~/sanchay-demo
```

That creates a small tree containing one byte-identical duplicate pair, one
regenerable build cache, one hardlink pair, and one deliberately unique file
(`documents/capstone-thesis.txt`) that must never reach a cleanup plan. It
deletes, moves, and transmits nothing.

Paths are shown POSIX-style. Report and plan destinations, ports, and elapsed
times will differ on your machine.

---

## 1. Getting evidence

### `/scan <path> [--cross-filesystems]`

Walks the tree, classifies every file, and keeps the result as the *active
scan* in memory. No report, no files touched. `--cross-filesystems` widens the
inventory across mount points, but capacity claims still stay per-filesystem —
crossing mounts never creates a shared capacity number.

```
sanchay> /scan ~/sanchay-demo
```

```
Scan complete: ~/sanchay-demo
  6 entries; 1.3MB allocated storage
  1 duplicate groups; 512.0KB potential reclaim
  2 reviewable; 2 archive reviews; 2 unique files protected from cleanup
  reasoning AI: off; local usage classifier used
  coverage: complete
```

`2 unique files protected from cleanup` is the line that matters: those files
were excluded before ranking, not filtered out afterwards.

### `/analyze <path> [options]`

`/scan` plus the candidate list plus an HTML report, in one command. Options:
`--report <name.html>`, `--limit <n>`, `--replace`, `--cross-filesystems`.
This is the demo command.

```
sanchay> /analyze ~/sanchay-demo --report demo-report.html
```

```
Analysis target: ~/sanchay-demo
Scan complete: ~/sanchay-demo
  6 entries; 1.3MB allocated storage
  1 duplicate groups; 512.0KB potential reclaim
  2 reviewable; 2 archive reviews; 2 unique files protected from cleanup
  reasoning AI: off; local usage classifier used
  coverage: complete
Candidates from active scan: ~/sanchay-demo
 #  reclaim   kind         AI clean  unchanged  relative path
------------------------------------------------------------------------------------------
 1   512.0KB  duplicate       95%     120.1d  downloads/boss-image-copy.iso
 2   200.0KB  disposable      93%      44.9d  workspace/node_modules/.cache/bundle.bin
AI archive reviews from active scan: ~/sanchay-demo
 #  allocated  confidence  unchanged  relative path
------------------------------------------------------------------------------------------
 1    512.0KB        76%     120.1d  archive/boss-image.iso
 2      41.0B        81%     300.0d  documents/capstone-thesis.txt
Archive is a recommendation only: choose a destination, copy separately, then verify it with /verify-archive.
HTML report destination: ~/Downloads/demo-report.html
Analysis complete.
Report created: ~/Downloads/demo-report.html
When you want to host it, run /serve separately.
```

In an interactive session this runs as a background task, so the prompt returns
immediately and the animated `Working` strip reports progress.

### `/run <path> [options]`

Identical to `/analyze`. Just a shorter name.

### `/refresh`

Re-runs the active scan with the same root and flags. Three side effects worth
knowing: it revokes any temporary file-action permission, it shuts down a
running report server (that server was serving evidence you just replaced), and
it is **mandatory after any file action** — deleting or moving marks the scan
stale, and every command that reads the plan refuses until you refresh.

```
sanchay> /refresh
```

```
Refresh complete: ~/sanchay-demo
  5 entries; 1.1MB allocated storage
  1 duplicate groups; 512.0KB potential reclaim
  0 reviewable; 1 archive reviews; 2 unique files protected from cleanup
  reasoning AI: off; local usage classifier used
  coverage: complete
```

This transcript follows the `/clean` example further down — one entry fewer, and
nothing left to review.

### `/ai [status|auto|ollama|api|off] [model]`

Picks the reasoning provider layered on top of the local classifier. `auto`
prefers a local Ollama, then a configured API; `ollama` is local only; `api`
uses your `SANCHAY_AI_API_*` environment settings; `off` leaves only the local
usage classifier. It applies to the **next** scan, not to evidence you already
have.

```
sanchay> /ai status
```

```
Hybrid AI mode: auto
  usage prediction: sanchay_local_action_classifier v1 (always local)
  Ollama: available; selected qwen2.5-coder:7b; installed qwen2.5-coder:7b, moondream:latest
  OpenAI-compatible API: not configured; API keys are never printed
  safety: reasoning may keep or confirm a review; it cannot delete, promote an unsafe file, or bypass human approval
```

Switching provider prints the same status block plus
`The setting applies to the next /analyze, /scan, or /refresh.`

---

## 2. Reading what it found

### `/status`

Active scan summary, artifact paths, reclaim-target state, permission state.
Your "where am I" command.

```
sanchay> /status
```

```
Active scan: ~/sanchay-demo
  6 entries; 1.3MB allocated storage
  1 duplicate groups; 512.0KB potential reclaim
  2 reviewable; 2 archive reviews; 2 unique files protected from cleanup
  reasoning AI: off; local usage classifier used
  coverage: complete
  report: not generated
  plan: not written
  file actions: disabled
```

### `/coverage`

Whether the scan actually read everything in scope. If directories or files were
unreadable it counts them and states that capacity trends and whole-tree claims
are withheld from a partial view. This is the honesty command — worth showing a
jury.

```
sanchay> /coverage
```

```
Coverage complete: all in-scope, non-sensitive paths were inspected.
```

On a partial scan it reads instead:

```
Coverage incomplete: 12 directories and 3 files could not be inspected.
Capacity trends and whole-tree claims are withheld from this partial view.
```

### `/candidates [limit]`

Default 20. The ranked review list from the verified active plan. It is
deterministic review **priority**, never an execution order.

```
sanchay> /candidates 5
```

```
Candidates from active scan: ~/sanchay-demo
 #  reclaim   kind         AI clean  unchanged  relative path
------------------------------------------------------------------------------------------
 1   512.0KB  duplicate       95%     120.1d  downloads/boss-image-copy.iso
 2   200.0KB  disposable      93%      44.9d  workspace/node_modules/.cache/bundle.bin
```

The numbers in the first column are what `/delete` and `/move` take.

### `/archives [limit]`

Default 20. Archive-review candidates the model ranked separately. These are
files that can never be cleanup candidates; archive review is the only
recommendation available for them.

```
sanchay> /archives 5
```

```
AI archive reviews from active scan: ~/sanchay-demo
 #  allocated  confidence  unchanged  relative path
------------------------------------------------------------------------------------------
 1    512.0KB        76%     120.1d  archive/boss-image.iso
 2      41.0B        81%     300.0d  documents/capstone-thesis.txt
Archive is a recommendation only: choose a destination, copy separately, then verify it with /verify-archive.
```

`documents/capstone-thesis.txt` is the deliberately unique fixture file. It
appears here, and never in `/candidates`.

### `/duplicates [limit]`

Default 10. Digest-matched groups with physical copy counts and reviewable
bytes. Every group is re-confirmed byte-for-byte when the plan is built, so this
listing is a preview of evidence, not the evidence itself.

```
sanchay> /duplicates 3
```

```
Duplicates from active scan: ~/sanchay-demo
1 groups; 512.0KB potential allocated reclaim.
1. 2 physical copies; about 512.0KB reviewable
     archive/boss-image.iso
     downloads/boss-image-copy.iso
Every duplicate recommendation is byte-confirmed again when its plan is built.
```

`2 physical copies` counts allocation, not directory entries — the fixture's
hardlink pair is not listed here, because unlinking one alias frees nothing.

### `/target <size|clear>`

Builds a target-aware plan: lower-risk classes are selected first, and the
result reports selected bytes plus met or short-by. `clear` restores the default
plan. Both drop file-action permission, and it refuses to run while a background
scan is in flight.

```
sanchay> /target 600K
```

```
Target 600.0KB: 712.0KB selected (met).
Run /candidates to review the selection before any action.
```

Ask for more than the evidence supports and it says so rather than reaching into
protected files:

```
sanchay> /target 9G
```

```
Target 9.0GB: 712.0KB selected (short by 9.0GB).
Run /candidates to review the selection before any action.
```

```
sanchay> /target clear
```

```
Reclaim target cleared; the default review plan is active.
```

---

## 3. Artifacts you can keep

### `/report [name.html]`

Writes the interactive HTML report into Downloads. Write-once unless you pass
`--replace`.

```
sanchay> /report demo-report.html
```

```
HTML report destination: ~/Downloads/demo-report.html
Report created: ~/Downloads/demo-report.html
This report uses the active scan shown by /status. Run /open-report, or /serve for its exact browser URL.
```

### `/plan [name.json] [--replace]`

Writes the review plan: typed recovery evidence per candidate plus a SHA-256
integrity checksum. Write-once by default, with a timestamped default filename.
Unlike `/report`, the plan is written **relative to the working directory**, not
into Downloads.

```
sanchay> /plan review.json
```

```
Review plan created: ~/evidence/review.json
```

Running it again refuses rather than overwriting evidence:

```
sanchay> /plan review.json
```

```
Plan was not written: [Errno 17] File exists: 'review.json'
```

```
sanchay> /plan review.json --replace
```

```
Review plan created: ~/evidence/review.json
```

### `/verify-plan <plan.json>`

Rechecks the checksum **and** each file's identity, then reports whether the plan
is still valid. It never modifies a candidate.

```
sanchay> /verify-plan ~/evidence/review.json
```

```
Plan is valid for human review; 4 recommendations checked.
```

Now change one file the plan recorded — appending a few bytes to the cache file
is enough — and ask again:

```
sanchay> /verify-plan ~/evidence/review.json
```

```
Plan is not valid for review; 4 recommendations checked.
```

This is the fail-closed proof: the plan is refused before a human acts on it,
not after.

### `/verify-archive <source> <copy>`

Proves two separately chosen files are byte-identical without copying, moving,
or deleting either. A same-filesystem match is deliberately **not** called a
backup.

```
sanchay> /verify-archive ~/sanchay-demo/downloads/boss-image-copy.iso ~/sanchay-demo/archive/boss-image.iso
```

```
Retained copy verified; manual-review reclaim: 512.0KB
```

### `/serve [port]`

Hosts the latest report on `127.0.0.1` only, as a background task. The default
port `0` asks the OS for a free port, which avoids opening a stale site that
happens to own port 8000.

```
sanchay> /serve
```

```
Exact URL for the active scan report: http://127.0.0.1:49714/demo-report.html
The filename at the end matters; do not open an older server root URL.
Background task 1 is hosting the report. Use /ps to view it or /stop 1 to close it.
```

Pass a port explicitly when you need a predictable URL: `/serve 8123`.

### `/open-report`

Opens the served URL if a server is running, otherwise the local `file://` path.
Prints `Opened: <url>`, or `The browser did not open automatically. Use: <url>`
when no browser is available — common over SSH or in a bare WSL session.

---

## 4. Background work

### `/ps`

Table of running tasks: id, status, elapsed, kind, and the live phase.

```
sanchay> /ps
```

```
 ID  status   elapsed  kind           details
------------------------------------------------------------------------------
  1  running        0s  report-server  http://127.0.0.1:49714/demo-report.html
```

With nothing running:

```
No SANCHAY background tasks are running.
```

### `/stop <id|all>`

Stops a service outright, or asks a running scan to cancel cooperatively.

```
sanchay> /stop 1
```

```
Stopped background task 1: report-server.
```

A scan behaves differently, because stopping it mid-flight must not publish a
half-finished view:

- still scanning → `Cancellation requested for background task 2: scan. It will
  stop at the next safe checkpoint.`
- already published → `Background task 2 is finishing; completed evidence has
  already been published.`
- wrong id → `Background task 7 is not running. Use /ps to view tasks.`

`/stop all` stops everything at once. **Esc** does the same as `/stop <id>` for
the newest *interruptible* task without leaving the prompt — it does not touch a
report server.

---

## 5. The action gate

Disabled by default, and the sequence is deliberately awkward.

### `/permissions [status|enable I_UNDERSTAND_FILE_ACTIONS|disable]`

Authorization is **one-use**: it covers a single action command and is dropped
afterwards, and also on refresh, on target change, and on exit.

```
sanchay> /permissions status
```

```
File actions are disabled.
Enable for one action command with: /permissions enable I_UNDERSTAND_FILE_ACTIONS
```

```
sanchay> /permissions enable I_UNDERSTAND_FILE_ACTIONS
```

```
File actions authorized for one action command. Preview the command before adding --execute.
```

A wrong phrase changes nothing: `Authorization phrase did not match; file actions
remain disabled.`

### `/delete <number>`

Previews by default; nothing happens without `--execute --confirm
DELETE:<number>`. A duplicate additionally requires `--retain "<named peer>"`, so
you state which copy survives rather than letting the tool choose.

```
sanchay> /delete 1
```

```
PREVIEW only: permanently delete candidate 1, 512.0KB duplicate: downloads/boss-image-copy.iso
To execute: authorize actions, then rerun with --execute --confirm DELETE:1
Duplicate retention confirmation required: --retain "~/sanchay-demo/archive/boss-image.iso"
```

The full form is then:

```
sanchay> /delete 1 --execute --confirm DELETE:1 --retain "~/sanchay-demo/archive/boss-image.iso"
```

On success it prints `Deleted verified candidate: <path>` and marks the scan
stale. A refused action prints `Delete refused: <reason>`.

### `/move <number> <destination>`

Same preview and confirm shape. Execution refuses overwrites and
cross-filesystem moves outright.

```
sanchay> /move 1 ~/sanchay-demo/moved.bin
```

```
PREVIEW only: move candidate 1, 512.0KB duplicate, to ~/sanchay-demo/moved.bin
Execution refuses overwrites and cross-filesystem moves. Authorize actions, then rerun with --execute --confirm MOVE:1
```

### `/clean`

Batch, but only over regenerable candidates. Duplicate, tracked, unique, and
hardlinked files are excluded by construction. The confirmation carries the
count, so if the count shifts between preview and execute, the confirmation no
longer matches.

```
sanchay> /clean
```

```
PREVIEW only: permanently delete 1 regenerable candidates (200.0KB). Duplicate, tracked, unique, and hardlinked files are excluded.
To execute: authorize actions, then rerun with --execute --confirm CLEAN:1
```

```
sanchay> /permissions enable I_UNDERSTAND_FILE_ACTIONS
sanchay> /clean --execute --confirm CLEAN:1
```

```
Deleted 1 verified regenerable candidates (200.0KB).
The active scan is now stale; run /refresh before another action.
```

Every plan-reading command now refuses until you refresh:

```
sanchay> /candidates
```

```
The active scan is stale after a file action. Run /refresh first.
```

---

## 6. Session

### `/about`

The purpose and safety boundary, including the model identity and the statement
that the AI has no file-action authority.

```
sanchay> /about
```

```
SANCHAY is a local, evidence-first storage review assistant.
It inventories allocated storage and runs a local learned classifier over metadata and positive usage evidence to recommend Keep, Cleanup Review, or Archive Review. Deterministic recovery gates prohibit unique and hardlinked files from cleanup.
Usage model: sanchay_local_action_classifier v1 (multiclass logistic regression, trained locally from the bundled disclosed seed profiles). A constrained Ollama or OpenAI-compatible reasoning model can keep or confirm the resulting Cleanup and Archive reviews.

It creates an auditable HTML report in Downloads and can host that report on 127.0.0.1 as a managed background task. File actions are separate, disabled by default, and require temporary permission plus exact confirmation.

The AI records probabilities and top factors but has no file-action authority. SANCHAY does not upload scanned file paths or contents and does not elevate your operating-system permissions.
```

### `/help [command]`

The full table, or one command's detail.

```
sanchay> /help scan
```

```
Scan a drive or directory and retain the resulting evidence.
```

### `/clear`

Clears the visible terminal only. The active scan, plan, and artifacts survive;
there is no output.

### `/exit`

```
sanchay> /exit
```

```
SANCHAY closed.
```

Also revokes permission, stops every background task, and closes a running
report server, so nothing outlives the session. `/quit` and Ctrl+D do the same.

---

## The boundary in one screen

Sections 1 to 4 are entirely read-only. Section 5 is the only place a file
changes, and it needs all five of these to line up:

1. a scan that is not stale,
2. one-use permission from `/permissions enable I_UNDERSTAND_FILE_ACTIONS`,
3. an explicit `--execute`,
4. an exact `--confirm` string, plus `--retain` for a duplicate,
5. a fresh evidence recheck at execution time.

Any one of them failing stops the action, and the permission is dropped either
way.
