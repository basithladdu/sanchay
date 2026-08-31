"""Build the dashboard.

The CLI prints a table, which is fine over ssh. This is the thing you actually
look at: what is on the disk, what is safe to take, what is protected, and how
long you have before it fills.

Self-contained HTML -- plotly is inlined, so the file opens anywhere with no
network.
"""
import html
import time
from pathlib import Path

from . import dedup, forecast, plan

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
table{width:100%;border-collapse:collapse;font-size:13px;min-width:640px}
th{text-align:left;color:var(--mute);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.06em;padding:10px 12px;border-bottom:1px solid var(--line)}
td{padding:10px 12px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:0}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.p{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;color:var(--mute);word-break:break-all}
.tag{display:inline-block;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600;text-transform:uppercase}
.disposable{background:rgba(16,185,129,.18);color:#34d399}
.duplicate{background:rgba(132,204,22,.18);color:#a3e635}
.tracked{background:rgba(245,158,11,.18);color:#fcd34d}
.guard{background:rgba(239,68,68,.1);border-left:3px solid var(--red);border-radius:0 8px 8px 0;padding:14px 18px;margin-top:16px}
.guard b{color:var(--red)}
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


def build(files, root, free_bytes, out="sanchay-report.html", limit=50):
    from . import viz

    groups = dedup.duplicates(files)
    dup_paths = set(dedup.duplicate_map(groups))
    cleanup_plan = plan.build(files, groups, root, limit=limit)
    rows = cleanup_plan["recommendations"]
    protected_count = cleanup_plan["safety"]["protected_unique_files"]

    total = sum(f.size for f in files)
    reviewable = sum(r["size"] for r in rows)
    days = forecast.days_until_full(files, free_bytes)

    fig = viz.figure(files, dup_paths, root=root)
    chart = fig.to_html(full_html=False, include_plotlyjs=True,
                        default_height="500px", config={"displayModeBar": False})

    table_rows = []
    for r in rows:
        table_rows.append(
            f'<tr data-kind="{r["kind"]}"><td class="num font-bold">{human(r["size"])}</td>'
            f'<td><span class="tag {r["kind"]}">{r["kind"]}</span></td>'
            f'<td class="num">{r["staleness"] * 365:.0f} d</td>'
            f'<td class="p">{html.escape(_display_path(r["path"], root))}</td></tr>'
        )

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
      <h1>💾 SANCHAY <span class="badge-regret">Regret-Aware Storage</span></h1>
      <div class="sub">Selected local root &middot; Generated {time.strftime('%d %b %Y, %H:%M')}</div>
    </div>
  </header>

  <div class="cards">
    {_card("Scanned on disk", human(total), f"{len(files):,} total files")}
    {_card("Duplicate candidates", human(dedup.reclaimable(groups)), f"{len(groups):,} groups before survivor review", "#84cc16")}
    {_card("Reviewable candidates", human(reviewable), f"top {len(rows)} recommendations; human review required", "#10b981")}
    {_card("Disk runway", f"{days:.0f} days" if days else "—", f"{human(forecast.rate(files))}/day growth rate", "#3b82f6")}
  </div>

  <div class="panel">
    <h2>Storage Recoverability Treemap</h2>
    <p class="h">Treemap blocks are coloured by recoverability evidence: green has cache or duplicate evidence; red has no known recovery proof.</p>
    {chart}
  </div>

  <div class="panel">
    <h2>Reviewable Storage Candidates</h2>
    <p class="h">Ranked by the regret objective. This report makes recommendations; it does not execute cleanup.</p>
    
    <div class="formula-box">
      <span class="formula-tag">Objective:</span>
      <span>Priority = Size &times; Unchanged Age &times; (1 &minus; Regret) &nbsp;|&nbsp; Regret Weights: 0.02 (Disposable), 0.10 (Duplicate), 0.20 (Tracked Git)</span>
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
          <th style="width: 110px;">Size</th>
          <th style="width: 120px;">Category</th>
          <th class="num" style="width: 90px;">Unchanged</th>
          <th>Relative Path</th>
        </tr>
      </thead>
      <tbody>
        {"".join(table_rows)}
      </tbody>
    </table>

    <div class="guard">
      <b>{protected_count:,} unique files excluded from this plan.</b><br>
      Plan fingerprint: <code>{cleanup_plan["fingerprint_sha256"]}</code><br>
      The active policy excludes unique, untracked, uncached files before ranking. SANCHAY never deletes or moves files.
    </div>
  </div>
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
