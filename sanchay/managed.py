"""Recognise system-owned storage that must not be treated as loose files.

BOSS is Debian-derived, so APT's archive cache and persistent systemd journals
are useful operational signals. Container and Flatpak stores are not assumed to
exist on every BOSS endpoint, but when present they are also runtime-owned state.
Boot, configuration, package, log, and service-state paths need the same
conservative treatment even when no single owning tool can be inferred from a
path. None is a safe raw-path deletion target: the owning tool or approved
system policy controls locks, metadata, retention, and recoverability. SANCHAY
reports those areas as advisories and keeps them outside content evidence and
its file-level reclaim target.
"""
from dataclasses import dataclass

from . import scan, storage


@dataclass(frozen=True)
class ManagedPolicy:
    key: str
    label: str
    prefix: str
    review_action: str
    boundary: str


SPECIFIC_POLICIES = (
    ManagedPolicy(
        key="apt_archive_cache",
        label="APT archive cache",
        prefix="/var/cache/apt/archives/",
        review_action=(
            "review apt-get autoclean; use apt-get clean only under the "
            "approved package-cache policy"
        ),
        boundary=(
            "APT owns cache locks and package state; do not delete archive "
            "files individually"
        ),
    ),
    ManagedPolicy(
        key="persistent_system_journal",
        label="Persistent systemd journal",
        prefix="/var/log/journal/",
        review_action=(
            "review journalctl --disk-usage and the retention policy before "
            "choosing journalctl --vacuum-size=<approved limit>"
        ),
        boundary=(
            "journal retention can affect audit and incident evidence; do not "
            "delete journal files individually"
        ),
    ),
    ManagedPolicy(
        key="docker_engine_storage",
        label="Docker Engine storage",
        prefix="/var/lib/docker/",
        review_action=(
            "review docker system df -v; use Docker's explicit prune "
            "confirmation only after a deployment and data-retention review"
        ),
        boundary=(
            "Docker owns image, container, overlay, and volume state; do not "
            "delete files under this path individually"
        ),
    ),
    ManagedPolicy(
        key="container_runtime_storage",
        label="Container runtime storage",
        prefix="/var/lib/containerd/",
        review_action=(
            "review the owning container runtime or orchestrator state and "
            "retention policy before action"
        ),
        boundary=(
            "containerd owns runtime content and metadata; do not delete files "
            "under this path individually"
        ),
    ),
    ManagedPolicy(
        key="flatpak_system_installation",
        label="Flatpak system installation",
        prefix="/var/lib/flatpak/",
        review_action=(
            "review flatpak list; consider flatpak uninstall --unused only "
            "after checking required runtimes and installation scope"
        ),
        boundary=(
            "Flatpak owns application, runtime, and repository state; do not "
            "delete files under this path individually"
        ),
    ),
)

# These paths can contain package-managed files, boot components, configuration,
# service queues, or system logs. A path name alone cannot establish that a file
# is disposable, even when its bytes happen to duplicate another file. Keep the
# policy separate from the narrower owning-tool policies above so an APT cache,
# persistent journal, or container store retains its more precise guidance.
SYSTEM_RESERVED_PATHS = (
    "/boot/", "/etc/", "/usr/", "/bin/", "/sbin/", "/lib/", "/lib64/",
    "/opt/", "/run/", "/lost+found/", "/var/cache/", "/var/log/",
    "/var/backups/", "/var/lib/apt/", "/var/lib/dpkg/", "/var/lib/pacman/",
    "/var/lib/rpm/", "/var/lib/snapd/", "/var/lib/systemd/", "/var/spool/",
)
SYSTEM_RESERVED_POLICY = ManagedPolicy(
    key="system_reserved_paths",
    label="System-reserved paths",
    prefix="",
    review_action=(
        "review package ownership or the owning service policy before using an "
        "approved system management tool"
    ),
    boundary=(
        "boot, configuration, package, log, and service state can be "
        "security-critical; do not delete individual files by path"
    ),
)
POLICIES = SPECIFIC_POLICIES + (SYSTEM_RESERVED_POLICY,)


def classify(path):
    """Return a policy for an absolute Linux system path, if one applies."""
    normalized = "/" + str(path).replace("\\", "/").lstrip("/")
    for policy in SPECIFIC_POLICIES:
        if normalized.startswith(policy.prefix):
            return policy
    if any(normalized.startswith(prefix) for prefix in SYSTEM_RESERVED_PATHS):
        return SYSTEM_RESERVED_POLICY
    return None


def content_candidates(files):
    """Return files that may safely enter content-deduplication evidence."""
    return [info for info in files if is_content_candidate(info.path)]


def is_content_candidate(path):
    """Keep managed and known credential/control paths out of content reads."""
    return classify(path) is None and not scan.is_protected_path(path)


def advisories(files):
    """Summarise allocated bytes by managed policy without selecting files."""
    totals = {
        policy.key: {"policy": policy, "entries": 0, "allocated_bytes": 0}
        for policy in POLICIES
    }
    for info in storage.physical_records(files):
        policy = classify(info.path)
        if policy is None:
            continue
        total = totals[policy.key]
        total["entries"] += 1
        total["allocated_bytes"] += storage.allocated_bytes(info)

    return [
        {
            "key": policy.key,
            "label": policy.label,
            "entries": total["entries"],
            "allocated_bytes": total["allocated_bytes"],
            "review_action": policy.review_action,
            "boundary": policy.boundary,
        }
        for policy in POLICIES
        for total in (totals[policy.key],)
        if total["entries"]
    ]
