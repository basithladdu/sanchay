"""Treemap coloured by regret, not by size.

Every disk visualiser draws the same treemap. This one colours each block by
how safe it is to delete, so the answer is visible without reading a table:
green blocks are free money, red blocks are irreplaceable.

plotly does the drawing.
"""
import pandas as pd
import plotly.express as px

from . import regret

COLOURS = {
    "disposable": "#22c55e",   # a build tool regenerates it
    "duplicate": "#84cc16",    # another copy survives
    "tracked": "#eab308",      # committed somewhere
    "unique": "#ef4444",       # nothing gets it back
}
DEPTH = 4


def treemap(files, dup_paths=frozenset(), out="storage.html", limit=4000):
    top = sorted(files, key=lambda f: f.size, reverse=True)[:limit]
    rows = []
    for f in top:
        parts = f.path.replace("\\", "/").strip("/").split("/")
        level = (parts[-DEPTH:] + [""] * DEPTH)[:DEPTH]
        rows.append({
            **{f"L{i}": p or "." for i, p in enumerate(level)},
            "size": f.size,
            "kind": regret.classify(f, f.path in dup_paths),
        })

    df = pd.DataFrame(rows)
    fig = px.treemap(df, path=[f"L{i}" for i in range(DEPTH)], values="size",
                     color="kind", color_discrete_map=COLOURS,
                     title="Disk usage by deletion regret")
    fig.update_traces(marker_line_width=0.5, marker_line_color="white")
    fig.write_html(out)
    return out
