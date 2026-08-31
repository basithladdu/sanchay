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
            return (f"{strength}: byte-for-byte match with the named retained "
                    f"survivor at {_display_path(survivor, root)}")
        return f"{strength}: byte-for-byte match with a named retained survivor"
    return f"{strength}: {evidence['detail']}"


def build(files, root, free_bytes, out="sanchay-report.html", limit=50,
          target_reclaim_bytes=None, cross_filesystems=False):
    from . import viz

    groups = dedup.duplicates(managed.content_candidates(files), root=root)
    cleanup_plan = plan.build(files, groups, root, limit=limit,
                              target_reclaim_bytes=target_reclaim_bytes)
    rows = cleanup_plan["recommendations"]
    protected_count = cleanup_plan["safety"]["protected_unique_files"]
    managed_storage = cleanup_plan["safety"]["managed_operational_storage"]
    dup_paths = plan.duplicate_evidence_paths(cleanup_plan)

    total = storage.physical_bytes(files)
    aliases = storage.hardlink_alias_count(files)
    reviewable = sum(r["size"] for r in rows)
    days = (None if cross_filesystems
            else forecast.days_until_full(files, free_bytes))
    runway_note = ("not calculated across multiple filesystems; scan one filesystem "
                   "for a capacity forecast" if cross_filesystems
                   else f"{human(forecast.rate(files))}/day from mtime; capture snapshots for observed growth")
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
      <div class="sub">Selected local root &middot; Generated {time.strftime('%d %b %Y, %H:%M')}</div>
    </div>
  </header>

  <div class="cards">
    {_card("Allocated on disk", human(total), f"{len(files):,} entries; {aliases:,} hardlink aliases not double-counted")}
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
      {html.escape(cleanup_plan["safety"]["content_read_boundary"])}. A single hardlink removal releases no physical bytes. The active policy excludes unique, untracked, uncached, and hardlinked entries before ranking. SANCHAY never deletes or moves files.
    </div>
  </div>
  {managed_panel}
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
