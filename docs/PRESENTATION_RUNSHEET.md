# SANCHAY — 15-minute presentation run sheet

Deck: `Slide_deck_content_needed.pptx`, 11 slides. Team Zeros and Ones,
Track 2 — AI at Application Level.

**Plan: 10 minutes of deck, 5 minutes of questions.** Every slide gets airtime.
The demo lives inside slide 8 and lasts 90 seconds.

---

## Pre-flight — 15 minutes before you are called

```bash
cd ~/sanchay              # or E:\sanchay
git pull
ollama list               # confirm the service answers and qwen2.5-coder:7b is installed
rm -rf ~/sanchay-demo
python -m sanchay.demo ~/sanchay-demo
python -m sanchay.demo --prove
```

The last command must end in `proof -> PASS`. If it does, everything you claim
on slides 8 and 9 is true on this machine right now.

Then:

1. Open a terminal at font size 18 or larger, dark background, and maximise it.
2. `sanchay` → press Enter past the splash → `/ai status`. Confirm
   `Ollama: available`. If it says unavailable, restart Ollama, or plan to say
   "the reasoning stage is optional and falls back safely" and move on.
3. Put the deck in presenter view on the projector, terminal on your own screen,
   ready to alt-tab.
4. Close everything else. Notifications off.
5. Have `docs/COMMANDS.md` open on a second device for Q&A lookups.

---

## Timing

| Time | Slide | Seconds |
| --- | --- | ---: |
| 0:00 | 1 — Title | 30 |
| 0:30 | 2 — Problem & Objective | 70 |
| 1:40 | 3 — Proposed Solution | 70 |
| 2:50 | 4 — System Architecture | 50 |
| 3:40 | 5 — AI & Technical Approach | 90 |
| 5:10 | 6 — Innovation & Novelty | 50 |
| 6:00 | 7 — Security & Safety | 50 |
| 6:50 | 8 — Implementation + **live demo** | 120 |
| 8:50 | 9 — Results, Impact & Scalability | 50 |
| 9:40 | 10 — Future Scope & Conclusion | 30 |
| 10:10 | 11 — Thank you | 10 |
| 10:20 | **Questions** | 280 |

**If you are behind at slide 6, cut slide 6 to one sentence** ("existing tools
rank consumption; we rank consequence") and move on. Never cut the demo.

**If you are ahead**, slow down on slide 5 — that is the Track 2 slide.

---

## What to say, slide by slide

Speak these as prompts, not a script to read. One idea per breath.

### Slide 1 — Title (30s)

> Good afternoon. We are Zeros and Ones. Our project is SANCHAY — an
> AI-powered storage optimizer for Linux, under Track 2.
>
> One sentence before we start: SANCHAY uses AI twice, and neither stage can
> delete a file. It recommends; a human decides.

Then move. Do not read the team list aloud.

### Slide 2 — Problem & Objective (70s)

> Both of these are 2 GB. A disk-usage tool ranks them identically.
>
> One is a build cache — its own tool rebuilds it in minutes. The other is the
> only copy of a thesis. Deleting it is unrecoverable.
>
> That is the problem. Size tells you what is big. It does not tell you what is
> safe to remove. When the disk fills, hurried users and automated cleaners
> delete the wrong 2 GB.
>
> So our objective is to rank recovery evidence before anything is recommended,
> and leave every irreversible step to a human.

Point at the In-scope / Out-of-scope band and say: **"We are explicit about what
we do not do."** That single line buys credibility for the whole talk.

### Slide 3 — Proposed Solution (70s)

> We call it Regret-Aware Storage Intelligence. Regret is the cost of recovery
> — not a confidence score.
>
> Priority is allocated bytes, times unchanged age, times one minus regret,
> times the local cleanup probability, times the reasoning multiplier.
>
> Look at the last row. A unique file has regret 1.00, so its cleanup priority
> is exactly zero. It can never be recommended for cleanup. It may still be
> ranked for Archive Review, which is a different list.
>
> And a hardlink is not a duplicate — unlinking one name frees nothing, so we
> count it once.

### Slide 4 — System Architecture (50s)

> Scan, then recovery evidence, then the protected-file gate, then a review-only
> plan, then a human.
>
> The important word is gate. It runs **before** any model may speak, so the
> reasoner only ever sees candidates and actions that are already allowed.
>
> Every output is a checkable artifact: the plan carries a SHA-256, the snapshot
> is write-once, the operator brief has no paths in it at all.

### Slide 5 — AI & Technical Approach (90s) — your Track 2 slide

> This is where the AI is, and there are two stages.
>
> Stage one is local and always on: a three-class logistic regression trained on
> 38 disclosed synthetic profiles. It predicts Keep, Cleanup Review, or Archive
> Review from metadata and observed activity. It abstains to Keep below 45%
> confidence. The plan records the probabilities, the factors, the model
> version, and the checksum of the training data.
>
> Between the stages sits the deterministic gate.
>
> Stage two is optional: a local Ollama model, or a configured OpenAI-compatible
> API. It receives opaque candidate IDs, bounded metadata, the local
> probabilities and the allowed actions — never a path, never file content. It
> returns a structured decision under a strict schema.
>
> And here is the boundary. It may confirm a review or downgrade one to Keep. It
> cannot add a protected candidate, invent evidence, authorize execution, or
> bypass approval. If it is unavailable or returns invalid output, we fall back
> to stage one and record why.

Read the `selection 1` / `selection 2` lines off the capture: **"lower-risk class
first — the cache before the duplicate."**

### Slide 6 — Innovation & Novelty (50s)

> Three things are new here.
>
> Regret as a first-class ranking term — consequence, not consumption.
>
> The named evidence peer: a duplicate is only ever recommended alongside the
> file it byte-matches, so a human can recheck the claim independently.
>
> And forecasts that refuse false precision. Runway needs three snapshots, 24
> hours, and R-squared above 0.80. Risk needs seven days. Below that we show
> nothing.
>
> Existing tools rank consumption. We rank consequence — and when we are unsure,
> we withhold.

### Slide 7 — Security & Safety (50s)

> Fail-closed by default. File actions are disabled until you enable them, one
> command at a time, with an exact confirmation token and a fresh evidence
> recheck.
>
> The core is local. One filesystem by default. Package and service state stays
> a tool-owned advisory — we never treat APT or journal files as raw deletion
> candidates.
>
> The operator brief is path-free: no roots, names, PIDs, or content leave the
> machine.
>
> This is designed to **fit** a sovereign secure Linux operating model. We are
> not claiming any endorsement.

Say "fit". Never "approved", "certified", or "deployed".

### Slide 8 — Implementation + live demo (120s)

Talk for 30 seconds, then switch to the terminal.

> Dependency-light Python core, an interactive shell, optional dashboard and
> HTML report, and CI running the full suite plus this safety rehearsal on four
> Python versions on every push.
>
> Rather than describe the proof, I will run it.

**Alt-tab. Run one command:**

```bash
python -m sanchay.demo --prove
```

Walk the output line by line as it appears — it takes seconds:

> The unique thesis file stayed out of the plan. The duplicate was admitted only
> with its byte-confirmed peer named. Two hardlink entries excluded. 729,088
> bytes selected for review. Then we mutated one cache file, and verification
> failed closed. Bottom line: no file was deleted, moved, or transmitted.

**Then alt-tab back.** Do not run `/delete`, `/move`, or `/clean` live.

If the terminal misbehaves for more than 10 seconds, say **"I have this
captured on the next slide"** and move on. Never debug on stage.

### Slide 9 — Results (50s)

> Measured on the deterministic fixture: six entries, 1.3 MB, one duplicate
> group at 512 KB, two unique files protected from cleanup.
>
> We asked for 600 KB; it selected 712 KB and touched zero protected files.
>
> The hybrid run: four candidates reviewed, four confirmed, none changed to
> Keep, no fallback.

**If asked why nothing changed:** the fixture contains four unambiguous cases,
so agreement is expected. The claim is not that the model corrects the
classifier often — it is that it *can* downgrade to Keep and *cannot* promote
anything riskier.

> On scale: tiered hashing puts the expensive stage on the smallest set — size,
> then a 64 KB prefix, then BLAKE2b, then a byte compare.

### Slide 10 — Future Scope & Conclusion (30s)

> Proposed next, not built: more evidence classes, BOSS-family packaging,
> multi-host aggregation of path-free briefs, and operator-tunable regret
> weights recorded in the plan.
>
> To close. SANCHAY does not ask you to trust a cleanup model. It gives you
> evidence to review before an irreversible step.

Stop talking. Let that land.

### Slide 11 — Thank you (10s)

> Thank you. The repository is public and the questions are welcome.

---

## The eight questions you will get

**"Where exactly is the AI?"**
Two stages. A local logistic-regression classifier that always runs, and an
optional constrained reasoner that reviews only pre-approved candidates. Slide 5
shows both. The plan records which one ran.

**"How do I know the LLM actually ran?"**
`reasoning_model.applied` and `.status` in the plan JSON. Per-candidate fields
are filled by the fallback too, so those are not proof — `applied: true` is.

**"What is your accuracy?"**
The model card reports training fit on 38 rows and explicitly labels it a
bootstrap disclosure, not a generalisation claim. We publish the training data
and its checksum so the claim can be checked rather than believed.

**"Why not just delete the obvious files automatically?"**
Matching bytes or a cache path is not proof of ownership, retention policy, or
intent. We create a reviewable plan and verify it again before a human acts.

**"What if the AI is wrong?"**
It cannot promote a file into a riskier class. Unique files are excluded before
the model is consulted. Worst case it confirms something a human then rejects.

**"Does this delete anything?"**
Guarded `/delete`, `/move`, and `/clean` exist. They are disabled by default and
need one-use permission, `--execute`, an exact confirmation token, and a fresh
evidence recheck. There is no automatic executor.

**"Why probability instead of an exact full-disk date?"**
Workloads are not linear. We withhold the forecast until there is strong
same-mount history, and the forecast controls no action.

**"Does it work on BOSS?"**
It is designed to fit that operating model — local, dependency-light, one
filesystem, no network in the core path. We are not claiming an endorsement or
a deployment.

---

## Do not say

- "It automatically cleans your disk."
- "There is no cleanup executor." (There is one; it is guarded.)
- "C-DAC approved / certified / deployed."
- "It guarantees you will not lose files."
- "We tested it on thousands of machines."
- Any exact date a disk will fill.

## If something breaks

| Problem | Say this, then move |
| --- | --- |
| Ollama unavailable | "The reasoning stage is optional and falls back to the local classifier — that is the designed behaviour." |
| Terminal or projector fails | "I have this captured on the slide." |
| Scan slower than expected | "This runs in the background; the prompt stays live." Then switch to the captured output. |
| Question you cannot answer | "I do not have that measured. What we can show is…" — never invent a number. |

## If you split the talk

Three of you, three blocks: slides 1–4, slides 5–7 plus the demo, slides 8–11
and Q&A. Hand over on a slide change, never mid-slide, with one word: "Basith
will take the architecture." Rehearse the two handovers once — that is where
teams lose 30 seconds.
