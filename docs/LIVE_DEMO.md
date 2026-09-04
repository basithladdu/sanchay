# SANCHAY live demo — fast version

Eight steps, about 3 minutes 20 seconds. Each step: what to type, what it does,
what to say. Keep the spoken lines short — one or two sentences, then move.

---

## Before you start

Ubuntu tab, two terminals (A and B).

```bash
cd ~
which sanchay          # must say /home/awaiz/.local/bin/sanchay
sanchay
```

Browser tab open at `http://127.0.0.1:8123/demo.html` (it won't load until the
end — that's fine).

---

## Open with this

> My name is Awaiz. I'm going to show you SANCHAY working, live.
>
> SANCHAY finds storage you can safely get rid of. The important word is safely —
> it will not touch anything it can't prove is recoverable.

Then, with the welcome screen still up:

> This is its shell. Every command starts with a slash.

## 1. Show the menu (10s)

**Type:** `/`

**What it does:** lists every command as you type.

**Say:**

> Type a slash and it shows you everything it can do. Scan, review, report,
> delete — all of it from here.

Press Escape to close the menu.

## 2. Where the AI is (15s)

**Type:** `/ai status`

**What it does:** shows which AI models are running and what they're allowed to do.

**Say:**

> Two AI models, both on this laptop. Nothing goes to the internet.
>
> And read the last line — the AI can suggest keeping a file. It cannot delete
> anything.

## 3. Scan (25s)

**Type:** `/scan ~/sanchay-demo`

**What it does:** reads the folder and works out what each file is.

**Say:**

> That runs in the background, so I get my prompt back straight away.

When it finishes:

> Six files. One pair of duplicates. And two files it has protected — those are
> out before anything gets ranked.

## 4. What it suggests (25s)

**Type:** `/candidates`

**What it does:** the list of files it thinks you could review for removal.

**Say:**

> Two suggestions — a duplicate, and a build cache.
>
> Now look at what's *not* here. There's a thesis in that folder. It's not on
> this list. That's the whole project.

**Slow down here. This is the moment.**

## 5. Where the thesis went (20s)

**Type:** `/archives`

**What it does:** a separate list — files worth moving somewhere, not deleting.

**Say:**

> There it is. Nobody's opened it in 300 days, so it suggests archiving it —
> a completely different list.
>
> A one-of-a-kind file can be suggested for archiving. Never for deleting.

## 6. Try to delete it (30s)

**Type:** `/delete 1`

**What it does:** shows what *would* happen. Nothing is deleted.

**Say:**

> Nothing happened — it just showed me the preview.

**Type:** `/delete 1 --execute --confirm DELETE:1`

**What it does:** actually tries it.

**Say:**

> Refused. I never turned actions on. They're off by default.

## 7. It refuses old information (40s)

**Type:** `/plan review.json` then `/verify-plan review.json`

**What it does:** saves the full reasoning to a file, then checks it's still true.

**Say:**

> Valid. That file has every reason it picked each candidate.

**In terminal B:**

```bash
printf 'x' >> ~/sanchay-demo/workspace/node_modules/.cache/bundle.bin
```

> Something on the disk just changed. That happens all the time on a real
> machine.

**Back in terminal A, type:** `/verify-plan review.json`

**Say:**

> Now it refuses. Not a warning — it refuses, before anyone acts on it.

**This is your strongest 40 seconds.**

## 8. The report (35s)

**Type:** `/refresh`

Then: `/report demo.html --replace`

Then: `/serve 8123`

**What it does:** builds a web page of everything, and serves it on this machine only.

**Switch to the browser tab and refresh.**

**Say:**

> Same information as a page you can send someone. It's served on this laptop
> only, and it works with no internet at all.
>
> The red blocks are files with no way to get them back. That's not a delete
> list — that's what it's protecting.

**Finish on:**

> Nothing was deleted or uploaded that I didn't authorise — and you watched it
> refuse me twice.

---

## Optional extras — only if they ask or you have time

| They ask | Type | Say |
| --- | --- | --- |
| "Show it visually" | In terminal B: `sanchay ~/sanchay-demo --tui` | "Colour tells you the risk. Red means unrecoverable." Keys: `u` duplicates, `d` cache, `a` all, `q` quit |
| "Can it hit a target?" | `/target 600K` | "I asked for 600 KB, it found 712 — cheapest-to-replace first." |
| "Prove they're duplicates" | `/duplicates` | "Same size, then a partial hash, then a full byte-by-byte compare." |
| "Can it actually delete?" | `/permissions enable I_UNDERSTAND_FILE_ACTIONS` then `/delete 1 --execute --confirm DELETE:1 --retain "/home/awaiz/sanchay-demo/archive/boss-image.iso"` | "Permission, execute flag, exact code, and I name which copy survives." |
| "What didn't it scan?" | `/coverage` | "It tells you what it couldn't read." |
| "All the commands?" | `/help` | — |

---

## Rules

1. Run from `~`, never `/mnt/e/sanchay` — the report crashes there.
2. Type commands one at a time. Never paste two lines together.
3. `--execute` only ever on `~/sanchay-demo`.
4. Don't debug on stage. Ten seconds, then: "I've got this on the slide."
5. A refusal is the product working. Say so.

## If something breaks

| Problem | Say |
| --- | --- |
| Ollama unavailable | "That stage is optional — it falls back to the local model." |
| "Actions are disabled" after enabling | A refused try used it up. Enable again. |
| Report already exists | Add `--replace` — "files don't get silently overwritten." |
| Browser won't load | Open `~/Downloads/demo.html` directly. |
| Anything else | Back to the slides. |

## After rehearsing

If you ran a real delete, rebuild before the real thing:

```bash
rm -rf ~/sanchay-demo && python3 -m sanchay.demo ~/sanchay-demo
rm -f ~/review.json
```
