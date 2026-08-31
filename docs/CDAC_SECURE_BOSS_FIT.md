# SANCHAY fit for the Secure BOSS operating context

This is a source-bound presentation aid, not a claim that C-DAC has integrated,
endorsed, certified, or scored SANCHAY.

## What C-DAC currently describes

C-DAC describes Secure BOSS as a hardened operating system for **critical end
nodes** in defence and strategic sectors. Its stated controls include full-disk
encryption, service blocking, restriction of unnecessary ports and kernel
modules, logging/monitoring/alerts, policy management, and automatic security
updates. C-DAC lists two relevant use cases: Secure BOSS with an Internet
Security Operation Centre (ISOC) for client monitoring, and Secure BOSS for
intranet/standalone systems. It also states that the OS is installed on an
LVM-encrypted hard disk. Source: [C-DAC Secure BOSS
Linux](https://www.cdac.in/index.aspx?id=product_details&productId=SecureBOSSLinux).

## How to describe SANCHAY's fit accurately

| Secure BOSS context | SANCHAY response | Precise boundary |
| --- | --- | --- |
| Critical end nodes and hardening | The core has no cleanup executor, daemon, root-command runner, or network dependency. A recommendation is a review artifact, not authority to modify the endpoint. | Does not make SANCHAY a security-control replacement. |
| ISOC/client monitoring | `--operator-brief` generates a checksum-bearing aggregate handoff with no paths, names, process identifiers, mount sources, or file content. Schema-6 snapshot histories likewise carry a local SHA-256 checksum and `--verify-snapshot` is read-only. When a capacity-risk horizon was requested, the brief can include only the aggregate risk probability, horizon, sample evidence, and model metrics. The checksums reveal a mismatch against stored content; they are not signatures. | It does not transmit the brief, call an ISOC API, sign an event, attest a device, or claim SIEM integration. |
| Intranet and standalone systems | Scanning, duplicate proof, planning, verification, and default narration all work locally. Optional cloud narration is separately opted in and never controls a decision. | An operator still chooses how, or whether, to move a local brief through an approved channel. |
| LVM-encrypted disks | Mount-aware accounting separates filesystem usage from a directory walk; device-mapper, Btrfs, and overlay boundaries are made explicit. The capacity audit also shows block availability, inode capacity, and any visible accounting gap. | It does not infer encryption status, thin-pool headroom, volume-group capacity, or permission to run LVM/Btrfs commands. |
| Policy management and alerts | With explicit `--risk-horizon DAYS`, a sufficiently long, stable local snapshot history can yield a capacity-hit probability instead of a false exact exhaustion date. | It is local decision support only: no automatic alert, policy update, ISOC API call, cleanup, or volume operation occurs. |
| Policy-managed updates and package state | APT archive and persistent-journal storage are treated as tool-owned operational areas, never raw file-deletion targets. | SANCHAY does not run `apt`, `journalctl`, or any maintenance command. |
| Logging and alerts | Visible deleted-but-open files are separated as an operational advisory; a process lifecycle may need review before blocks are released. | It never kills, restarts, truncates, or signals a process. |

## One-slide framing

> **SANCHAY is a local, evidence-first storage decision layer for a hardened
> Linux endpoint. It shows what the storage state proves, what it does not
> prove, and what must remain under operator and policy control.**

Keep the emphasis on capability fit: local operation, path-free handoff,
mount-aware accounting, managed-storage boundaries, and human review. Do not
claim Secure BOSS deployment, C-DAC integration, ISOC ingestion, certification,
or a scoring advantage unless an organizer supplies that evidence.
