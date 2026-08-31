# Final-round research and product decisions

Captured 31 August 2026. This is a design record, not a claim that any source
endorses SANCHAY or defines the hackathon scoring rubric.

## Source findings

### C-DAC and Secure OS context

- C-DAC describes BOSS as a Debian-derived GNU/Linux distribution with broad
  Indian-language support, relevant to government use; it also identifies use
  by government agencies and defence establishments. Source: [C-DAC Free/Open
  Source Software](https://www.cdac.in/index.aspx?id=st_oss_free_open_source_software).
- C-DAC describes Secure BOSS as a hardened operating system for critical end
  nodes, with full-disk encryption, eToken support, policy management, and
  security logging, monitoring, and alerts. This supports a conservative local
  credential boundary, but is not a claim of C-DAC endorsement or integration.
  Source: [C-DAC Secure BOSS Linux](https://www.cdac.in/index.aspx?id=product_details&productId=SecureBOSSLinux).
- C-DAC further states that Secure BOSS is installed on an LVM-encrypted hard
  disk. This makes it important not to confuse filesystem-free bytes with
  logical-volume or thin-pool headroom. SANCHAY records the visible mount
  boundary but does not infer encryption or manage volumes. Source: [C-DAC
  Secure BOSS Linux](https://www.cdac.in/index.aspx?id=product_details&productId=SecureBOSSLinux).
- A 2026 C-DAC Secure OS tender calls out secure local and distributed storage,
  fault tolerance, redundancy, disaster recovery, observability, accessibility,
  and AI-based performance optimisation. It is useful product context, not a
  hackathon rule. Source: [C-DAC Secure OS tender, pp. 35–36](https://www.cdac.in/index.aspx?dynamicId=NjY2MTA5MjE%3D&id=tenders_viewpdf).
- The SSM portal frames the programme around a sovereign secure OS and national
  challenges. Source: [SSM Portal](https://ssm.cdac.in/).
- Debian documents that `apt-get clean` clears retrieved package files from the
  local archive cache, while `autoclean` only removes packages that can no
  longer be downloaded. Source: [Debian `apt-get(8)`](https://manpages.debian.org/bookworm/apt/apt-get.8.en.html).
- Debian documents `dpkg-query --search` as a package-ownership lookup and
  notes that it does not list files created by maintainer scripts or
  alternatives. Package ownership is therefore useful review evidence, not a
  sufficient automatic-delete rule for every system path. Source: [Debian
  `dpkg-query(1)`](https://manpages.debian.org/bookworm/dpkg/dpkg-query.1.en.html).
- systemd documents that `journalctl --vacuum-size=` removes **archived**
  journals only, so active journals and retention policy still matter. Source:
  [systemd `journalctl`](https://www.freedesktop.org/software/systemd/man/255/journalctl.html).
- Docker documents that `docker system df -v` reports detailed daemon disk use;
  `docker system prune` removes unused containers, networks, images, and build
  cache, while volume pruning is an explicit additional choice. SANCHAY does
  not execute either command: it reports Docker storage as a tool-owned review
  boundary. Source: [Docker disk usage](https://docs.docker.com/reference/cli/docker/system/df/)
  and [Docker prune](https://docs.docker.com/reference/cli/docker/system/prune/).
- Flatpak distinguishes system-wide from per-user installations and documents
  `flatpak uninstall --unused` for unused runtimes and extensions. SANCHAY
  therefore treats the system installation as tool-owned storage rather than
  loose files. Source: [Flatpak documentation](https://docs.flatpak.org/en/latest/using-flatpak.html).
- Docker documents that a Linux user's `~/.docker/config.json` can store
  registry credentials; npm documents registry credentials in the user's
  `.npmrc`; and Terraform documents API tokens in `.terraformrc` or
  `credentials.tfrc.json`. SANCHAY excludes these exact credential paths before
  metadata collection and duplicate hashing. Sources: [Docker login](https://docs.docker.com/reference/cli/docker/login/),
  [npm configuration](https://docs.npmjs.com/cli/v8/configuring-npm/npmrc/), and
  [Terraform CLI configuration](https://developer.hashicorp.com/terraform/cli/config/config-file)
  and [Terraform login](https://developer.hashicorp.com/terraform/cli/commands/login).

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
- POSIX specifies that removing a pathname does not release an open file's
  resources until its last reference is closed. This supports a separate
  process-held-deleted-storage advisory rather than pretending a directory scan
  explains every allocated block. Source: [The Open Group `unlink()`
  specification](https://pubs.opengroup.org/onlinepubs/000095399/functions/unlink.html).
- Linux documents `/proc/<pid>/mountinfo` fields for a mount's device, root,
  mount point, filesystem type, and source. SANCHAY reads those fields locally
  to scope a capacity claim to the selected mount. Source: [Linux kernel procfs
  documentation](https://docs.kernel.org/filesystems/proc.html#proc-pid-mountinfo-information-about-mounts).
- Btrfs documents that ordinary `df` can disagree with its detailed free-space
  accounting and that snapshots share extents. Its `filesystem usage` command
  exposes data, metadata, reserve, and estimated-free context. SANCHAY reports
  the boundary and never runs that command, balances a filesystem, or deletes a
  snapshot. Sources: [Btrfs filesystem usage](https://btrfs.readthedocs.io/en/stable/btrfs-filesystem.html)
  and [Btrfs filesystem concepts](https://btrfs.readthedocs.io/en/latest/btrfs-man5.html).
- Red Hat documents that LVM thin provisioning allocates a thin-pool's storage
  as applications write and can create logical volumes larger than currently
  available extents. SANCHAY therefore does not infer thin-pool headroom from a
  mounted filesystem's free-space value. Source: [Red Hat LVM thin
  provisioning](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/6/html/logical_volume_manager_administration/thinly_provisioned_volume_creation).

### AI security boundary

- OWASP identifies indirect prompt injection when an LLM consumes external
  content such as files, and recommends separating untrusted content and
  enforcing least privilege outside the model. SANCHAY therefore keeps the
  default narrative local; a separately opted-in cloud narrative gets opaque
  IDs and fixed metadata only, never raw file paths or an action capability.
  Source: [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).

### Practitioner evidence (anecdotal, not population research)

- Linux/self-hosted users explicitly worry about deleting the source copy or a
  hardlink when deduplicating. Source: [r/selfhosted discussion](https://www.reddit.com/r/selfhosted/comments/1r8bn44/dealing_with_duplicates/).
- Linux users often know how to locate disk usage with `ncdu` but cannot tell
  what is safe to remove. Source: [r/linuxquestions discussion](https://www.reddit.com/r/linuxquestions/comments/eriamd/how_can_i_figure_out_what_i_can_delete_to_free_up_space/).
- A recent Debian user reported a root filesystem filled by logs and commenters
  noted that deleting a still-open file does not necessarily return its space.
  This is anecdotal evidence for surfacing journal storage as a policy review,
  not promising an immediate raw-file reclaim. Source: [r/debian discussion](https://www.reddit.com/r/debian/comments/1l6elfa/).
- A Debian operator described a Docker-heavy root filesystem with ample space
  elsewhere and uncertainty around encrypted LVM layout and data relocation.
  This is anecdotal evidence for separating container-runtime review from a
  generic free-space recommendation. Source: [r/linuxquestions discussion](https://www.reddit.com/r/linuxquestions/comments/16j9d9c).
- Linux users describe `df` reporting more allocated space than `du` and point
  to deleted files that remain open as one cause. This is practitioner evidence,
  not proof that every `df`/`du` mismatch has that cause. Source:
  [r/linuxquestions discussion](https://www.reddit.com/r/linuxquestions/comments/1kpu4v9).

## Decisions derived from the evidence

| Need | SANCHAY decision | Status |
| --- | --- | --- |
| Avoid catastrophic loss | No automatic deletion or file movement; write a review-only plan instead. | Implemented |
| Make every recommendation auditable | Include class, typed recovery evidence with strength, survivor path for duplicates, observed device/inode/logical-size/allocated-size/mtime-nanoseconds/link count, and a SHA-256 integrity checksum (not a signature). | Implemented |
| Preserve source-of-truth and hardlinks | Keep a deterministic duplicate survivor; identify hardlinks by `(device, inode)`, count each inode once, and exclude individual hardlinked paths because one unlink releases no bytes. | Implemented |
| Avoid treating a path swap as duplicate proof | On Linux, walk from the canonical scan-root descriptor with `openat` plus no-follow flags; reject non-regular files or identity drift before/after a content read. | Implemented |
| Avoid collecting tool credentials | Exclude documented Docker, npm, and Terraform credential paths alongside existing cloud, key, vault, and environment-file safeguards before metadata collection or hashing. | Implemented |
| Make BOSS storage operations safer | Measure APT archive and persistent systemd-journal storage separately; defer action to the owning tool and approved package/log-retention policy instead of raw file deletion or reclaim-target selection. | Implemented |
| Protect managed application stores | When present, report Docker, containerd, and Flatpak system stores as tool-owned advisories; do not hash, rank, or raw-delete their files. | Implemented |
| Protect generic OS state | Fence boot, configuration, package/cache, log, backup, and service/spool paths before duplicate-content reads. Keep them as measured advisories, not raw deletion candidates; preserve narrower tool-specific guidance where available. | Implemented |
| Explain process-held deleted storage | On Linux, report visible deleted regular files held through `/proc` only as an operational advisory; never signal, restart, truncate, delete, or include them in a reclaim target. | Implemented |
| Keep capacity claims mount-aware | Record the selected Linux mount context. Label Btrfs, overlay, and device-mapper boundaries instead of inferring host-wide, snapshot-aware, or volume-pool capacity; run no filesystem or LVM command. | Implemented |
| Contain the optional LLM | Keep narration local by default. Require a separate cloud opt-in and send only opaque candidate IDs with fixed class/size/age metadata; deterministic code retains all decision and action boundaries. | Implemented |
| Avoid crossing a governance boundary silently | Scan one filesystem by default; cross-filesystem traversal requires an explicit flag and is inventory-only across mounts. | Implemented |
| Keep forecasting honest | Label the first pass an mtime-derived estimate; capture aggregate local snapshots for observed growth and an explainable local linear trend. Cross-mount scans refuse shared targets and capacity forecasts. | Implemented |
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
