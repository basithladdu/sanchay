# SSM Hackathon 2026 - Final-round local context

Last reviewed: 2026-09-01, Asia/Kolkata.

This file separates direct organizer communication, the official portal and
guidelines, and local repository facts. It is not a claim of organizer approval
or C-DAC integration.

## Confirmed final-round facts

Source: organizer email supplied in this workspace.

- Team: Zeros and Ones.
- Track: Track 2 - AI at Application Level.
- Problem statement: AI-Powered Intelligent Storage Optimizer for Linux OS.
- Shortlist position: Team 13 of the final-round order.
- Listed presentation time: 14:15, 4 September 2026.
- Event window: 09:30 to 18:30, online or offline in Chennai; exact venue was
  still to be shared in the organizer email.
- Slot length: 15 minutes, including presentation, demo, and jury Q&A.
- Offline travel is participant-borne; organizers said they will arrange food
  during the event as applicable.

## Competitive stakes

Source: official SSM portal homepage and the user-supplied shortlist.

- Five other shortlisted teams address the same storage-optimizer problem, so
  Zeros and Ones has five direct competitors and six teams total in that problem
  statement.
- Track 2 has 21 shortlisted teams in the supplied final-round list.
- The portal lists a per-track prize pool of INR 5,00,000: champion INR
  2,50,000; runner-up INR 1,50,000; second runner-up INR 1,00,000.

## What the official Stage 2 jury scores

Source: https://ssm.cdac.in/guidelines/view, Annexure II, rendered locally on
2026-09-01.

The published Stage 2 rubric has six criteria:

1. Live Demonstration - technical implementation and solution walkthrough.
2. Technical Depth (Q&A) - accurate design and implementation answers.
3. Scalability & Security - scalable design and adequate safeguards.
4. Explainability - whether AI-driven decisions are understandable to an end
   user.
5. Presentation Quality - technical communication.
6. Impact & Alignment - potential impact and alignment with hackathon goals and
   national self-reliance goals.

The rubric says Stage 2 totals 100 marks, but it does not display individual
criterion weights. It says the Stage 1/Stage 2 cumulative-score ratio will be
communicated before Stage 2.

## Track-label conflict to avoid on the final deck

There is a conflict between sources:

- The organizer email and finalist shortlist supplied in this workspace identify
  Zeros and Ones as **Track 2 - AI at Application Level**, Team 13.
- Annexure I, page 11 of the official guidelines PDF labels the same
  AI-Powered Intelligent Storage Optimizer problem as **Track 1 - AI at
  Application Level**.

Use the exact problem statement and team name on the final deck. Do not state a
track number unless the organizer confirms which source controls; if a track
number is compulsory before clarification, preserve the latest team-specific
organizer email wording and keep the source email available.

## What the current checkout demonstrates (not Stage 1 provenance)

Repository: https://github.com/basithladdu/sanchay

- Live demo: deterministic disposable fixture, protected unique file excluded,
  byte-confirmed duplicate with a named evidence peer, hardlinks excluded, and
  a plan that fails closed after the synthetic candidate changes.
- Technical depth: recovery-evidence gate, bounded exact target selection,
  mount-scoped accounting, identity/content revalidation, and local snapshot
  gates.
- Security/scalability: credential/control path fencing, system-managed storage
  deferral, no cleanup executor, one-filesystem default, and bounded optimizer
  behaviour.
- Explainability: typed recovery evidence, frozen decision traces, a visible
  lower-risk-first selection trace, and a local deterministic explanation path.
- Presentation: eight-slide evidence-console deck content and a 15-minute
  runbook exist in the repository, but must be transferred into the official
  organizer template when received.

These are current-head technical facts only. They are **not** evidence that
the same functionality was available in the submitted Stage 1 revision. The
read-only historical audit found that the 24-August snapshot had only the basic
scanner/dedup/ranking workflow and 5 tests; the current evidence-plan and
forecast safeguards came later. See `STAGE1_SNAPSHOT_CAPABILITY_BOUNDARY.md`.
Do not call the current demo a Stage 1 proof unless organizers explicitly
resolve the repository and deadline issue.

Do not claim a trained model, C-DAC deployment, Secure BOSS certification,
autonomous deletion, an exact full-disk date, an independent backup from a
same-filesystem duplicate, or a completed C-DAC integration.

## C-DAC Secure BOSS context for the pitch

Source: https://www.cdac.in/index.aspx?id=product_details&productId=SecureBOSSLinux,
reviewed 2026-09-01.

C-DAC describes Secure BOSS Linux as customised for critical end nodes. Its
published context includes full-disk encryption, service/port/kernel-module
restrictions, logging, monitoring and alerts; ISOC monitoring; intranet and
standalone use; and installation on an LVM-encrypted disk.

Use only this conclusion:

> SANCHAY is a credible local decision-support fit for a hardened Linux
> endpoint because it avoids a required cloud call, has no cleanup executor,
> scopes capacity to the visible mount, and preserves review evidence.

Do not say that it is deployed, certified, approved, integrated with Secure
BOSS, or connected to ISOC. Those claims require C-DAC interface, policy,
security-review, and deployment evidence that this project does not have.

## C-DAC implementation-evidence cue - not the scoring rubric

Source: C-DAC's 2026 Indigenous Multi-variant Operating System RFP,
https://cdac.in/index.aspx?dynamicId=ODI3ODM0MDA%3D&id=tenders_viewpdf,
reviewed 2026-09-01.

The RFP's Network & Storage workstream names architecture/performance reports
or a validated proof of concept/benchmark as evidence types. Its AI & Emerging
Technologies workstream likewise names research/whitepapers or an experimental
prototype/framework-integration note. This is organisational context, not the
hackathon rubric and not evidence that SANCHAY meets a procurement requirement.

Practical pitch consequence: use the final to show a reproducible, constrained
proof with visible inputs, decision trace, verification result, and an honest
boundary. Do not compensate for missing deployment evidence with a decorative
dashboard or an invented integration claim.

## Public benchmark scan - not finalist identity evidence

On 2026-09-01, public GitHub search for the exact storage-optimizer problem
wording returned the following repositories. They are public benchmark examples
only; do not assume any belongs to a shortlisted team or mention them to the
jury.

- https://github.com/subashreesp24/AIStor-Linux-Storage-Optimizer describes a
  dashboard, SHA-256 duplicate detection, "AI-style" prediction, user
  confirmation before destructive action, and planned Bash/systemd integration.
- https://github.com/Hardaksh963/AI-Powered-Intelligent-Storage-Optimizer
  describes a general storage copilot and illustrates an exact estimated
  capacity date from a stated daily growth rate.
- https://github.com/nithyaswinimittapally/storage-optimizer exposed a minimal
  public fixture tree and no readable repository README endpoint at the time of
  review.
- https://github.com/singhprateek813045/Ai-storage---optimizer had a one-line
  public README and a test-oriented Python structure.

Practical differentiation for SANCHAY:

1. Lead with the recovery-evidence decision boundary, not a dashboard.
2. Show physical correctness: allocated blocks, hardlinks, byte-for-byte
   duplicate evidence, and a named survivor that is not called a backup.
3. Show an explicit, lower-risk-first target-selection trace rather than a
   generic priority list.
4. Show a forecast being withheld when its evidence is weak instead of an exact
   full-disk date.
5. Show verification fail closed after a candidate changes. This is stronger
   than simply asking a user to click confirmation before deletion.

## Critical submission-compliance alert

Source: official guidelines section 7.2, visually verified on page 7 of the
official PDF on 2026-09-01.

The official guidelines require the Stage 1 GitHub repository to remain private
until hackathon completion, add `ssm-hackathon` as a collaborator with
appropriate access before the submission deadline, and forbid commits,
modifications, force-pushes, branch replacements, history rewrites, or source
code changes after the submission deadline. They say an attempt to modify the
submitted repository after the deadline may result in immediate disqualification.

The same guidelines also say that:

- AI-assisted development tools, including LLMs and coding assistants, must be
  disclosed in the Technical Description when used during development.
- The proposed AI-driven solution must be developed, executed, and demonstrated
  only on an open-source-based operating system.
- The organizers may inspect repository history, branches, contributors, and
  version history; do not attempt a visibility-only or history-rewrite "fix".

Read-only audit on 2026-09-01 found:

- `docs/SUBMISSION.md` has stated since 2026-08-23 that its fields should be
  copied into the SSM portal and names `https://github.com/basithladdu/sanchay`
  as the GitHub link.
- The remote repository is currently public.
- `ssm-hackathon` has `read` access.
- The remote history contains commits after the portal's listed 25 August 2026
  submission deadline, including work performed during final-round preparation.

The published PDF also contains a conflicting 16 August date in its timeline;
the repository history begins on 23 August. See
`STAGE1_SUBMISSION_COMPLIANCE_AUDIT.md` and
`STAGE1_SNAPSHOT_CAPABILITY_BOUNDARY.md` for exact read-only evidence.

Therefore do not make further commits, change visibility, invite/remove users,
or rewrite history until the team confirms whether this is the repository
submitted through the portal and obtains organizer direction if needed. A late
visibility flip or history rewrite is not assumed to cure the issue.

## External waits

- The available signed-in Gmail account has no matching C-DAC/SSM final-round
  message or PPT template as of 2026-09-01; the forwarded organizer email may
  be in a different team account.
- Muqeeth47 has a valid pending GitHub write invitation.
- shaik2501 has GitHub write access.

## Latest preflight and access verification

Read-only verification on 2026-09-01 against remote-matching commit
`70b08e49583b7eb3ba2549672c71ab6f5c2f7db9`:

- WSL Ubuntu ran the final preflight successfully: 110 tests passed, 5 skipped;
  the disposable safety rehearsal passed; and the synthetic capacity-risk gate
  rehearsal passed. The latter reported a 1.8% seven-day probability only for
  synthetic aggregate snapshots and withheld the result after a synthetic
  capacity resize.
- The source checkout remained clean and its local `HEAD` exactly matched
  `origin/master` after the run.
- GitHub access was rechecked without mutation: `shaik2501` has write access;
  `Muqeeth47` has a pending write invitation created on 2026-08-31; and
  `ssm-hackathon` resolves to read access. The public repository naturally
  exposes read access independently; do not change roles or visibility while
  the submission-repository question remains unanswered.

## Immediate safe next actions

1. Confirm whether this public repository was the Stage 1 portal submission.
2. If it was, request written organizer clarification before any further GitHub
   mutation or visibility change.
3. Receive the official PPT template, then transfer the already prepared
   evidence-first deck content without inventing unsupported claims.
4. Rehearse the final against the published six-item Stage 2 rubric, reserving
   time for the technical Q&A.
5. Use a prepared Linux/BOSS machine or Linux VM for the live final; do not
   demonstrate from Windows.
6. Ask the organizer how to make any required AI-development disclosure without
   altering the frozen Stage 1 submission, if it was not already disclosed.
7. Run `SSM_LINUX_PREFLIGHT.sh /path/to/sanchay` on the final Linux machine. It
   passed against the current repository under WSL Ubuntu on 2026-09-01.
