"""Build the dashboard.

The CLI prints a table, which is fine over ssh. This is the thing you actually
look at: what is on the disk, what has recovery evidence, what is protected, and how
long you have before it fills.

Self-contained HTML -- plotly is inlined, so the file opens anywhere with no
network.
"""
import html
import time
from pathlib import Path

from . import dedup, forecast, managed, plan, storage

CSS = """
:root{--bg:#090d16;--panel:#111827;--panel-sub:#1a2333;--ink:#f3f4f6;--mute:#9ca3af;--line:#1f293d;
--green:#10b981;--lime:#84cc16;--amber:#f59e0b;--red:#ef4444;--accent:#3b82f6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;padding:36px 20px}
.wrap{max-width:1200px;margin:0 auto}
header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:18px;margin-bottom:28px}
h1{font-size:24px;margin:0 0 4px;letter-spacing:-.02em;display:flex;align-items:center;gap:10px}
.badge-regret{background:linear-gradient(135deg,var(--green),var(--accent));color:#fff;font-size:11px;font-weight:600;padding:3px 9px;border-radius:99px;letter-spacing:.05em;text-transform:uppercase}
.sub{color:var(--mute);font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:28px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 20px}
.card .k{color:var(--mute);font-size:12px;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
.card .v{font-size:26px;font-weight:700;margin:6px 0 2px;letter-spacing:-.02em}
.card .n{color:var(--mute);font-size:12px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:22px;margin-bottom:24px;overflow-x:auto}
.panel h2{font-size:16px;font-weight:600;margin:0 0 4px;letter-spacing:-.01em}
.panel .h{color:var(--mute);font-size:13px;margin:0 0 16px}
.formula-box{background:var(--panel-sub);border:1px solid #2d3b55;border-radius:8px;padding:12px 16px;font-size:13px;margin-bottom:18px;display:flex;align-items:center;gap:12px}
.formula-tag{font-weight:700;color:var(--accent);font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.controls{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;align-items:center}
.search-box{background:var(--panel-sub);border:1px solid var(--line);color:#fff;padding:8px 14px;border-radius:6px;font-size:13px;flex:1;min-width:240px}
.filter-btn{background:var(--panel-sub);border:1px solid var(--line);color:var(--mute);padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.filter-btn:hover, .filter-btn.active{background:var(--accent);color:#fff;border-color:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:760px}
th{text-align:left;color:var(--mute);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.06em;padding:10px 12px;border-bottom:1px solid var(--line)}
td{padding:10px 12px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:0}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.p{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;color:var(--mute);word-break:break-all}
.tag{display:inline-block;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600;text-transform:uppercase}
.evidence{color:var(--mute);font-size:12px;max-width:280px}
.disposable{background:rgba(16,185,129,.18);color:#34d399}
.duplicate{background:rgba(132,204,22,.18);color:#a3e635}
.tracked{background:rgba(245,158,11,.18);color:#fcd34d}
.guard{background:rgba(239,68,68,.1);border-left:3px solid var(--red);border-radius:0 8px 8px 0;padding:14px 18px;margin-top:16px}
.guard b{color:var(--red)}
@media (max-width:600px){
body{padding:20px 12px}
header{align-items:flex-start;margin-bottom:20px}
.cards{grid-template-columns:1fr;gap:12px;margin-bottom:20px}
.card{padding:16px}
.panel{padding:16px;margin-bottom:16px}
.formula-box{display:block;padding:12px}
.formula-tag{display:block;margin-bottom:6px}
.search-box{flex-basis:100%;min-width:0}
.filter-btn{flex:1 1 44%}
table{min-width:0}
thead{display:none}
table,tbody,tr,td{display:block;width:100%}
tr{padding:9px 0;border-bottom:1px solid var(--line)}
td,td.num{padding:4px 0;border:0;text-align:left;white-space:normal}
td::before{content:attr(data-label);display:block;color:var(--mute);font-size:10px;font-weight:600;letter-spacing:.06em;text-transform:uppercase}
td.p{word-break:break-word}
.evidence{max-width:none}
}

/* Evidence-console override: a local forensic report, not a generic dashboard. */
:root{--bg:#f1f0ea;--panel:#fbfaf5;--panel-sub:#e7e8df;--ink:#141713;--mute:#5d625b;--line:#bec3ba;--green:#27664b;--lime:#5a8294;--amber:#9a5c1b;--red:#a13e32;--accent:#275f78}
body{background:var(--bg);color:var(--ink);font:13px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;padding:24px 20px}
.wrap{max-width:1180px}
header{align-items:flex-start;border-bottom:1px solid var(--line);border-top:4px solid var(--ink);margin-bottom:0;padding:14px 0 16px}
h1{font-size:19px;letter-spacing:.06em}
.badge-regret{background:transparent;border:1px solid var(--green);border-radius:0;color:var(--green);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9px;padding:3px 5px}
.sub{color:var(--mute);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px;margin-top:4px}
.cards{border-bottom:1px solid var(--line);gap:0;grid-template-columns:repeat(4,1fr);margin-bottom:28px}
.card{background:transparent;border:0;border-bottom:0;border-radius:0;border-right:1px solid var(--line);padding:20px}
.card:first-child{padding-left:0}.card:last-child{border-right:0;padding-right:0}
.card .k{color:var(--mute);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9px}.card .v{color:var(--ink)!important;font-size:24px;margin:5px 0 2px}.card .n{color:var(--mute);font-size:11px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:0;margin-bottom:24px;overflow-x:auto;padding:22px}
.panel h2{color:var(--ink);font-size:18px;letter-spacing:-.03em}.panel .h{color:var(--mute);font-size:12px;margin-bottom:16px}
.formula-box{background:var(--panel-sub);border:1px solid var(--line);border-left:4px solid var(--ink);border-radius:0;font-size:12px;padding:12px 14px}.formula-tag{color:var(--ink);font-size:10px}
.controls{border-bottom:1px solid var(--line);gap:8px;padding-bottom:12px}.search-box{background:var(--panel);border:1px solid var(--ink);border-radius:0;color:var(--ink);font-size:12px;padding:8px 10px}.filter-btn{background:transparent;border:0;border-bottom:2px solid transparent;border-radius:0;color:var(--mute);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px;padding:7px 0}.filter-btn:hover,.filter-btn.active{background:transparent;border-bottom-color:var(--ink);color:var(--ink)}
table{font-size:12px}th{color:var(--mute);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9px;padding:10px 8px}td{border-bottom-color:var(--line);color:var(--ink);padding:11px 8px}td.p{color:var(--mute);font-size:11px}.tag{background:transparent;border:1px solid currentColor;border-radius:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9px;padding:3px 5px}.disposable{color:var(--green)}.duplicate{color:var(--accent)}.tracked{color:var(--amber)}.evidence{color:var(--mute);font-size:11px}
.guard{background:#f1eadc;border:1px solid #d2b984;border-left:3px solid var(--amber);border-radius:0;color:#5b4829;padding:12px 14px}.guard b{color:#77501b}.guard code{overflow-wrap:anywhere}
@media (max-width:600px){body{padding:16px 12px}.cards{grid-template-columns:1fr}.card,.card:first-child,.card:last-child{border-bottom:1px solid var(--line);border-right:0;padding:15px 0}.panel{padding:16px}.formula-box{padding:12px}.search-box{min-width:0}.filter-btn{flex:1 1 42%}td::before{color:var(--mute);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9px}.guard{font-size:12px}}
"""


def human(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"


def _card(k, v, note="", color=""):
    color_attr = f' style="color: {color};"' if color else ""
    return (f'<div class="card"><div class="k">{k}</div><div class="v"{color_attr}>{v}</div>'
            f'<div class="n">{note}</div></div>')


def _display_path(path, root):
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve())).replace("\\", "/")
    except (OSError, ValueError):
        return Path(path).name


def _evidence_label(row, root):
    evidence = row["recovery_evidence"]
    strength = evidence["strength"].replace("_", " ")
    if row["kind"] == "duplicate":
        survivor = row.get("survivor_path")
        if isinstance(survivor, str):
            return (f"{strength}: byte-for-byte match with named evidence peer "
                    f"at {_display_path(survivor, root)}; human selects retention")
        return f"{strength}: byte-for-byte match with a named evidence peer; human selects retention"
    return f"{strength}: {evidence['detail']}"


def _holder_summary(record):
    """Render a bounded, human-readable list of processes holding one inode."""
    shown = record.holders[:3]
    summary = ", ".join(
        f"PID {holder.pid} ({holder.process}), fd {holder.fd}"
        for holder in shown)
    if len(record.holders) > len(shown):
        summary += f"; +{len(record.holders) - len(shown)} more holder(s)"
    return summary


def build(files, root, free_bytes, out="sanchay-report.html", limit=50,
          target_reclaim_bytes=None, cross_filesystems=False, process_held=None,
          filesystem_context=None, scan_coverage=None, capacity_accounting=None):
    from . import viz

    groups = dedup.duplicates(managed.content_candidates(files), root=root)
    cleanup_plan = plan.build(files, groups, root, limit=limit,
                              target_reclaim_bytes=target_reclaim_bytes,
                              cross_filesystems=cross_filesystems,
                              filesystem_context=filesystem_context,
                              scan_coverage=scan_coverage)
    rows = cleanup_plan["recommendations"]
    protected_count = cleanup_plan["safety"]["protected_unique_files"]
    credential_control_entries = cleanup_plan["safety"]["excluded_credential_control_entries"]
    managed_storage = cleanup_plan["safety"]["managed_operational_storage"]
    coverage = cleanup_plan["safety"]["scan_coverage"]
    dup_paths = plan.duplicate_evidence_paths(cleanup_plan)

    physical = storage.physical_records(files)
    total = sum(storage.allocated_bytes(info) for info in physical)
    aliases = storage.hardlink_alias_count(files)
    reviewable = sum(r["size"] for r in rows)
    filesystem_count = len({getattr(info, "device", None) for info in physical})
    allocation_title = ("Readable allocated inventory" if not coverage["complete"]
                        else "Allocated inventory" if cross_filesystems
                        else "Allocated on disk")
    allocation_note = (
        f"{len(files):,} entries across {filesystem_count:,} filesystem"
        f"{'s' if filesystem_count != 1 else ''}; no shared free-space claim"
        if cross_filesystems else
        f"{len(files):,} entries; {aliases:,} hardlink aliases not double-counted"
    )
    header_scope = (
        "Readable inventory only; inaccessible paths are not included"
        if not coverage["complete"] else
        "Cross-filesystem inventory; no aggregate free-space or reclaim target"
        if cross_filesystems else "Selected local root"
    )
    days = (None if cross_filesystems or not coverage["complete"]
            else forecast.days_until_full(files, free_bytes))
    runway_note = ("not calculated; scan coverage is incomplete" if not coverage["complete"]
                   else "not calculated across multiple filesystems; scan one filesystem "
                   "for a capacity forecast" if cross_filesystems
                   else f"{human(forecast.rate(files))}/day from readable-inventory mtime; "
                   "capture same-mount snapshots for observed growth")
    selection = cleanup_plan.get("selection")
    review_note = f"top {len(rows)} recommendations; human review required"
    if selection:
        state = "target met" if selection["target_met"] else (
            f"short by {human(selection['shortfall_bytes'])}")
        review_note = (f"{human(selection['selected_reclaim_bytes'])} selected for "
                       f"{human(selection['target_reclaim_bytes'])} target; {state}")

    fig = viz.figure(files, dup_paths, root=root)
    chart = fig.to_html(full_html=False, include_plotlyjs=True,
                        default_height="500px", config={"displayModeBar": False})

    table_rows = []
    for r in rows:
        table_rows.append(
            f'<tr data-kind="{r["kind"]}"><td class="num font-bold" data-label="Allocated reclaim">{human(r["size"])}</td>'
            f'<td data-label="Category"><span class="tag {r["kind"]}">{r["kind"]}</span></td>'
            f'<td class="num" data-label="Unchanged">{r["staleness"] * 365:.0f} d</td>'
            f'<td class="p" data-label="Relative path">{html.escape(_display_path(r["path"], root))}</td>'
            f'<td class="evidence" data-label="Recovery evidence">{html.escape(_evidence_label(r, root))}</td></tr>'
        )

    managed_panel = ""
    if managed_storage:
        managed_rows = []
        for item in managed_storage:
            managed_rows.append(
                f'<tr><td data-label="System area">{html.escape(item["label"])}</td>'
                f'<td class="num" data-label="Allocated storage">{human(item["allocated_bytes"])}</td>'
                f'<td class="num" data-label="Entries">{item["entries"]:,}</td>'
                f'<td class="evidence" data-label="Human review">{html.escape(item["review_action"])}. '
                f'{html.escape(item["boundary"])}</td></tr>'
            )
        managed_panel = f"""
  <div class="panel">
    <h2>System-managed storage</h2>
    <p class="h">These paths are measured but excluded from file-level reclamation and target selection. Their owning Linux tools and an approved retention policy decide any action.</p>
    <table>
      <thead><tr><th>System area</th><th class="num">Allocated storage</th><th class="num">Entries</th><th>Human review</th></tr></thead>
      <tbody>{"".join(managed_rows)}</tbody>
    </table>
  </div>
"""

    coverage_panel = ""
    if not coverage["complete"]:
        coverage_panel = f"""
  <div class="panel">
    <h2>Scan coverage boundary</h2>
    <p class="h">{coverage['unreadable_directories']:,} directory(ies) and {coverage['unreadable_files']:,} file(s) could not be inspected. This report inventories only readable in-scope files; it does not calculate a growth forecast or create a comparable snapshot from this partial view.</p>
  </div>
"""

    credential_boundary = ""
    if credential_control_entries:
        credential_boundary = (
            f"<br>{credential_control_entries:,} known credential/control path entry "
            "was excluded before content evidence and planning."
            if credential_control_entries == 1 else
            f"<br>{credential_control_entries:,} known credential/control path entries "
            "were excluded before content evidence and planning."
        )

    process_panel = ""
    process_held = tuple(process_held or ())
    if process_held:
        process_rows = []
        for record in process_held:
            path = record.holders[0].path if record.holders else "(unavailable)"
            process_rows.append(
                f'<tr><td class="num" data-label="Allocated storage">{human(record.allocated_size)}</td>'
                f'<td data-label="Process holders">{html.escape(_holder_summary(record))}</td>'
                f'<td class="p" data-label="Observed deleted path">{html.escape(path)}</td>'
                f'<td class="evidence" data-label="Operational boundary">Review the owning service lifecycle. '
                f'SANCHAY never signals, restarts, truncates, or deletes process-held storage.</td></tr>'
            )
        process_panel = f"""
  <div class="panel">
    <h2>Process-held deleted files</h2>
    <p class="h">No directory entry remains for these files, but their allocated bytes persist until every listed process closes its descriptor. They are operational evidence, never cleanup candidates.</p>
    <table>
      <thead><tr><th class="num">Allocated storage</th><th>Process holders</th><th>Observed deleted path</th><th>Operational boundary</th></tr></thead>
      <tbody>{"".join(process_rows)}</tbody>
    </table>
  </div>
"""

    accounting_panel = ""
    if capacity_accounting:
        if capacity_accounting.get("assessed"):
            gap = capacity_accounting["accounting_gap_bytes"]
            sign = "+" if gap >= 0 else "-"
            inode_capacity = capacity_accounting.get("inode_capacity")
            inode_note = ""
            if isinstance(inode_capacity, dict) and inode_capacity.get("assessed"):
                available = inode_capacity.get("available_inodes")
                available_note = (
                    f"; {available:,} available to an unprivileged process"
                    if isinstance(available, int) else "")
                inode_note = (
                    f"<p class=\"h\">Inode capacity advisory: "
                    f"{inode_capacity['total_inodes']:,} file entries; "
                    f"{inode_capacity['free_inodes']:,} free; "
                    f"{inode_capacity['used_percent']:.1f}% used{available_note}. "
                    f"This is a mount-level observation, not a cleanup instruction.</p>")
            elif isinstance(inode_capacity, dict):
                inode_note = (
                    "<p class=\"h\">Inode capacity advisory not assessed: "
                    + html.escape(inode_capacity.get("reason", "unavailable"))
                    + ".</p>")
            block_availability = capacity_accounting.get("block_availability")
            block_note = ""
            if isinstance(block_availability, dict) and block_availability.get("assessed"):
                unavailable = block_availability[
                    "free_unavailable_to_unprivileged_bytes"]
                unavailable_note = (
                    f"; {human(unavailable)} free but unavailable to an unprivileged process"
                    if unavailable else "")
                block_note = (
                    f"<p class=\"h\">Block availability advisory: "
                    f"{human(block_availability['free_bytes'])} free; "
                    f"{human(block_availability['available_bytes'])} available to an "
                    f"unprivileged process{unavailable_note}. This is a mount-level "
                    f"observation, not a filesystem-policy change.</p>")
            elif isinstance(block_availability, dict):
                block_note = (
                    "<p class=\"h\">Block availability advisory not assessed: "
                    + html.escape(block_availability.get("reason", "unavailable"))
                    + ".</p>")
            accounting_panel = f"""
  <div class="panel">
    <h2>Filesystem accounting boundary</h2>
    <p class="h">This compares the mounted filesystem's used blocks with the readable file inventory plus visible deleted-open files. The result is an accounting gap, not a reclaim recommendation.</p>
    <table>
      <thead><tr><th>Filesystem used</th><th>Readable inventory</th><th>Visible deleted-open</th><th>Accounting gap</th></tr></thead>
      <tbody><tr><td class="num" data-label="Filesystem used">{human(capacity_accounting['filesystem_used_bytes'])}</td><td class="num" data-label="Readable inventory">{human(capacity_accounting['readable_file_allocated_bytes'])}</td><td class="num" data-label="Visible deleted-open">{human(capacity_accounting['deleted_open_allocated_bytes'])}</td><td class="num" data-label="Accounting gap">{sign}{human(abs(gap))}</td></tr></tbody>
    </table>
    <p class="h">{html.escape(capacity_accounting['boundary'])}</p>
    {inode_note}
    {block_note}
  </div>
"""
        else:
            accounting_panel = f"""
  <div class="panel">
    <h2>Filesystem accounting boundary</h2>
    <p class="h">Capacity audit not assessed: {html.escape(capacity_accounting.get('reason', 'unavailable'))}. {html.escape(capacity_accounting.get('boundary', ''))}</p>
  </div>
"""

    mount_panel = ""
    mount_context = cleanup_plan["safety"].get("filesystem_context")
    topology_note = ""
    if isinstance(mount_context, dict):
        nested_count = mount_context.get("nested_mount_point_count")
        if (isinstance(nested_count, int) and not isinstance(nested_count, bool)
                and nested_count > 0 and mount_context.get("nested_mount_boundary")
                and mount_context.get("nested_mount_review_action")):
            topology_note = f"""
    <p class="h"><b>Nested mount topology:</b> {html.escape(mount_context['nested_mount_boundary'])} {html.escape(mount_context['nested_mount_review_action'])}</p>
"""
    if mount_context and (mount_context.get("advisory") or topology_note):
        mount_details = ""
        if mount_context.get("advisory"):
            mount_details = f"""
    <p class="h">{html.escape(mount_context.get('capacity_scope', 'Capacity claims are mount-scoped.'))}</p>
    <table>
      <thead><tr><th>Filesystem</th><th>Source class</th><th>Capacity boundary</th><th>Human review</th></tr></thead>
      <tbody><tr><td>{html.escape(mount_context["filesystem"])}</td><td>{html.escape(mount_context["source_class"])}</td><td class="evidence">{html.escape(mount_context["advisory"])}</td><td class="evidence">{html.escape(mount_context["review_action"])}</td></tr></tbody>
    </table>
"""
        mount_panel = f"""
  <div class="panel">
    <h2>{html.escape(mount_context.get("label", "Mount topology boundary"))}</h2>
    {mount_details}
    {topology_note}
  </div>
"""

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SANCHAY — Regret-Aware Storage Dashboard</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>SANCHAY <span class="badge-regret">Regret-Aware Storage</span></h1>
      <div class="sub">{header_scope} &middot; Generated {time.strftime('%d %b %Y, %H:%M')}</div>
    </div>
  </header>

  <div class="cards">
    {_card(allocation_title, human(total), allocation_note)}
    {_card("Duplicate candidates", human(dedup.reclaimable(groups)), f"{len(groups):,} content groups; allocated reclaim only", "#84cc16")}
    {_card("Reviewable candidates", human(reviewable), review_note, "#10b981")}
    {_card("First-run runway estimate", forecast.runway_label(days), runway_note, "#3b82f6")}
  </div>

  <div class="panel">
    <h2>Storage Recoverability Treemap</h2>
    <p class="h">One block represents one physical inode sized by allocated bytes. Blocks are coloured by recoverability evidence: green has cache or byte-confirmed duplicate evidence; red has no known recovery proof.</p>
    {chart}
  </div>

  <div class="panel">
    <h2>Reviewable Storage Candidates</h2>
    <p class="h">Ranked by the regret objective. This report makes recommendations; it does not execute cleanup.</p>
    
    <div class="formula-box">
      <span class="formula-tag">Objective:</span>
      <span>Priority = Reclaimable Allocated Bytes &times; Unchanged Age &times; (1 &minus; Regret) &nbsp;|&nbsp; Regret Weights: 0.02 (Disposable), 0.10 (Duplicate), 0.20 (Tracked Git)</span>
    </div>

    <div class="controls">
      <input type="text" id="searchInput" class="search-box" placeholder="Filter candidates by path or name..." onkeyup="filterCandidates()">
      <button class="filter-btn active" onclick="setKindFilter('all', this)">All ({len(rows)})</button>
      <button class="filter-btn" onclick="setKindFilter('disposable', this)">Disposable</button>
      <button class="filter-btn" onclick="setKindFilter('duplicate', this)">Duplicates</button>
      <button class="filter-btn" onclick="setKindFilter('tracked', this)">Tracked Git</button>
    </div>

    <table id="candidateTable">
      <thead>
        <tr>
          <th style="width: 110px;">Allocated reclaim</th>
          <th style="width: 120px;">Category</th>
          <th class="num" style="width: 90px;">Unchanged</th>
          <th>Relative Path</th>
          <th>Recovery evidence</th>
        </tr>
      </thead>
      <tbody>
        {"".join(table_rows)}
      </tbody>
    </table>

    <div class="guard">
      <b>{protected_count:,} unique files and {cleanup_plan["safety"]["excluded_hardlink_entries"]:,} hardlinked entries are excluded from this plan.</b><br>
      Integrity checksum (not a signature): <code>{cleanup_plan["fingerprint_sha256"]}</code><br>
      {html.escape(cleanup_plan["safety"]["content_read_boundary"])}. A single hardlink removal releases no physical bytes. The active policy excludes known credential/control paths, unique, untracked, uncached, and hardlinked entries before ranking.{credential_boundary} SANCHAY never deletes or moves files.
    </div>
  </div>
  {managed_panel}
  {coverage_panel}
  {process_panel}
  {accounting_panel}
  {mount_panel}
</div>

<script>
let currentKind = 'all';

function setKindFilter(kind, btn) {{
  currentKind = kind;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  filterCandidates();
}}

function filterCandidates() {{
  const query = document.getElementById('searchInput').value.toLowerCase();
  const rows = document.querySelectorAll('#candidateTable tbody tr');
  rows.forEach(r => {{
    const kind = r.getAttribute('data-kind');
    const text = r.textContent.toLowerCase();
    const matchesKind = (currentKind === 'all' || kind === currentKind);
    const matchesQuery = text.indexOf(query) > -1;
    r.style.display = (matchesKind && matchesQuery) ? '' : 'none';
  }});
}}
</script>
</body>
</html>
"""

    Path(out).write_text(page, encoding="utf-8")
    return out
