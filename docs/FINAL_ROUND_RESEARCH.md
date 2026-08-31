# Final-round research and product decisions

Captured 31 August 2026. This is a design record, not a claim that any source
endorses SANCHAY or defines the hackathon scoring rubric.

## Source findings

### C-DAC and Secure OS context

- C-DAC describes BOSS as a Debian-derived GNU/Linux distribution with broad
  Indian-language support, relevant to government use; it also identifies use
  by government agencies and defence establishments. Source: [C-DAC Free/Open
  Source Software](https://www.cdac.in/index.aspx?id=st_oss_free_open_source_software).
- A 2026 C-DAC Secure OS tender calls out secure local and distributed storage,
  fault tolerance, redundancy, disaster recovery, observability, accessibility,
  and AI-based performance optimisation. It is useful product context, not a
  hackathon rule. Source: [C-DAC Secure OS tender, pp. 35–36](https://www.cdac.in/index.aspx?dynamicId=NjY2MTA5MjE%3D&id=tenders_viewpdf).
- The SSM portal frames the programme around a sovereign secure OS and national
  challenges. Source: [SSM Portal](https://ssm.cdac.in/).
- Debian documents that `apt-get clean` clears retrieved package files from the
  local archive cache, while `autoclean` only removes packages that can no
  longer be downloaded. Source: [Debian `apt-get(8)`](https://manpages.debian.org/bookworm/apt/apt-get.8.en.html).
- systemd documents that `journalctl --vacuum-size=` removes **archived**
  journals only, so active journals and retention policy still matter. Source:
  [systemd `journalctl`](https://www.freedesktop.org/software/systemd/man/255/journalctl.html).

### Storage-systems research

- Whole-file hashing, fixed-size blocking, and content-defined chunking make
  different recall, compute, and metadata trade-offs; redundancy varies greatly
  with workload and file type. Source: Policroniades and Pratt, [Alternatives
  for Detecting Redundancy in Storage Systems Data](https://www.usenix.org/legacy/publications/library/proceedings/usenix04/tech/general/full_papers/policroniades/policroniades_html/rabinPaper.html).
- Capacity forecasting work uses historical data and models rather than treating
  a single instant as ground truth. Source: Chamness, [Capacity Forecasting in
  a Backup Storage Environment](https://www.usenix.org/conference/lisa11/capacity-forecasting-backup-storage-environment-practice-experience-report).
- POSIX specifies that `O_NOFOLLOW` rejects a symbolic-link final component and
  that descriptor-relative `openat` avoids the path-change race that affects
  ordinary path-based opening. Source: [The Open Group `open()`
  specification](https://pubs.opengroup.org/onlinepubs/9799919799/functions/open.html).

### Practitioner evidence (anecdotal, not population research)

- Linux/self-hosted users explicitly worry about deleting the source copy or a
  hardlink when deduplicating. Source: [r/selfhosted discussion](https://www.reddit.com/r/selfhosted/comments/1r8bn44/dealing_with_duplicates/).
- Linux users often know how to locate disk usage with `ncdu` but cannot tell
  what is safe to remove. Source: [r/linuxquestions discussion](https://www.reddit.com/r/linuxquestions/comments/eriamd/how_can_i_figure_out_what_i_can_delete_to_free_up_space/).
- A recent Debian user reported a root filesystem filled by logs and commenters
  noted that deleting a still-open file does not necessarily return its space.
  This is anecdotal evidence for surfacing journal storage as a policy review,
  not promising an immediate raw-file reclaim. Source: [r/debian discussion](https://www.reddit.com/r/debian/comments/1l6elfa/).

## Decisions derived from the evidence

| Need | SANCHAY decision | Status |
| --- | --- | --- |
| Avoid catastrophic loss | No automatic deletion or file movement; write a review-only plan instead. | Implemented |
| Make every recommendation auditable | Include class, typed recovery evidence with strength, survivor path for duplicates, observed device/inode/logical-size/allocated-size/mtime-nanoseconds/link count, and a SHA-256 integrity checksum (not a signature). | Implemented |
| Preserve source-of-truth and hardlinks | Keep a deterministic duplicate survivor; identify hardlinks by `(device, inode)`, count each inode once, and exclude individual hardlinked paths because one unlink releases no bytes. | Implemented |
| Avoid treating a path swap as duplicate proof | On Linux, walk from the canonical scan-root descriptor with `openat` plus no-follow flags; reject non-regular files or identity drift before/after a content read. | Implemented |
| Make BOSS storage operations safer | Measure APT archive and persistent systemd-journal storage separately; defer action to the owning tool and approved package/log-retention policy instead of raw file deletion or reclaim-target selection. | Implemented |
| Avoid crossing a governance boundary silently | Scan one filesystem by default; cross-filesystem traversal requires an explicit flag. | Implemented |
| Keep forecasting honest | Label the first pass an mtime-derived estimate; capture aggregate local snapshots for observed growth and an explainable local linear trend. | Implemented |
| Support government/BOSS deployment | Keep the core local, dependency-light, inspectable, and suitable for an offline terminal workflow. | Implemented |
| Improve inclusivity | Add Hindi and other BOSS-language UI strings only after native-speaker review; do not machine-claim localisation. | Planned |

## Demo truth boundary

The public browser page is a seeded explanatory demo. It cannot inspect a
visitor's filesystem. A real scan runs through the local CLI, for example:

```bash
sanchay /home/user --plan cleanup-plan.json --snapshot baseline.json
# Run later:
sanchay /home/user --compare baseline.json --snapshot current.json
```

The plan is a recommendation artifact. Before any separate, explicitly
reviewed cleanup action, `sanchay --verify-plan cleanup-plan.json` rechecks the
integrity checksum, each candidate identity including link count, the retained
duplicate, and clean Git HEAD state where applicable. SANCHAY still does not
delete or move files.
