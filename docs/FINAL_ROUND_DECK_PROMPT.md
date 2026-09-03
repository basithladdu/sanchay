# Final-round slide-deck prompt — SANCHAY

A complete, self-contained build prompt for the official organizer template
`TEAM_NAME – TRACK_ID.pptx` (AI Enabled Operating System Hackathon 2026, C-DAC /
MeitY). Hand this whole file to whoever — or whatever — builds the deck.

Companion documents: [`FINAL_ROUND_DECK_CONTENT.md`](FINAL_ROUND_DECK_CONTENT.md)
(the eight-slide core narrative), [`FINAL_ROUND_JURY_BRIEF.md`](FINAL_ROUND_JURY_BRIEF.md)
(spoken positioning, hostile Q&A — keep off the visible slides),
[`FINAL_ROUND_RUNBOOK.md`](FINAL_ROUND_RUNBOOK.md) (the demo commands),
[`CDAC_SECURE_BOSS_FIT.md`](CDAC_SECURE_BOSS_FIT.md) and
[`FINAL_ROUND_RESEARCH.md`](FINAL_ROUND_RESEARCH.md) (sources).

---

## 1. The prompt

> Build the final technical presentation for **SANCHAY** inside the official
> organizer template `TEAM_NAME – TRACK_ID.pptx`, without altering the
> template's chrome, palette, logos, or geometry. Deliver exactly 20 slides,
> numbered `N / 20`, following the slide map in §6. Every visible claim must be
> traceable to the repository; every external claim carries a `[Sources]` block
> in the speaker notes. The deck recommends — it never asserts that SANCHAY
> deletes, moves, guarantees, or predicts anything with certainty. Rename the
> output to `Zeros_and_Ones – Track2.pptx` before submission.

---

## 2. Template facts (measured, do not guess)

| Property | Value |
| --- | --- |
| Slide size | **20.00 in × 11.25 in** (16:9, oversized canvas — not 13.3 in) |
| Slides supplied | 11 (1 title, 9 section headers, 1 closing) |
| Required final length | **20 slides**, footer reads `N / 20` |
| Theme font | **Calibri** (major and minor) |
| Layout used by every slide | `slideLayout7` ("Blank") — all content is free-floating shapes |
| Bundled media | C-DAC logo (`image2.png`), MeitY/emblem art (`image3.jpeg`), two 77×77 icons, one unused stock image |

### Palette

| Role | Hex | Where |
| --- | --- | --- |
| Deep navy background | `071539` | Title slide, closing slide |
| Navy panel / rule | `17306E`, `0F2666`, `1B3A82` | Dark-slide bands |
| Title ink | `0B1F5C` | Content-slide titles (42 pt bold) |
| Gold eyebrow | `B08A2E` | Section label above the title (15.76 pt bold) |
| Footer grey | `8992A6` (light slides) / `6B7BB0` (dark slides) | Footer + page number, 12 pt |
| Ice blue | `CFE0FF` | Dark-slide subtitles and links |
| Muted blue label | `8FA3D9` | Title-slide field labels (12.75 pt bold) |
| Body blue-grey | `AEB9DC` | Title-slide ministry lines (20.51 pt) |
| Orange accent | `EF6211` | `TEAM NAME` on the title slide (42 pt bold) |
| White | `FFFFFF` | Dark-slide headings and field values |

Content slides are **white**; only slides 1 and 20 are navy. Keep it that way —
the dark/light/dark sandwich is the template's own structure.

### Geometry of a content slide (inches)

| Element | Position | Size | Type |
| --- | --- | --- | --- |
| Gold section eyebrow | 0.75, 0.48 | 13.51 × 0.45 | 15.76 pt bold `B08A2E` |
| Logo lockup (C-DAC) | 17.84, 0.53 | 1.43 × 0.98 | image |
| Emblem freeform | 15.51, 0.48 | 1.37 × 1.19 | image |
| **Slide title** | 0.85, 0.89 | 14.21 × 0.79 | **42 pt bold `0B1F5C`** |
| Footer text | 0.75, 10.72 | 12.91 × 0.42 | 12 pt `8992A6` |
| Page number | 18.01, 10.72 | 1.25 × 0.42 | 12 pt `8992A6` |
| **Free content band** | **0.85, 1.95** | **18.30 × 8.45** | yours |

Footer text, verbatim:
`C-DAC  |  MINISTRY OF ELECTRONICS AND INFORMATION TECHNOLOGY (MeitY), GOVERNMENT OF INDIA`

### Title slide (slide 1) fields

Replace every bracketed field, then delete the template's own instruction line
("Replace all bracketed fields with your project-specific information.").

| Label (12.75 pt bold `8FA3D9`) | Value (18.76 pt `FFFFFF`) |
| --- | --- |
| `PROJECT TITLE` | SANCHAY — Evidence-first storage decisions for Linux |
| `TEAM LEADER / PARTICIPANT` | *(team leader's name)* |
| `TRACK` | Track 2 — AI at Application Level |
| `TEAM MEMBERS` | *(full roster, comma separated)* |
| `PROBLEM STATEMENT` | AI-Powered Intelligent Storage Optimizer for Linux OS |

Fixed text already on the slide, leave untouched: `AI ENABLED OPERATING SYSTEM
HACKATHON 2026` (58 pt bold white), `FINAL TECHNICAL PRESENTATION` (25.51 pt
`CFE0FF`), the two MeitY lines (20.51 pt `AEB9DC`), and `1 / 20`. Set the orange
`TEAM NAME` shape to **Zeros and Ones**.

### Closing slide (slide 20)

`THANK YOU` (69 pt bold white) stays. Fill:
`GitHub: https://github.com/basithladdu/sanchay` and `Contact: <team email>`
(18.76 pt `CFE0FF`). A QR code is optional and only if it has been tested from
the presentation machine. Page number `20 / 20`.

### Section headers supplied by the template (slides 2–10, in order)

1. Problem Statement & Objective
2. Proposed Solution
3. System Architecture
4. AI & Technical Approach
5. Innovation & Novelty
6. Security & Safety
7. Implementation & Demonstration
8. Results, Impact & Scalability
9. Future Scope & Conclusion

Each becomes **two slides** — a claim slide and a proof slide — which is exactly
what fills 20 pages: `1 title + (9 × 2) + 1 closing`.

---

## 3. Project facts the deck may assert

All of these are grounded in the repository. Nothing outside this list belongs on
a visible slide.

**Identity.** SANCHAY (संचय) is a local, review-first storage *decision layer*
for Linux. Scans, reports, and plans never change files. Team Zeros and Ones,
Track 2 — AI at Application Level.

**Core model.** Regret-Aware Storage Intelligence:
`Priority = reclaimable allocated bytes × unchanged-age × (1 − regret)`

| Evidence class | Regret | Review boundary |
| --- | ---: | --- |
| Regenerable cache or build output | 0.02 | Review through its owning tool |
| Byte-confirmed duplicate | 0.10 | A named evidence peer remains; a human selects retention |
| Clean Git HEAD file | 0.20 | Confirm the project owner accepts removal |
| Unique or otherwise unproven file | 1.00 | Excluded from the plan (priority 0.0) |

**Gates and boundaries.**
- Protected-file gate runs *before* ranking: unique, untracked, uncached,
  credential/control, managed-OS, and hardlinked entries never enter the plan.
- The plan is JSON with typed recovery evidence and a SHA-256 integrity
  checksum — it detects accidental change, it is **not** a digital signature.
- File actions are disabled by default and need, in order: temporary permission,
  explicit execution, exact confirmation, and a fresh evidence recheck.
- Allocated bytes are used where the platform exposes them. A hardlink shares a
  `(device, inode)` identity, counts once, and is not reclaimable — unlinking one
  entry releases no physical storage.
- Duplicate chain: `same size → 64 KB prefix → BLAKE2b-256 digest →
  byte-for-byte confirmation → named evidence peer → identity recheck`.
  A match never identifies the authoritative copy and never proves a backup.
- Target reclaim: bounded exact subset search for a same-risk class of up to 28
  candidates; a larger class records a deterministic greedy fallback in the plan.
  It never expands into protected files to satisfy a target.
- Runway forecast is withheld unless: same root/device, ≥ 24 h of history,
  ≥ 3 snapshots, and R² ≥ 0.80. Capacity-risk probability needs 7 complete
  same-capacity snapshots across 7 days. No file, volume, alert, or network
  action follows from a forecast.
- Managed storage (APT, journal, Docker, containerd, Flatpak, boot, config,
  service state) is surfaced as a tool-owned advisory, never as a raw
  file-deletion candidate.
- The operator brief is path-free: no roots, paths, names, PIDs, mount sources,
  or content leave the machine; it is write-once by default.
- Optional narration (cloud, or local loopback Ollama) is separately opt-in,
  receives only opaque IDs plus fixed class/size/age metadata, and cannot add
  candidates, reorder gates, or execute an action.

**Surfaces.** `sanchay` interactive shell with a slash-command palette,
`sanchay-ui` Textual dashboard, self-contained Plotly HTML treemap report,
snapshot/forecast/capacity-audit subcommands, GitHub Actions CI, and
`python -m sanchay.demo --prove` — a disposable fixture rehearsal that never
deletes, moves, or transmits a file.

---

## 4. Claims that must NOT appear

Carried forward from [`FINAL_ROUND_DECK_CONTENT.md`](FINAL_ROUND_DECK_CONTENT.md);
the superseded `docs/SANCHAY.pptx` draft contains several of these.

- Track 1, or any track other than **Track 2 — AI at Application Level**.
- Any guarantee of safety, correctness, or recovery.
- An exact full-disk date, or a forecast presented as certainty.
- Legal or regulatory compliance claims.
- Test-coverage percentages, benchmark numbers, or user counts not produced by
  the repository's own suite.
- C-DAC endorsement, deployment, Secure BOSS certification, or an ISOC API.
  The correct phrasing is *"designed to fit that operating model."*
- "Automatically cleans", "frees space for you", or anything implying autonomous
  deletion.

---

## 5. Visual direction

- **One claim, one composition per slide.** The slide title states the section;
  a single bold conclusion line states the claim; the body proves it.
- Use the SANCHAY evidence-console language: white field, navy ink, restrained
  green/blue/red evidence accents, small monospace labels for commands, paths,
  and hashes (Consolas or Courier New).
- Prefer these compositions, and vary them across the deck: two-column contrast,
  left-to-right pipeline flow, evidence ladder (numbered stages), large stat
  callout with a small caption, before/after comparison, one real terminal
  capture.
- **Do not** use: decorative accent stripes or color bars, an underline rule
  under a title, generic AI/robot/cloud stock art, fake telemetry dashboards,
  icon grids used as filler, or centered body text.
- Every slide needs one visual element. No slide is title + bullets alone.
- Minimum 0.5 in margins; 0.3–0.5 in between blocks, used consistently.
- Body text 16–20 pt (this canvas is 20 in wide — 14 pt reads small from the
  back of a hall); section sub-headers 22–26 pt bold; stat callouts 60–72 pt.
- Source URLs and technical qualifications go in the **speaker notes**, never in
  the visible body copy.

---

## 6. Slide map — all 20

Format per slide: **title** (goes in the 42 pt title box), *eyebrow* (gold
section label), the visible claim, the body, the visual, and the notes.

### Slide 1 — Title *(template slide 1, dark)*
Fill the five bracketed fields per §2. Team name shape → **Zeros and Ones**.
Notes: 30-second opening — local, review-first, recommends only.

### Slide 2 — Problem Statement & Objective
*Eyebrow:* Problem Statement & Objective
**Claim:** Size does not tell us what is safe to remove.
**Body:** Two-column contrast, no bullets.

| Same 2 GB | Different consequence |
| --- | --- |
| Regenerable build cache (`node_modules/.cache`) | The only copy of a thesis, DB export, or document |

**Visual:** two equal-weight blocks, identical size labels, opposite outcome
colors (neutral vs red).
**Notes:** a size-only cleaner cannot tell these apart; hurried users and
automated cleaners cause irrecoverable loss. `[Sources] README.md#problem`.

### Slide 3 — Problem Statement & Objective
*Eyebrow:* Problem Statement & Objective
**Claim:** Rank recovery evidence, not bytes.
**Body:** Objective in one line, then scope as two short columns —
*In scope:* local scan, evidence classification, review-only plans, capacity
evidence, operator handoff. *Out of scope:* autonomous deletion, cloud upload of
paths or content, cross-mount capacity claims, guaranteed forecasts.
**Visual:** in/out-of-scope split with a clear boundary line down the middle.
**Notes:** state the non-goals aloud — juries reward an explicit boundary.

### Slide 4 — Proposed Solution
*Eyebrow:* Proposed Solution
**Claim:** Regret-Aware Storage Intelligence.
**Body:** The formula, set large and centered as the hero:
`Priority = reclaimable allocated bytes × unchanged-age × (1 − regret)`
with one line under it: *for an irreplaceable unique file regret = 1.00, so
priority is 0.0 and it never reaches the plan.*
**Visual:** formula as a 44–54 pt callout; three tiny worked chips beneath it.
**Notes:** regret is the cost of recovery, not a confidence score.

### Slide 5 — Proposed Solution
*Eyebrow:* Proposed Solution
**Claim:** Four evidence classes, one hard exclusion.
**Body:** the evidence table from §3 (class / regret / review boundary), with
the 1.00 row visually separated as *excluded before ranking*.
**Visual:** table where the regret column is a small bar, and the excluded row
sits below a boundary rule.
**Notes:** the protected-file gate runs before ranking, not as a filter after.

### Slide 6 — System Architecture
*Eyebrow:* System Architecture
**Claim:** Evidence is a gate, not a score.
**Body:** left-to-right pipeline —
`local scan → recovery evidence → protected-file gate → review-only plan → human decision`
with the three evidence routes branching into the gate: byte-confirmed
duplicate, clean Git HEAD, narrow regenerable cache/build path.
**Visual:** single-row flow, the gate drawn as an actual gate; a dashed
"excluded" path exiting downward (unique, untracked, uncached,
credential/control, managed-OS, hardlinked).
**Notes:** nothing crosses the gate without a typed evidence record.

### Slide 7 — System Architecture
*Eyebrow:* System Architecture
**Claim:** Every output is a write-once, checkable artifact.
**Body:** four artifacts as compact cards — review plan (JSON + SHA-256
checksum), mount snapshot (schema-6, write-once), path-free operator brief,
interactive HTML report / Textual TUI. One line each on what it proves and what
it deliberately does not.
**Visual:** 2 × 2 card grid, monospace filenames.
**Notes:** the checksum detects accidental change; it is not a signature.

### Slide 8 — AI & Technical Approach
*Eyebrow:* AI & Technical Approach
**Claim:** The decision layer is explainable and evidence-bounded.
**Body:** three numbered stages — (1) recoverability scoring from typed
evidence, (2) constrained target selection: exact subset search up to 28
same-risk candidates, deterministic greedy fallback recorded in the plan,
(3) local observed-growth models with withholding gates.
**Visual:** the `--target-reclaim 600K` trace as the worked example:
`need 600K → 204,800 B regenerable cache → 524,288 B byte-confirmed duplicate → review plan`
**Notes:** lower-risk class first; excess minimized only inside eligible
evidence; never expands into protected files.

### Slide 9 — AI & Technical Approach
*Eyebrow:* AI & Technical Approach
**Claim:** The language model explains; it never decides.
**Body:** what narration receives (opaque IDs, fixed class/size/age metadata),
what it cannot do (add candidates, reorder gates, execute actions), and the
three modes (deterministic local narrative by default; opt-in cloud; opt-in
loopback Ollama for standalone Linux).
**Visual:** a one-way arrow from the plan to the narrator, with a blocked
return arrow.
**Notes:** answers "where is the AI?" — say it before the jury asks.

### Slide 10 — Innovation & Novelty
*Eyebrow:* Innovation & Novelty
**Claim:** Withholding a recommendation is a feature.
**Body:** three novelties — regret as a first-class ranking term; the named
byte-confirmed *evidence peer* that a human can recheck independently; forecast
gates that refuse false precision (R² ≥ 0.80, ≥ 3 snapshots, ≥ 24 h; risk needs
7 days × 7 complete snapshots).
**Visual:** evidence ladder, four rungs, with the top rung greyed out and
labelled *withheld — evidence insufficient*.
**Notes:** most tools degrade gracefully into a guess; SANCHAY degrades into
silence.

### Slide 11 — Innovation & Novelty
*Eyebrow:* Innovation & Novelty
**Claim:** Existing tools rank consumption; SANCHAY ranks consequence.
**Body:** comparison table — disk-usage explorers (ncdu, baobab), duplicate
finders (fdupes, rdfind), cleaners (BleachBit) vs SANCHAY, across four rows:
*what it ranks*, *what it proves*, *who decides*, *what it does when unsure*.
**Visual:** comparison columns; SANCHAY column emphasised by weight, not by a
stripe.
**Notes:** name the tools honestly; do not claim they are unsafe, claim they
answer a different question.

### Slide 12 — Security & Safety
*Eyebrow:* Security & Safety
**Claim:** Fail-closed by default.
**Body:** the action gate as an ordered chain — actions disabled by default →
temporary permission → explicit execution → exact confirmation → fresh evidence
recheck → single guarded action; plus: plan verification re-runs before a human
acts, and one synthetic cache mutation makes `--verify-plan` fail closed.
**Visual:** the chain with the fail-closed exit drawn at every link.
**Notes:** demonstrate this live on slide 15.

### Slide 13 — Security & Safety
*Eyebrow:* Security & Safety
**Claim:** Designed to fit a sovereign secure Linux operating model.
**Body:** four proof points — local core, no file contents transmitted by the
core workflow; one filesystem by default, no shared capacity claim across
mounts; managed OS state stays a tool-owned advisory; the operator brief is
path-free (no roots, paths, names, PIDs, mount sources, content).
**Visual:** a boundary diagram: endpoint inside, everything outside the line
labelled *not transmitted*.
**Notes:** phrase as *fit*, never as endorsement or certification.
`[Sources] docs/CDAC_SECURE_BOSS_FIT.md`.

### Slide 14 — Implementation & Demonstration
*Eyebrow:* Implementation & Demonstration
**Claim:** Dependency-light core, optional surfaces.
**Body:** stack and structure — Python core with no required third-party
dependency; optional extras for the Textual dashboard and Plotly report;
`sanchay/` module map (scan, dedup, plan, managed, snapshot, forecast, report,
actions, shell); GitHub Actions CI running the full suite plus a final-round
rehearsal.
**Visual:** the interactive shell screenshot (`docs/tui.png`) beside a compact
module list.
**Notes:** editable install, `pip install -e .[viz]` for the report.

### Slide 15 — Implementation & Demonstration
*Eyebrow:* Implementation & Demonstration
**Claim:** The proof is controlled, deterministic, and repeatable.
**Body:** the demo order, exactly as rehearsed —
1. `capstone-thesis.txt` is absent from the plan;
2. a duplicate carries a named byte-confirmed evidence peer;
3. hardlink aliases are excluded from reclaimable storage;
4. `--target-reclaim 600K` prints a lower-risk-first selection trace, with the
   review table labelled priority, not execution order;
5. `--verify-plan` passes, then fails closed after one synthetic cache mutation.
**Visual:** one real terminal capture from the fixture — not a mockup.
**Notes:** `python -m sanchay.demo --prove` from the repository root; disposable
fixture only. Commands in `docs/FINAL_ROUND_RUNBOOK.md`.

### Slide 16 — Results, Impact & Scalability
*Eyebrow:* Results, Impact & Scalability
**Claim:** Evidence-bounded results, stated as measured.
**Body:** the fixture result as a stat row — bytes classified, candidates
admitted, candidates excluded by the protected-file gate, exact target met with
zero protected files touched. Each number labelled *measured on the
deterministic fixture*.
**Visual:** three or four large stat callouts (60–72 pt) with 12–14 pt captions;
the treemap report as a supporting thumbnail.
**Notes:** never generalize fixture numbers into a performance claim.

### Slide 17 — Results, Impact & Scalability
*Eyebrow:* Results, Impact & Scalability
**Claim:** Scales by boundary, not by cluster.
**Body:** tiered fast hashing (size → 64 KB prefix → BLAKE2b-256 → byte
compare) keeps duplicate confirmation cheap; per-mount accounting keeps
capacity claims honest at any volume count; snapshot history is local,
operator-chosen, and needs no scheduler or service.
**Visual:** the hashing funnel, showing how many candidates survive each stage.
**Notes:** the expensive stage runs on the smallest set.

### Slide 18 — Future Scope & Conclusion
*Eyebrow:* Future Scope & Conclusion
**Claim:** The roadmap extends evidence, not authority.
**Body:** four items, each phrased as an evidence extension — additional typed
evidence classes with published review boundaries; packaging for BOSS-family
distributions; multi-host aggregation of path-free briefs; operator-tunable
regret weights with the plan recording the weights used. Mark each as *proposed*.
**Visual:** a simple horizon list, no timeline promises.
**Notes:** be explicit that none of this is implemented today.

### Slide 19 — Future Scope & Conclusion
*Eyebrow:* Future Scope & Conclusion
**Claim:** **SANCHAY does not ask users to trust a cleanup model. It gives them
evidence to review before an irreversible step.**
**Body:** sparse — the claim, and the one-line decision boundary: *recommendations
only; no automatic deletion or file movement.*
**Visual:** whitespace. One small evidence-chain mark.
**Notes:** land this line, then stop talking.

### Slide 20 — Thank you *(template slide 11, dark)*
GitHub link, contact email, page `20 / 20`. Optional tested QR code.

---

## 7. How to build it

The template's text is free-floating shapes on a Blank layout, so `python-pptx`
placeholder filling does not apply — edit the slide XML, or rebuild the shapes at
the coordinates in §2.

```bash
python3 -c "import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall('unpacked')" "TEAM_NAME – TRACK_ID.pptx"
# duplicate a section slide to create its second page — structure BEFORE content
python scripts/add_slide.py unpacked/ slide2.xml --after slide2.xml
# reorder or delete: edit <p:sldIdLst> in ppt/presentation.xml, then
python scripts/clean.py unpacked/
# edit ppt/slides/slideN.xml, then repack from inside the directory
(cd unpacked && rm -f ../out.pptx && zip -Xr ../out.pptx .)
python scripts/office/validate.py out.pptx --original "TEAM_NAME – TRACK_ID.pptx"
```

Rules that bite on this specific deck:

- Do **all** structural work (add, delete, reorder) before editing any content —
  `add_slide.py` copies a slide verbatim.
- Parse XML with `defusedxml.minidom`; round-tripping through
  `xml.etree.ElementTree` rewrites namespace prefixes and corrupts the deck.
- One `<a:p>` per list item, copying the sibling `<a:pPr>`; never a literal `•`.
- `xml:space="preserve"` on any `<a:t>` with leading or trailing spaces.
- Renumber every footer page number after the deck reaches 20 slides — the
  template ships every section slide stamped `3 / 20`.

## 8. QA checklist before submission

1. `markitdown out.pptx | grep -iE "\bx{3,}\b|lorem|ipsum|TODO|\[insert|\[PROJECT|\[TRACK|\[TEAM|\[EMAIL|\[LINK"` returns nothing.
2. `python scripts/office/validate.py out.pptx --original "TEAM_NAME – TRACK_ID.pptx"` passes.
3. Page numbers read `1 / 20` … `20 / 20`, in order, with no `3 / 20` left.
4. Render to images and inspect every slide for text overflow, overlap, footer
   collisions, and margins below 0.5 in.
5. Every external claim has a `[Sources]` note; no claim from §4 appears.
6. The demo capture on slide 15 is a real run of the current fixture.
7. Filename is `Zeros_and_Ones – Track2.pptx` (team name – track id).
