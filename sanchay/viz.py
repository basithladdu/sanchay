"""Treemap coloured by recoverability evidence, not just by size.

Every disk visualiser draws the same treemap. This one distinguishes cache,
duplicate, clean-Git, and no-known-recovery evidence so a person can review the
storage context without treating colour as authorization to delete.

plotly does the drawing.
"""
import pandas as pd
import plotly.express as px
from pathlib import Path

from . import regret

COLOURS = {
    "disposable": "#22c55e",   # a build tool regenerates it
    "duplicate": "#84cc16",    # another copy survives
    "tracked": "#eab308",      # committed somewhere
    "unique": "#ef4444",       # nothing gets it back
}
DEPTH = 4


def _relative_parts(path, root):
    if root is None:
        return path.replace("\\", "/").strip("/").split("/")
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).parts
    except (OSError, ValueError):
        return ("outside selected root", Path(path).name)


def figure(files, dup_paths=frozenset(), limit=4000, root=None):
    top = sorted(files, key=lambda f: f.size, reverse=True)[:limit]
    rows = []
    for f in top:
        parts = list(_relative_parts(f.path, root))
        level = (parts[-DEPTH:] + [""] * DEPTH)[:DEPTH]
        rows.append({
            **{f"L{i}": p or "." for i, p in enumerate(level)},
            "size": f.size,
            "kind": regret.classify(f, f.path in dup_paths),
        })

    df = pd.DataFrame(rows)
    fig = px.treemap(df, path=[f"L{i}" for i in range(DEPTH)], values="size",
                     color="kind", color_discrete_map=COLOURS,
                     title="Disk usage by recoverability evidence")
    fig.update_traces(marker_line_width=0.5, marker_line_color="white")
    fig.update_layout(margin=dict(t=10, l=0, r=0, b=0),
                      paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)",
                      font_color="#94a3b8", title=None)
    return fig


def treemap(files, dup_paths=frozenset(), out="storage.html", limit=4000, root=None):
    figure(files, dup_paths, limit, root).write_html(out)
    return out
