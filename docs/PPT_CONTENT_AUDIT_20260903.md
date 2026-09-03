# SANCHAY deck content audit — 03 September 2026

Reviewed file: `C:\Users\Awaiz\Downloads\Slide_deck_content_needed.pptx`

## Verdict

The 11-slide deck is visually coherent and mostly readable, but it is not yet
submission-ready. The largest problem is not design: slides 3–5 and 8–10 describe
an older implementation in which an LLM only narrates a finished plan. SANCHAY
now has an optional constrained Ollama/OpenAI-compatible reasoning stage in the
recommendation path, so the deck must show that stage accurately without
implying that it controls safety or execution.

## Must-fix items

1. **Fill all placeholders.** Slide 1 still contains `Team Leader Name` and
   `Member 1 | Member 2 | Member 3`; slide 11 still says `Contact: [fill in]`.
2. **Replace the old LLM boundary on slide 5.** The model is no longer only an
   optional narrator. It may review prefiltered candidates, confirm an allowed
   review, change one to Keep, and influence ordering inside the allowed set.
   Deterministic gates still own the permitted action classes.
3. **Correct slide 8's dependency claim.** The base package requires
   `prompt-toolkit`; Plotly and pandas remain optional visualization
   dependencies. Use “dependency-light Python core,” not “no required
   third-party dependency.”
4. **Correct the execution claim.** SANCHAY now has guarded `/delete`, `/move`,
   and `/clean` commands. They are disabled by default and require temporary
   permission, `--execute`, an exact confirmation token, and a fresh evidence
   check. Do not say “there is no cleanup executor.” Say “there is no automatic
   executor.”
5. **Repair slide 9's clipped diagram.** The four boxes at the lower left clip
   `size`, `64 KB prefix`, `BLAKE2b-256`, and `byte compare` vertically.
6. **Differentiate cleanup from archive.** Unique files are excluded from
   cleanup, but the learned model may rank them for Archive Review. Statements
   such as “excluded before ranking” must say “excluded before cleanup ranking.”
7. **Add source notes.** Only some slides contain a `[Sources]` block. Add source
   URLs/attribution in speaker notes for C-DAC/MeitY marks, Secure BOSS claims,
   tool comparisons, and any external technical claim.

## Slide-by-slide corrections

### Slide 1 — Title

- Replace the team placeholders and verify the GitHub/contact identity.
- Recommended footer: **No automatic deletion or movement. Human approval and
  deterministic evidence gates retain authority.**

### Slide 2 — Problem & objective

- The core contrast is sound.
- Add the complete problem-statement checklist to the narration: understand
  usage, identify duplicates/potentially unused files, predict requirements,
  recommend cleanup/archive, and keep recommendations safe and explainable.

### Slide 3 — Proposed solution

- Change “unique priority = 0 and never enters the plan” to “unique priority = 0
  for cleanup; it may enter a separate Archive Review list.”
- Updated ranking expression:

  `priority = allocated bytes × unchanged age × (1 − regret) × local cleanup probability × reasoning multiplier`

  The reasoning multiplier is `1` when the second stage is off or unavailable.

### Slide 4 — System architecture

Use this sequence:

`filesystem scan → verified metadata/activity → local usage/action classifier → deterministic allowed-action gate → constrained Ollama/API review → Keep / Cleanup Review / Archive Review → target optimizer → explanation → human approval → guarded action`

Draw unique files into Keep/Archive Review, not into Cleanup Review. Draw a
blocked connection from both AI models to execution.

### Slide 5 — AI & technical approach

Replace “plan → narrator” with these two explicit AI stages:

- **Stage 1: local prediction.** `sanchay_local_action_classifier v1`, a
  three-class multinomial logistic regression trained from 38 disclosed
  synthetic expert-labelled profiles. It uses bounded metadata and positive
  activity observations and abstains to Keep below 45% confidence.
- **Stage 2: constrained reasoning.** Local Ollama or an explicitly configured
  OpenAI-compatible API receives opaque IDs, bounded metadata, local
  probabilities, allowed actions, and verified evidence flags. It returns a
  structured action, confidence, reason codes, and explanation.
- **Authority boundary.** The reasoner can confirm an already-allowed review or
  change it to Keep. It cannot add a protected candidate, invent recovery
  evidence, authorize execution, or bypass human approval. Invalid or
  unavailable output safely falls back to Stage 1.

For the current demo laptop, the installed model is `qwen2.5-coder:7b` through
Windows Ollama. API mode is implemented but no API key is currently configured.

### Slide 6 — Innovation & novelty

- Replace “Below that, SANCHAY shows nothing” with “Below those evidence
  thresholds, SANCHAY withholds the forecast and states why.”
- Qualify the comparison table as a feature comparison for the scoped prototype;
  avoid universal claims about every version or configuration of other tools.

### Slide 7 — Security & safety

- Fix the spacing typo in `advisories , never`.
- Say that local Ollama receives path-free records over fixed loopback. Remote
  API mode must be explicit, HTTPS (except loopback), and environment-keyed.
- State that model output is schema-validated and checked against per-candidate
  allowed actions and evidence-supported reason codes.

### Slide 8 — Implementation & demonstration

- Replace “Python core with no required third-party dependency” with
  “dependency-light Python core plus a prompt-toolkit interactive shell;
  optional pandas/Plotly visualization and Textual dashboard.”
- Add `/ai status` and `/ai ollama qwen2.5-coder:7b` to the demonstration.
- Replace any speaker-note claim that no executor exists with the guarded-action
  boundary described above.

### Slide 9 — Results, impact & scalability

- Repair the clipped hashing-pipeline boxes.
- Change “2 excluded irreplaceable files, out before ranking (2 eligible)” to
  “2 unique files protected from cleanup; eligible only for Keep/Archive
  Review.”
- Add one measured hybrid result: provider/model, number reviewed, number
  confirmed, number changed to Keep, and whether fallback occurred.

### Slide 10 — Future scope & conclusion

- Add collection of consented real-world feedback, hold-out validation,
  probability calibration, drift monitoring, and model-card updates to future
  scope. These are the honest steps needed to move beyond the 38-row synthetic
  bootstrap.
- Replace “Recommendations only. No automatic deletion or file movement” with
  “No automatic deletion or movement; guarded actions remain separate and
  human-authorized.”

### Slide 11 — Thank you

- Fill the contact placeholder.
- Confirm the GitHub repository URL is correct and accessible.

## Recommended 20-second jury answer: “Where is the AI?”

“SANCHAY uses AI twice. First, our local three-class logistic-regression model
predicts Keep, Cleanup Review, or Archive Review from metadata and observed
activity. Second, an optional Ollama or API model reviews only the candidates
and actions that deterministic safety rules already allow, then returns a
structured decision and explanation. If that model is unavailable, invalid, or
contradicts the evidence, SANCHAY falls back safely. Neither model can delete a
file or bypass human approval.”
