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
- Kumar and Chamness report that storage utilization can be non-linear and
  discontinuous, and frame the operational question as the probability of
  reaching capacity within a stated time window rather than one exact date.
  Their Stochastic Estimated Risk model uses Brownian motion with drift. SANCHAY
  adapts only that local, interpretable risk framing; it does not claim the
  paper's production accuracy or validation on Secure BOSS endpoints. Source:
  [Stochastic Estimated Risk for Storage Capacity](https://arxiv.org/abs/1901.10552).
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
- Linux documents that a process sees its own mount namespace through
  `/proc/<pid>/mountinfo`, and shows a bind mount obscuring an existing file at
  its target. SANCHAY therefore counts nested mount points as a topology
  boundary: a directory walk sees the mounted view, not a proof that older
  entries below it are absent. It does not mount, unmount, or remount anything.
  Source: [Linux `mount_namespaces(7)`](https://man7.org/linux/man-pages/man7/mount_namespaces.7.html).
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
- Python documents that `os.walk()` ignores `scandir()` errors by default and
  exposes the failed filename only through an explicit `onerror` callback.
  SANCHAY records count-only coverage evidence instead of silently treating a
  permission-limited walk as a complete inventory. Source: [Python `os.walk`
  documentation](https://docs.python.org/3/library/os.html#os.walk).
- Python documents that `shutil.disk_usage(path)` returns the mounted path's
  total, used, and free space in bytes. SANCHAY records those values separately
  from its readable inventory in schema-6 snapshots, then trends only the used
  series after confirming the same selected root and filesystem device. Source:
  [Python `shutil.disk_usage`](https://docs.python.org/3/library/shutil.html#shutil.disk_usage).
- GNU `du` documents that it estimates filesystem use and returns nonzero on
  failure. That is a useful baseline: a storage estimate must preserve its
  failure boundary rather than silently report a misleading total. Source:
  [GNU Coreutils `du`](https://www.gnu.org/software/coreutils/manual/html_node/du-invocation.html).
- Python documents that `os.statvfs()` exposes a filesystem's free blocks,
  free blocks available to unprivileged users, total file-entry (inode) count,
  free file entries, and free entries available to an unprivileged process;
  Linux documents the same counters in `statvfs(3)`. A byte-capacity check
  alone can therefore miss a full file-entry table, while a free-block figure
  can overstate what an ordinary user may consume. SANCHAY reads these counters
  only in its explicit, mount-root capacity audit and never converts them into
  a deletion or filesystem-policy instruction. Sources: [Python
  `os.statvfs`](https://docs.python.org/3/library/os.html#os.statvfs) and
  [Linux `statvfs(3)`](https://man7.org/linux/man-pages/man3/statvfs.3.html).

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
- Practitioners also report Btrfs snapshots, data hidden beneath a mount point,
  and container-overlay storage as distinct reasons that a directory walk and
  filesystem capacity can diverge. These are examples, not a population study
  or a diagnosis for any particular endpoint. Sources: [r/linuxquestions on
  deleted-open files and hidden mounts](https://www.reddit.com/r/linuxquestions/comments/1cl57ke/),
  [r/linuxquestions on Btrfs snapshots](https://www.reddit.com/r/linuxquestions/comments/rlbye3/),
  and [r/selfhosted on Docker overlay use](https://www.reddit.com/r/selfhosted/comments/1eagm9c/).
- A Linux user reported `ENOSPC` despite free byte space after exhausting ext4
  inodes; commenters in a separate discussion likewise describe inode counts
  as a second capacity metric. These are practitioner accounts, not a
  filesystem-wide incident rate, but they justify surfacing the counters before
  a user is forced into a recovery path. Sources: [r/linuxquestions: ENOSPC
  with free space](https://www.reddit.com/r/linuxquestions/comments/1vtb008/how_to_handle_enospc_on_the_root_filesystem/) and
  [r/linuxadmin: inode exhaustion](https://www.reddit.com/r/linuxadmin/comments/k7n557/removed/).

## Decisions derived from the evidence

| Need | SANCHAY decision | Status |
| --- | --- | --- |
| Avoid catastrophic loss | No automatic deletion or file movement; write a review-only plan instead. | Implemented |
| Meet a stated reclaim target without needless review scope | Exhaust lower recovery-risk classes before a higher-risk class. For a same-risk class of 28 or fewer candidates that can meet the remaining target, use an exact minimum-excess subset search; record a deterministic fallback when the class is larger. | Implemented |
| Make every recommendation auditable | Include class, typed recovery evidence with strength, survivor path for duplicates, observed device/inode/logical-size/allocated-size/mtime-nanoseconds/link count, and a SHA-256 integrity checksum (not a signature). | Implemented |
| Preserve a prior review decision | Refuse to overwrite an existing plan artifact by default. An operator must explicitly request `--replace-plan` to replace it. | Implemented |
| Preserve recovery evidence without inferring source of truth | Keep a deterministic byte-matched evidence peer for duplicate rechecks, but require an operator to choose retention; identify hardlinks by `(device, inode)`, count each inode once, and exclude individual hardlinked paths because one unlink releases no bytes. | Implemented |
| Avoid treating a path swap as duplicate proof | On Linux, walk from the canonical scan-root descriptor with `openat` plus no-follow flags; reject non-regular files or identity drift before/after a content read. | Implemented |
| Avoid collecting tool credentials | Exclude documented Docker, npm, and Terraform credential paths alongside existing cloud, key, vault, and environment-file safeguards before metadata collection or hashing; repeat that known-path gate in content and plan APIs for direct caller inputs. | Implemented |
| Make BOSS storage operations safer | Measure APT archive and persistent systemd-journal storage separately; defer action to the owning tool and approved package/log-retention policy instead of raw file deletion or reclaim-target selection. | Implemented |
| Protect managed application stores | When present, report Docker, containerd, and Flatpak system stores as tool-owned advisories; do not hash, rank, or raw-delete their files. | Implemented |
| Protect generic OS state | Fence boot, configuration, package/cache, log, backup, and service/spool paths before duplicate-content reads. Keep them as measured advisories, not raw deletion candidates; preserve narrower tool-specific guidance where available. | Implemented |
| Explain process-held deleted storage | On Linux, report visible deleted regular files held through `/proc` only as an operational advisory; never signal, restart, truncate, delete, or include them in a reclaim target. | Implemented |
| Keep capacity claims mount-aware | Record the selected Linux mount context. Label Btrfs, overlay, and device-mapper boundaries instead of inferring host-wide, snapshot-aware, or volume-pool capacity; run no filesystem or LVM command. | Implemented |
| Surface covered-path uncertainty | Count nested mount points under the selected root and state that a path walk sees the mounted view; older entries beneath a child mount can contribute to an accounting gap without being visible. In default one-filesystem mode, prune each visible child mount before traversal, including same-device bind mounts; cross-filesystem inventory guards directory identities against recursive bind walks. Preserve only the count in the path-free operator brief; never mount or unmount a path. | Implemented |
| Make capacity disagreement measurable, not actionable | On explicit request, compare filesystem-used blocks with a complete mount-root readable inventory plus visible deleted-open bytes. Label the signed remainder an accounting gap, never reclaimable or a complete diagnosis. | Implemented |
| Detect file-entry exhaustion separately from byte exhaustion | In the same explicit mount-root audit, read POSIX `statvfs` total/free/available inode counters when exposed. Report them as an advisory only; do not infer a cause or nominate a file for deletion. | Implemented |
| Distinguish raw free blocks from user-available blocks | In the explicit mount-root audit, report `statvfs` free versus unprivileged-available block counters as a filesystem-policy boundary, never as a prompt to alter reservation policy. | Implemented |
| Keep scan coverage honest | Count unreadable in-scope directories/files without serialising their paths. Mark the view as readable-file inventory and withhold mtime forecasts plus snapshots/history when coverage is incomplete. | Implemented |
| Gate projected exhaustion dates | Preserve a two-capture measured rate as evidence, but require at least three same-root snapshots and R² >= 0.80 before saying `full in ...`. A product gate can only reduce false precision; it is not a statistical guarantee of future growth. | Implemented |
| Prefer capacity risk to false point precision | On explicit `--risk-horizon DAYS`, use a local Brownian-motion-with-drift hitting-time estimate over mounted-filesystem used bytes. Require seven complete snapshots over seven days, twelve-hour minimum intervals, same root/device, and unchanged capacity; otherwise withhold the probability. The estimate controls no action, alert, or network transfer. | Implemented |
| Contain the optional LLM | Keep narration local by default. Require a separate cloud opt-in and send only opaque candidate IDs with fixed class/size/age metadata; deterministic code retains all decision and action boundaries. | Implemented |
| Avoid crossing a governance boundary silently | Scan one filesystem by default; cross-filesystem traversal requires an explicit flag and is inventory-only across mounts. | Implemented |
| Keep forecasting honest | Label the first pass a readable-inventory mtime estimate. Schema-6 snapshots retain that inventory separately but trend the selected mounted filesystem's reported used bytes; reject legacy or different-device snapshots, and withhold a rate until the history spans 24 hours, rather than mixing metrics or annualising seconds of background activity. Cross-mount scans refuse shared targets and capacity forecasts. | Implemented |
| Keep history evidence intact | Seal each schema-6 aggregate snapshot with a SHA-256 checksum and reject a missing or checksum-mismatched history artifact before a CLI comparison, trend, or risk estimate. Snapshot writing refuses to replace an existing evidence artifact. `--snapshot-history DIR` loads only SANCHAY's explicit timestamped records and appends a new write-once aggregate record after a valid scan; a standalone read-only verifier is available. The checksum detects a mismatch against stored content; it is not a signature, attestation, or authorization. | Implemented |
| Prevent tool output from becoming a cleanup candidate | Exclude explicitly supplied SANCHAY snapshots, plans, reports, and briefs from the readable inventory when they sit under the scan root, while retaining their physical bytes in the mounted-filesystem measurement. | Implemented |
| Support government/BOSS deployment | Keep the core local, dependency-light, inspectable, and suitable for an offline terminal workflow. | Implemented |
| Support monitored secure endpoints without exporting path metadata | Keep the detailed plan and HTML report local. Add a separately requested `--operator-brief` that contains only aggregate evidence, capacity, operational-advisory counts, and, when explicitly requested and assessed, capacity-risk horizon/sample/model metrics. It excludes paths, names, process IDs/names, mount/device sources, free-form model rationale, and content, and makes no network call. | Implemented |
| Improve inclusivity | Add Hindi and other BOSS-language UI strings only after native-speaker review; do not machine-claim localisation. | Planned |

The presentation-ready mapping from cited Secure BOSS capabilities to
SANCHAY's implemented boundaries is maintained separately in
[`CDAC_SECURE_BOSS_FIT.md`](CDAC_SECURE_BOSS_FIT.md). It deliberately separates
observed C-DAC facts from our product-fit inference and nonclaims.

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
