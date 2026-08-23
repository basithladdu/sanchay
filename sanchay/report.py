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

from . import dedup, forecast, regret

CSS = """
:root{--bg:#fbfbfd;--panel:#fff;--ink:#0f172a;--mute:#64748b;--line:#e2e8f0;
--green:#16a34a;--lime:#65a30d;--amber:#ca8a04;--red:#dc2626;--accent:#2563eb}
@media(prefers-color-scheme:dark){:root{--bg:#0b1120;--panel:#111827;--ink:#e6edf7;
--mute:#94a3b8;--line:#1f2937;--accent:#60a5fa}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:40px 24px 72px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.02em}
.sub{color:var(--mute);margin:0 0 28px;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin-bottom:28px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 20px}
.card .k{color:var(--mute);font-size:12px;text-transform:uppercase;letter-spacing:.07em}
.card .v{font-size:26px;font-weight:650;margin-top:6px;letter-spacing:-.02em}
.card .n{color:var(--mute);font-size:12.5px;margin-top:3px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;
padding:22px;margin-bottom:22px;overflow-x:auto}
.panel h2{font-size:15px;margin:0 0 4px;letter-spacing:-.01em}
.panel .h{color:var(--mute);font-size:13px;margin:0 0 18px}
table{width:100%;border-collapse:collapse;font-size:13.5px;min-width:640px}
th{text-align:left;color:var(--mute);font-weight:500;font-size:11.5px;
text-transform:uppercase;letter-spacing:.06em;padding:0 12px 10px;border-bottom:1px solid var(--line)}
td{padding:11px 12px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:0}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.p{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;
color:var(--mute);word-break:break-all}
.tag{display:inline-block;padding:2px 9px;border-radius:99px;font-size:11.5px;font-weight:550}
.disposable{background:color-mix(in srgb,var(--green) 15%,transparent);color:var(--green)}
.duplicate{background:color-mix(in srgb,var(--lime) 15%,transparent);color:var(--lime)}
.tracked{background:color-mix(in srgb,var(--amber) 15%,transparent);color:var(--amber)}
.guard{border-left:3px solid var(--red);padding-left:16px;margin-top:4px}
.guard b{color:var(--red)}
"""


def human(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"


def _card(k, v, note=""):
    return (f'<div class="card"><div class="k">{k}</div><div class="v">{v}</div>'
            f'<div class="n">{note}</div></div>')


def build(files, root, free_bytes, out="sanchay-report.html", limit=30):
    from . import viz  # pulls plotly; only needed for the report

    groups = dedup.duplicates(files)
    dup_paths = {f.path for g in groups for f in g[1:]}
    rows = regret.rank(files, dup_paths, limit=limit)
    protected = [f for f in files
                 if regret.classify(f, f.path in dup_paths) == "unique"]

    total = sum(f.size for f in files)
    safe = sum(r["size"] for r in rows)
    days = forecast.days_until_full(files, free_bytes)

    fig = viz.figure(files, dup_paths)
    chart = fig.to_html(full_html=False, include_plotlyjs=True,
                        default_height="520px", config={"displayModeBar": False})

    body = "".join(
        f'<tr><td class="num">{human(r["size"])}</td>'
        f'<td><span class="tag {r["kind"]}">{r["kind"]}</span></td>'
        f'<td class="num">{r["staleness"] * 365:.0f} d</td>'
        f'<td class="p">{html.escape(r["path"])}</td></tr>' for r in rows)

    page = f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SANCHAY — {html.escape(str(root))}</title><style>{CSS}</style>
<div class="wrap">
<h1>Storage report</h1>
<p class="sub">{html.escape(str(root))} &middot; {time.strftime('%d %b %Y, %H:%M')}</p>

<div class="cards">
{_card("On disk", human(total), f"{len(files):,} files")}
{_card("Duplicated", human(dedup.reclaimable(groups)), f"{len(groups):,} groups")}
{_card("Safe to reclaim", human(safe), f"top {len(rows)} candidates")}
{_card("Disk fills in", f"{days:.0f} days" if days else "—",
       f"{human(forecast.rate(files))}/day")}
</div>

<div class="panel">
<h2>Where the space went</h2>
<p class="h">Coloured by whether you can get the file back, not by size.
Green is free money. Red is irreplaceable.</p>
{chart}
</div>

<div class="panel">
<h2>Safe to delete</h2>
<p class="h">Ranked by size &times; how long untouched &times; how safe it is to lose.</p>
<table><thead><tr><th>Size</th><th>Kind</th><th class="num">Unused</th><th>Path</th></tr></thead>
<tbody>{body}</tbody></table>
<div class="guard"><b>{len(protected):,} files were held back.</b>
They are unique, untracked and uncached &mdash; nothing on this machine could
reproduce them, so they are never recommended, whatever their size.</div>
</div>
</div>"""

    Path(out).write_text(page, encoding="utf-8")
    return out
