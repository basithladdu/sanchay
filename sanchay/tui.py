"""The interface.

A disk tool belongs in the terminal -- that is where the disks are, and it is
the only place that works over ssh on a box with no desktop. ncdu got that
right. This is the same idea with the regret model wired in, so the colour of a
row shows the available recovery-evidence class rather than authorizing action.

Built on Textual.
"""
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import DataTable, Footer, Header, Static

from . import dedup, forecast, managed, mounts, plan, processes, scan, storage

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
    #status { margin: 0 2; color: $accent; text-style: italic; }
    #table { margin: 1 2; height: 1fr; border: round $primary 30%; }
    #guard { margin: 0 2 1 2; color: $text-muted; }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "rescan", "Rescan"),
        ("s", "sort_size", "Sort by size"),
        ("p", "sort_priority", "Sort by priority"),
        ("a", "filter_all", "All reviewable"),
        ("d", "filter_disposable", "Disposable"),
        ("u", "filter_duplicate", "Duplicates"),
        ("t", "filter_tracked", "Tracked"),
    ]
    TITLE = "SANCHAY"
    SUB_TITLE = " Regret-Aware Storage Intelligence for Linux"

    def __init__(self, root="."):
        super().__init__()
        self.root = root
        self.all_rows = []
        self.rows = []
        self.active_filter = "all"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="stats"):
            yield Stat("on disk")
            yield Stat("duplicated")
            yield Stat("reviewable")
            yield Stat("first-pass runway")
        yield Static("Scanning filesystem...", id="status")
        yield DataTable(id="table", zebra_stripes=True, cursor_type="row")
        yield Static("", id="guard")
        yield Footer()

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_column("Size", width=11)
        table.add_column("Kind", width=14)
        table.add_column("Unchanged", width=11)
        table.add_column("Path")
        self.scan_disk()

    @work(thread=True)
    def scan_disk(self):
        files = scan.scan(self.root)
        groups = dedup.duplicates(managed.content_candidates(files), root=self.root)
        filesystem_context = mounts.capacity_context(self.root)
        cleanup_plan = plan.build(files, groups, self.root, limit=500,
                                  filesystem_context=filesystem_context)
        rows = cleanup_plan["recommendations"]
        protected = cleanup_plan["safety"]["protected_unique_files"]
        hardlinks = cleanup_plan["safety"]["excluded_hardlink_entries"]
        managed_storage = cleanup_plan["safety"]["managed_operational_storage"]
        devices = {getattr(info, "device", None)
                   for info in storage.physical_records(files)}
        held_deleted = processes.deleted_open_files(
            {device for device in devices if device is not None})
        self.call_from_thread(self.show, files, groups, rows, protected, hardlinks,
                              managed_storage, held_deleted, filesystem_context)

    def show(self, files, groups, rows, protected, hardlinks, managed_storage,
             held_deleted, filesystem_context):
        self.all_rows = rows
        self.rows = list(rows)
        stats = self.query(Stat)
        stats[0].set(human(storage.physical_bytes(files)),
                     f"{len(files):,} entries; {storage.hardlink_alias_count(files):,} aliases")
        stats[1].set(human(dedup.reclaimable(groups)), f"{len(groups):,} groups")
        stats[2].set(human(sum(r['size'] for r in rows)), f"{len(rows):,} reviewable")
        try:
            import shutil
            days = forecast.days_until_full(files, shutil.disk_usage(self.root).free)
        except OSError:
            days = None
        stats[3].set(forecast.runway_label(days),
                     f"{human(forecast.rate(files))}/day mtime estimate")

        self.update_status_bar()
        guard = Text.assemble(
            (f"{protected:,} files held back. ", "bold red"),
            ("Unique, untracked, uncached files have no known reproducibility "
             "proof, so they are excluded from the review plan. ", "dim"),
            (f"{hardlinks:,} hardlinked entries are also excluded because one link removal frees no bytes. ",
             "dim"))
        if managed_storage:
            deferred_entries = sum(item["entries"] for item in managed_storage)
            deferred_bytes = sum(item["allocated_bytes"] for item in managed_storage)
            guard.append(
                f"{deferred_entries:,} system-managed entries ({human(deferred_bytes)}) are deferred to their owning tools.",
                style="dim")
        if held_deleted:
            guard.append(
                f" {len(held_deleted):,} deleted inode(s) ({human(processes.allocated_total(held_deleted))}) are held open by process descriptors and excluded from the plan.",
                style="dim")
        if filesystem_context and filesystem_context.get("advisory"):
            guard.append(
                f" {filesystem_context['label']}: {filesystem_context['advisory']}",
                style="dim")
        self.query_one("#guard", Static).update(guard)
        self.fill()

    def update_status_bar(self):
        self.query_one("#status", Static).update(Text.assemble(
            ("Target: ", "dim"), (f"{self.root}  ", "bold"),
            ("Filter: ", "dim"), (f"[{self.active_filter.upper()}]  ", "bold cyan"),
            ("Keys: [s]ize [p]riority [a]ll [d]isposable d[u]plicate [t]racked [r]escan", "dim italic")
        ))

    def fill(self):
        table = self.query_one(DataTable)
        table.clear()
        for r in self.rows:
            table.add_row(
                Text(human(r["size"]), justify="right"),
                Text(r["kind"].upper(), style=KIND_STYLE[r["kind"]]),
                Text(f"{r['staleness'] * 365:.0f} d", justify="right", style="dim"),
                Text(tail(r["path"]), style="dim"))

    def action_rescan(self):
        self.query_one("#status", Static).update("Scanning filesystem...")
        self.scan_disk()

    def action_sort_size(self):
        self.rows.sort(key=lambda r: r["size"], reverse=True)
        self.fill()

    def action_sort_priority(self):
        self.rows.sort(key=lambda r: r["priority"], reverse=True)
        self.fill()

    def action_filter_all(self):
        self.active_filter = "all"
        self.rows = list(self.all_rows)
        self.update_status_bar()
        self.fill()

    def action_filter_disposable(self):
        self.active_filter = "disposable"
        self.rows = [r for r in self.all_rows if r["kind"] == "disposable"]
        self.update_status_bar()
        self.fill()

    def action_filter_duplicate(self):
        self.active_filter = "duplicate"
        self.rows = [r for r in self.all_rows if r["kind"] == "duplicate"]
        self.update_status_bar()
        self.fill()

    def action_filter_tracked(self):
        self.active_filter = "tracked"
        self.rows = [r for r in self.all_rows if r["kind"] == "tracked"]
        self.update_status_bar()
        self.fill()


def run(root="."):
    Sanchay(root).run()

