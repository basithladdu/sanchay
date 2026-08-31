# About sanchay-report.html

The checked-in HTML report is a static report generated from the deterministic
SANCHAY demo fixture. It is an explanatory sample, not a scan of the viewer's
machine and not a live dashboard.

To create a real local report:

    sanchay /path/to/scan --report report.html

To recreate the reviewable sample fixture:

    sanchay-demo /tmp/sanchay-demo
    sanchay /tmp/sanchay-demo --report sanchay-report.html

The report intentionally shows paths relative to the selected root so a shared
report does not disclose the operator's absolute local path.

When Linux exposes a deleted regular file that a process still has open, the
report includes a separate **Process-held deleted files** panel. It identifies
the visible holders and allocated bytes as operational evidence only; those
records never become file cleanup candidates.

The report also separates **System-managed storage** from file-level cleanup.
This includes specific APT, journal, and runtime stores as well as generic
system-reserved boot, configuration, package/cache, log, backup, and
service/spool paths. Those files are excluded before duplicate-content reads;
matching bytes are not treated as permission to remove OS state.

When the selected mount is Btrfs, overlay, or device-mapper-backed, the report
also includes a **filesystem capacity boundary** panel. It records why a
directory-level total is not proof of host-wide, snapshot-aware, or volume-pool
headroom; it never offers a filesystem or volume-management action.
