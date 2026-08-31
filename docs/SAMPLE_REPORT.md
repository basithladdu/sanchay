# About sanchay-report.html

The checked-in HTML report is a static report generated from the deterministic
SANCHAY demo fixture. It is an explanatory sample, not a scan of the viewer's
machine and not a live dashboard.

To create a real local report:

    sanchay /path/to/scan --report report.html

To recreate the safe sample fixture:

    sanchay-demo /tmp/sanchay-demo
    sanchay /tmp/sanchay-demo --report sanchay-report.html

The report intentionally shows paths relative to the selected root so a shared
report does not disclose the operator's absolute local path.
