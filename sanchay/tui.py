"""The interface.

A disk tool belongs in the terminal -- that is where the disks are, and it is
the only place that works over ssh on a box with no desktop. ncdu got that
right. This is the same idea with the regret model wired in, so the colour of a
row tells you whether you can afford to lose it.

Built on Textual.
"""
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Static

from . import dedup, forecast, regret, scan

KIND_STYLE = {
    "disposable": "bold green",
    "duplicate": "bold chartreuse3",
    "tracked": "bold yellow",
    "unique": "bold red",
}


def human(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"


class Stat(Static):
    """One number and what it means."""

    def __init__(self, label):
        super().__init__()
        self.label = label

    def on_mount(self):
        self.set("-")

    def set(self, value, note=""):
        self.update(Text.assemble(
            (self.label.upper() + "\n", "dim"),
            (value + "\n", "bold"),
            (note, "dim italic")))


def tail(path, width=64):
    """Keep the end of a path -- that is the part that identifies the file."""
    return path if len(path) <= width else "..." + path[-(width - 3):]


class Sanchay(App):
    CSS = """
    Screen { background: $surface; }
    #stats { height: 7; margin: 1 2 0 2; }
    Stat {
        width: 1fr; height: 7; padding: 1 2; margin-right: 1;
        border: round $primary 40%;
    }
    #table { margin: 1 2; height: 1fr; border: round $primary 30%; }
    #guard { margin: 0 2 1 2; color: $text-muted; }
    #status { margin: 0 2; color: $text-muted; }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "rescan", "Rescan"),
        ("s", "sort_size", "Sort by size"),
        ("p", "sort_priority", "Sort by priority"),
    ]
    TITLE = "SANCHAY"
    SUB_TITLE = " what is safe to delete"

    def __init__(self, root="."):
        super().__init__()
        self.root = root
        self.rows = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="stats"):
            yield Stat("on disk")
            yield Stat("duplicated")
            yield Stat("safe to reclaim")
            yield Stat("disk fills in")
        yield Static("scanning…", id="status")
        yield DataTable(id="table", zebra_stripes=True, cursor_type="row")
        yield Static("", id="guard")
        yield Footer()

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_column("Size", width=11)
        table.add_column("Kind", width=13)
        table.add_column("Unused", width=9)
        table.add_column("Path")
        self.scan_disk()

    @work(thread=True)
    def scan_disk(self):
        files = scan.scan(self.root)
        groups = dedup.duplicates(files)
        dups = {f.path for g in groups for f in g[1:]}
        rows = regret.rank(files, dups, limit=400)
        protected = sum(1 for f in files
                        if regret.classify(f, f.path in dups) == "unique")
        self.call_from_thread(self.show, files, groups, rows, protected)

    def show(self, files, groups, rows, protected):
        self.rows = rows
        stats = self.query(Stat)
        stats[0].set(human(sum(f.size for f in files)), f"{len(files):,} files")
        stats[1].set(human(dedup.reclaimable(groups)), f"{len(groups):,} groups")
        stats[2].set(human(sum(r['size'] for r in rows)), f"{len(rows):,} candidates")
        try:
            import shutil
            days = forecast.days_until_full(files, shutil.disk_usage(self.root).free)
        except OSError:
            days = None
        stats[3].set(f"{days:.0f} days" if days else "—",
                     f"{human(forecast.rate(files))}/day")

        self.query_one("#status", Static).update(
            Text(f"{self.root}", style="dim"))
        self.query_one("#guard", Static).update(Text.assemble(
            (f"{protected:,} files held back. ", "bold red"),
            ("Unique, untracked, uncached — nothing here could rebuild them, "
             "so they are never recommended, whatever their size.", "dim")))
        self.fill()

    def fill(self):
        table = self.query_one(DataTable)
        table.clear()
        for r in self.rows:
            table.add_row(
                Text(human(r["size"]), justify="right"),
                Text(r["kind"], style=KIND_STYLE[r["kind"]]),
                Text(f"{r['staleness'] * 365:.0f} d", justify="right", style="dim"),
                Text(tail(r["path"]), style="dim"))

    def action_rescan(self):
        self.query_one("#status", Static).update("scanning…")
        self.scan_disk()

    def action_sort_size(self):
        self.rows.sort(key=lambda r: r["size"], reverse=True)
        self.fill()

    def action_sort_priority(self):
        self.rows.sort(key=lambda r: r["priority"], reverse=True)
        self.fill()


def run(root="."):
    Sanchay(root).run()
