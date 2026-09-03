"""Interactive slash-command shell for SANCHAY."""
import cmd
import copy
from concurrent.futures import CancelledError
from dataclasses import replace
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shlex
import threading
from urllib.parse import quote
import webbrowser

from . import actions, advisor, archive, dedup, plan
from .jobs import BackgroundTasks
from .paths import report_destination
from .session import ScanSession
from .spinner import LoadingIndicator, format_elapsed


HELP_ROWS = (
    ("/analyze <path> [options]", "Scan, show candidates, and create an HTML report"),
    ("/run <path> [options]", "Short alias for /analyze"),
    ("/scan <path>", "Scan a folder and retain its evidence"),
    ("/refresh", "Rescan the active target after files change"),
    ("/ai [status|auto|ollama|api|off]", "Inspect or configure hybrid AI reasoning"),
    ("/status", "Show active scan, artifact, and permission status"),
    ("/coverage", "Show whether the scan inspected its full scope"),
    ("/candidates [limit]", "List ranked review candidates"),
    ("/archives [limit]", "List AI-ranked archive-review candidates"),
    ("/duplicates [limit]", "List byte-confirmed duplicate groups"),
    ("/target <size|clear>", "Set or clear a reclaim target"),
    ("/report [name.html]", "Write the active report into Downloads"),
    ("/serve [port]", "Host the latest report as a background task"),
    ("/open-report", "Open the latest report in the default browser"),
    ("/ps", "List SANCHAY background tasks"),
    ("/stop <id|all>", "Stop one or all background tasks"),
    ("/plan [name.json]", "Write the active integrity-checked review plan"),
    ("/verify-plan <plan.json>", "Recheck a saved plan and file identities"),
    ("/verify-archive <source> <copy>", "Verify a separate byte-matched copy"),
    ("/permissions <action>", "View, enable, or disable action permission"),
    ("/delete <number>", "Preview or execute one guarded deletion"),
    ("/move <number> <destination>", "Preview or execute one guarded move"),
    ("/clean", "Preview or clean regenerable candidates only"),
    ("/about", "Explain what SANCHAY does and its safety boundary"),
    ("/help [command]", "Show this table or help for one command"),
    ("/clear", "Clear the terminal without clearing scan state"),
    ("/exit", "Stop background tasks and close SANCHAY"),
)


def split_arguments(value):
    """Split quoted shell arguments without consuming Windows backslashes."""
    lexer = shlex.shlex(value, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = ""
    return list(lexer)


def human(number):
    number = float(number)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(number) < 1024:
            return f"{number:.1f}{unit}"
        number /= 1024
    return f"{number:.1f}PB"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *args):
        return


class ReportServer:
    """Serve exactly one report directory on the loopback interface."""

    def __init__(self):
        self.httpd = None
        self.thread = None
        self.report_path = None
        self.url = None

    def start(self, report_path, port=8000):
        self.stop()
        report_path = Path(report_path).resolve()
        if not report_path.is_file():
            raise ValueError("The latest report file no longer exists")
        handler = partial(_QuietHandler, directory=str(report_path.parent))
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
        except OSError as exc:
            raise ValueError(f"Cannot start local report server on port {port}: {exc}") from exc
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        actual_port = httpd.server_address[1]
        self.httpd = httpd
        self.thread = thread
        self.report_path = str(report_path)
        self.url = f"http://127.0.0.1:{actual_port}/{quote(report_path.name)}"
        return self.url

    def stop(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)
        self.httpd = None
        self.thread = None
        self.report_path = None
        self.url = None


class _BackgroundOperation:
    """Cooperatively cancellable work owned by one interactive shell."""

    def __init__(self, description):
        self.description = description
        self.cancel_event = threading.Event()
        self.finished_event = threading.Event()
        self.committed_event = threading.Event()
        self.thread = None
        self._phase = "queued"
        self._lock = threading.Lock()

    def set_phase(self, value):
        with self._lock:
            self._phase = str(value)
        if value in {"cancelled", "failed", "complete"}:
            self.finished_event.set()

    def details(self):
        with self._lock:
            phase = self._phase
        return f"{phase}: {self.description}"

    def status(self):
        if self.committed_event.is_set():
            return "finishing"
        return "cancelling" if self.cancel_event.is_set() else "running"

    def cancel(self):
        with self._lock:
            if self.committed_event.is_set() or self.finished_event.is_set():
                return False
            already_requested = self.cancel_event.is_set()
            self.cancel_event.set()
            self._phase = "cancellation requested"
            return not already_requested

    def publish(self, callback):
        """Serialize the final cancel check with publication of completed work."""
        with self._lock:
            if self.cancel_event.is_set():
                raise CancelledError
            callback()
            self.committed_event.set()

    def alive(self):
        if self.finished_event.is_set():
            return False
        if self.thread is None:
            return True
        # A registered thread has a very small pre-start window where
        # is_alive() is false.  Keep the task visible until start() runs.
        return self.thread.ident is None or self.thread.is_alive()


class SanchayShell(cmd.Cmd):
    intro = (
        "SANCHAY - evidence-first storage review and recovery assistant\n"
        "It uses local learned recommendations, protects unique files, and creates auditable HTML reports.\n"
        "Read-only commands are available immediately. File actions are disabled.\n"
        "Type / for the command menu, or run /help for full usage."
    )
    prompt = "sanchay> "

    def __init__(self, session=None, stdin=None, stdout=None, report_server=None):
        super().__init__(stdin=stdin, stdout=stdout)
        self.use_rawinput = stdin is None
        self.identchars += "-"
        self._raw_input_line = ""
        self.session = session or ScanSession()
        self.permission = actions.ActionPermission()
        self.report_server = report_server or ReportServer()
        self.background_tasks = BackgroundTasks()
        self.background_work_enabled = False
        self._output_lock = threading.RLock()
        self._session_lock = threading.RLock()
        self._closing = False
        try:
            self.advisor_config = advisor.config_from_environment(
                default_provider="auto")
            self.advisor_config_error = None
        except ValueError as exc:
            self.advisor_config = advisor.AdvisorConfig(provider="off")
            self.advisor_config_error = str(exc)

    def parseline(self, line):
        self._raw_input_line = line.strip()
        stripped = line.strip()
        if stripped.startswith("/"):
            stripped = stripped[1:]
        command, argument, parsed = super().parseline(stripped)
        if command:
            command = command.replace("-", "_")
        return command, argument, parsed

    def cmdloop(self, intro=None):
        """Use the slash-command palette for a real terminal session."""
        from .palette import can_use_palette, run_palette_loop
        if can_use_palette(self):
            return run_palette_loop(self, intro=intro)
        return super().cmdloop(intro=intro)

    def emptyline(self):
        return None

    def default(self, line):
        path = self._pasted_path(self._raw_input_line)
        if path is not None:
            if os.path.isfile(path):
                folder = str(Path(path).resolve().parent)
                self._write(
                    "That is a file path, not a SANCHAY command.\n"
                    "SANCHAY scans folders. To scan the containing folder, use:\n"
                    f'  /scan "{folder}"\n'
                    "Candidate actions use the number shown by /candidates, for example /delete 2.")
            else:
                self._write(
                    "That looks like a path, but paths must follow a command.\n"
                    f'  To scan it: /scan "{path}"\n'
                    "  To choose a report file: /report \"path-to-report.html\"")
            return
        command = line.split(None, 1)[0] if line.strip() else line
        self._write(f"Unknown command: /{command}. Run /help.")

    def do_help(self, argument):
        """Show slash-command help."""
        if argument.strip():
            topic = argument.strip().lstrip("/").replace("-", "_")
            return super().do_help(topic)
        command_width = max(len(command) for command, _ in HELP_ROWS)
        lines = [
            "SANCHAY command reference",
            "COMMAND".ljust(command_width) + "  PURPOSE",
            "-" * command_width + "  " + "-" * 52,
        ]
        lines.extend(
            command.ljust(command_width) + "  " + purpose
            for command, purpose in HELP_ROWS)
        lines.extend((
            "",
            "Analyze options: --report <filename.html> --limit <n> "
            "[--replace] [--cross-filesystems]",
            "Interactive work: analyze, scan, and refresh run in the background; "
            "use /ps, Esc, or /stop <id>.",
            "Reports: interactive HTML reports are always stored in Downloads.",
            "Safety: delete, move, and clean are previews until temporary permission, "
            "--execute, exact confirmation, and evidence checks all pass.",
            "Type /about for a description of SANCHAY and its operating boundary.",
        ))
        self._write("\n".join(lines))

    def do_about(self, argument):
        """Explain SANCHAY's purpose and safety boundary."""
        if argument.strip():
            self._write("Usage: /about")
            return
        self._write(
            "SANCHAY is a local, evidence-first storage review assistant.\n"
            "It inventories allocated storage and runs a local learned classifier over "
            "metadata and positive usage evidence to recommend Keep, Cleanup Review, or "
            "Archive Review. Deterministic recovery gates prohibit unique and hardlinked "
            "files from cleanup.\n"
            "Usage model: sanchay_local_action_classifier v1 "
            "(multiclass logistic regression, trained locally from the bundled disclosed "
            "seed profiles). A constrained Ollama or OpenAI-compatible reasoning model "
            "can keep or confirm the resulting Cleanup and Archive reviews.\n\n"
            "It creates an auditable HTML report in Downloads and can host that report "
            "on 127.0.0.1 as a managed background task. File actions are separate, "
            "disabled by default, and require temporary permission plus exact confirmation.\n\n"
            "The AI records probabilities and top factors but has no file-action authority. "
            "SANCHAY does not upload scanned file paths or contents and does not elevate "
            "your operating-system permissions.")

    def do_ai(self, argument):
        """Inspect or configure the hybrid recommendation provider for future scans."""
        try:
            tokens = split_arguments(argument)
        except ValueError as exc:
            self._write(f"AI arguments are invalid: {exc}")
            return
        if not tokens or tokens == ["status"]:
            self._write("\n".join(self._ai_status_lines()))
            return
        mode = advisor.PROVIDER_ALIASES.get(tokens[0].lower(), tokens[0].lower())
        if mode not in advisor.PROVIDERS or len(tokens) > 2:
            self._write(
                "Usage: /ai [status|auto|ollama|api|off] [model]\n"
                "  auto/hybrid: prefer local Ollama, then an explicitly configured API\n"
                "  ollama/local: use only local Ollama\n"
                "  api: use only SANCHAY_AI_API_* environment configuration\n"
                "  off: use only the local usage classifier")
            return
        model = tokens[1] if len(tokens) == 2 else None
        if mode == "api":
            self.advisor_config = replace(
                self.advisor_config,
                provider=mode,
                api_model=model or self.advisor_config.api_model,
            )
        elif mode in {"auto", "ollama"}:
            self.advisor_config = replace(
                self.advisor_config,
                provider=mode,
                ollama_model=model or self.advisor_config.ollama_model,
            )
        else:
            if model is not None:
                self._write("The off mode does not accept a model name.")
                return
            self.advisor_config = replace(self.advisor_config, provider="off")
        self.advisor_config_error = None
        self._write("\n".join(self._ai_status_lines()))
        self._write("The setting applies to the next /analyze, /scan, or /refresh.")

    def do_analyze(self, argument):
        """Scan a location, show candidates, and generate its HTML report."""
        try:
            root, output, limit, replace, cross_filesystems = (
                self._analyze_arguments(argument))
        except ValueError as exc:
            self._write(
                "Usage: /analyze <path> [--report <filename.html>] [--limit <number>] "
                "[--replace] [--cross-filesystems]\n"
                f"Reason: {exc}")
            return

        try:
            report_path = report_destination(output)
        except (OSError, ValueError) as exc:
            self._write(f"Report destination is unavailable: {exc}")
            return
        if report_path.exists() and not replace:
            self._write(
                "Report already exists; choose another --report path or add --replace.")
            return

        self._write(f"Analysis target: {root}")
        if self.background_work_enabled:
            description = f"analyze {root}"

            def analyze(operation):
                working = copy.copy(self.session)
                operation.set_phase("scanning and verifying recovery evidence")
                summary = working.scan(
                    root, cross_filesystems=cross_filesystems,
                    cancel_event=operation.cancel_event,
                    advisor_config=self.advisor_config)
                operation.set_phase("building the HTML report")
                if report_path.exists() and not replace:
                    raise ValueError(
                        "the report destination appeared while the scan was running; "
                        "choose another name or use --replace")
                written = working.write_report(
                    str(report_path), cancel_event=operation.cancel_event)
                operation.set_phase("publishing completed evidence")
                self._publish_background_session(operation, working)
                lines = self._summary_lines(summary, heading="Scan complete")
                rows = working.candidates(limit)
                if rows:
                    lines.extend(("", *self._candidate_lines(rows)))
                else:
                    lines.extend(("", "The active plan contains no reviewable candidates."))
                archive_rows = working.archive_candidates(limit)
                if archive_rows:
                    lines.extend(("", *self._archive_lines(archive_rows)))
                lines.extend((
                    "",
                    "Analysis complete.",
                    f"Report created: {written}",
                    "When you want to host it, run /serve separately.",
                ))
                return "\n".join(lines)

            self._start_background_operation("analysis", description, analyze)
            return
        try:
            with LoadingIndicator(
                    self.stdout, "Scanning and verifying recovery evidence"):
                summary = self.session.scan(
                    root, cross_filesystems=cross_filesystems)
        except KeyboardInterrupt:
            self._write("Analysis cancelled; the previous completed scan remains active.")
            return
        except (OSError, RuntimeError, ValueError) as exc:
            self._write(f"Scan failed: {exc}")
            return

        self.permission.disable()
        self._retire_report_server()
        self._print_summary(summary, heading="Scan complete")
        try:
            rows = self.session.candidates(limit)
        except (RuntimeError, ValueError) as exc:
            self._write(f"Candidates unavailable: {exc}")
            return
        if rows:
            self._write("\n".join(self._candidate_lines(rows)))
        else:
            self._write("The active plan contains no reviewable candidates.")
        archive_rows = self.session.archive_candidates(limit)
        if isinstance(archive_rows, (list, tuple)) and archive_rows:
            self._write("\n".join(self._archive_lines(archive_rows)))

        self._write("HTML report destination: " + str(report_path))
        try:
            with LoadingIndicator(self.stdout, "Building the HTML report"):
                written = self.session.write_report(str(report_path))
        except ModuleNotFoundError:
            self._write(
                'Report dependencies are unavailable; install with: pip install -e ".[viz]"')
            return
        except (OSError, RuntimeError, ValueError) as exc:
            self._write(f"Report was not written: {exc}")
            return
        self._write(
            "Analysis complete.\n"
            f"Report created: {written}\n"
            "When you want to host it, run /serve separately.")

    do_run = do_analyze

    def do_scan(self, argument):
        """Scan a drive or directory and retain the resulting evidence."""
        try:
            tokens = split_arguments(argument)
        except ValueError as exc:
            self._write(f"Scan arguments are invalid: {exc}")
            return
        cross_filesystems = "--cross-filesystems" in tokens
        tokens = [token for token in tokens if token != "--cross-filesystems"]
        if len(tokens) != 1:
            self._write("Usage: /scan <path> [--cross-filesystems]")
            return
        if self.background_work_enabled:
            target = tokens[0]

            def scan_in_background(operation):
                working = copy.copy(self.session)
                operation.set_phase(f"scanning and verifying {target}")
                summary = working.scan(
                    target, cross_filesystems=cross_filesystems,
                    cancel_event=operation.cancel_event,
                    advisor_config=self.advisor_config)
                operation.set_phase("publishing completed evidence")
                self._publish_background_session(operation, working)
                return "\n".join(self._summary_lines(summary, heading="Scan complete"))

            self._start_background_operation(
                "scan", f"scan {target}", scan_in_background)
            return
        try:
            with LoadingIndicator(
                    self.stdout, f"Scanning and verifying {tokens[0]}"):
                summary = self.session.scan(
                    tokens[0], cross_filesystems=cross_filesystems)
        except KeyboardInterrupt:
            self._write("Scan cancelled; the previous completed scan remains active.")
            return
        except (OSError, RuntimeError, ValueError) as exc:
            self._write(f"Scan failed: {exc}")
            return
        self.permission.disable()
        self._retire_report_server()
        self._print_summary(summary, heading="Scan complete")

    def do_refresh(self, argument):
        """Repeat the active scan and discard temporary action permission."""
        if argument.strip():
            self._write("Usage: /refresh")
            return
        if not self._require_scan():
            return
        root = self.session.root
        cross_filesystems = self.session.cross_filesystems
        if self.background_work_enabled:

            def refresh_in_background(operation):
                working = copy.copy(self.session)
                operation.set_phase(f"refreshing scan evidence for {root}")
                summary = working.scan(
                    root, cross_filesystems=cross_filesystems,
                    cancel_event=operation.cancel_event,
                    advisor_config=self.advisor_config)
                operation.set_phase("publishing completed evidence")
                self._publish_background_session(operation, working)
                return "\n".join(self._summary_lines(summary, heading="Refresh complete"))

            self._start_background_operation(
                "refresh", f"refresh {root}", refresh_in_background)
            return
        try:
            with LoadingIndicator(self.stdout, f"Refreshing scan evidence for {root}"):
                summary = self.session.scan(
                    root, cross_filesystems=cross_filesystems)
        except KeyboardInterrupt:
            self._write("Refresh cancelled; the previous completed scan remains active.")
            return
        except (OSError, RuntimeError, ValueError) as exc:
            self._write(f"Refresh failed: {exc}")
            return
        self.permission.disable()
        self._retire_report_server()
        self._print_summary(summary, heading="Refresh complete")

    def do_status(self, argument):
        """Show the active scan and artifact status."""
        if argument.strip():
            self._write("Usage: /status")
            return
        if not self._require_scan():
            return
        self._print_summary(self.session.summary(), heading="Active scan")
        selection = self.session.active_plan.get("selection")
        if selection:
            state = "met" if selection["target_met"] else "not met"
            self._write(
                f"  target: {human(selection['target_reclaim_bytes'])}; "
                f"selected {human(selection['selected_reclaim_bytes'])} ({state})")
        self._write(f"  report: {self.session.last_report or 'not generated'}")
        self._write(f"  plan: {self.session.last_plan or 'not written'}")
        if getattr(self.session, "stale", False):
            self._write("  evidence: stale after a file action; /refresh is required")
        self._write(
            "  file actions: " + ("authorized" if self.permission.enabled else "disabled"))

    def do_coverage(self, argument):
        """Show what the active scan could and could not inspect."""
        if argument.strip():
            self._write("Usage: /coverage")
            return
        if not self._require_scan():
            return
        coverage = self.session.coverage
        if coverage["complete"]:
            self._write("Coverage complete: all in-scope, non-sensitive paths were inspected.")
        else:
            self._write(
                "Coverage incomplete: "
                f"{coverage['unreadable_directories']:,} directories and "
                f"{coverage['unreadable_files']:,} files could not be inspected.")
            self._write(
                "Capacity trends and whole-tree claims are withheld from this partial view.")

    def do_candidates(self, argument):
        """List ranked candidates from the active verified plan."""
        if not self._require_fresh_scan():
            return
        try:
            tokens = split_arguments(argument)
            if len(tokens) > 1:
                raise ValueError
            limit = int(tokens[0]) if tokens else 20
            rows = self.session.candidates(limit)
        except (TypeError, ValueError):
            self._write("Usage: /candidates [positive-limit]")
            return
        if not rows:
            self._write("The active plan contains no reviewable candidates.")
            return
        self._write("\n".join(self._candidate_lines(rows)))

    def do_archives(self, argument):
        """List AI-ranked archive reviews from the active verified plan."""
        if not self._require_fresh_scan():
            return
        try:
            tokens = split_arguments(argument)
            if len(tokens) > 1:
                raise ValueError
            limit = int(tokens[0]) if tokens else 20
            rows = self.session.archive_candidates(limit)
        except (TypeError, ValueError):
            self._write("Usage: /archives [positive-limit]")
            return
        if not rows:
            self._write("The AI model produced no archive-review candidates.")
            return
        self._write("\n".join(self._archive_lines(rows)))

    def do_duplicates(self, argument):
        """Show digest-matched content groups from the active scan."""
        if not self._require_fresh_scan():
            return
        try:
            tokens = split_arguments(argument)
            if len(tokens) > 1:
                raise ValueError
            limit = int(tokens[0]) if tokens else 10
            if limit <= 0:
                raise ValueError
        except (TypeError, ValueError):
            self._write("Usage: /duplicates [positive-limit]")
            return
        lines = [
            f"Duplicates from active scan: {self.session.root}",
            f"{len(self.session.groups):,} groups; "
            f"{human(self.session.summary()['duplicate_reclaimable_bytes'])} "
            "potential allocated reclaim.",
        ]
        for index, group in enumerate(self.session.groups[:limit], start=1):
            reclaimable = dedup.reclaimable([group])
            lines.append(
                f"{index}. {len(group)} physical copies; about {human(reclaimable)} reviewable")
            for info in group[:3]:
                lines.append("     " + self._relative(info.path))
            if len(group) > 3:
                lines.append(f"     +{len(group) - 3} more")
        lines.append(
            "Every duplicate recommendation is byte-confirmed again when its plan is built.")
        self._write("\n".join(lines))

    def do_target(self, argument):
        """Build a target-aware active plan or restore the default plan."""
        if not self._require_idle_storage_work("change the active reclaim target"):
            return
        if not self._require_fresh_scan():
            return
        value = argument.strip()
        if not value:
            self._write("Usage: /target <size|clear>")
            return
        if value.lower() == "clear":
            self.session.clear_target()
            self.permission.disable()
            self._write("Reclaim target cleared; the default review plan is active.")
            return
        try:
            from .cli import parse_reclaim_bytes
            selection = self.session.target(parse_reclaim_bytes(value))
        except (ValueError, RuntimeError) as exc:
            self._write(f"Target unavailable: {exc}")
            return
        self.permission.disable()
        state = "met" if selection["target_met"] else (
            f"short by {human(selection['shortfall_bytes'])}")
        self._write(
            f"Target {human(selection['target_reclaim_bytes'])}: "
            f"{human(selection['selected_reclaim_bytes'])} selected ({state}).")
        self._write("Run /candidates to review the selection before any action.")

    def do_report(self, argument):
        """Write an HTML report using the retained scan evidence."""
        if not self._require_idle_storage_work("generate a report"):
            return
        if not self._require_fresh_scan():
            return
        parsed = self._artifact_arguments(argument, self._timestamped("sanchay-report", ".html"))
        if parsed is None:
            self._write("Usage: /report [filename.html] [--replace]")
            return
        output, replace = parsed
        try:
            path = report_destination(output)
        except (OSError, ValueError) as exc:
            self._write(f"Report destination is unavailable: {exc}")
            return
        if path.exists() and not replace:
            self._write("Report already exists; add --replace to overwrite it.")
            return
        self._write("HTML report destination: " + str(path))
        try:
            with LoadingIndicator(self.stdout, "Building the HTML report"):
                written = self.session.write_report(str(path))
        except ModuleNotFoundError:
            self._write(
                'Report dependencies are unavailable; install with: pip install -e ".[viz]"')
            return
        except (OSError, RuntimeError, ValueError) as exc:
            self._write(f"Report was not written: {exc}")
            return
        self._write("Report created: " + written)
        self._write(
            "This report uses the active scan shown by /status. "
            "Run /open-report, or /serve for its exact browser URL.")

    def do_serve(self, argument):
        """Serve the latest HTML report on loopback only."""
        if not self.session.last_report:
            self._write("Generate a report with /report first.")
            return
        try:
            tokens = split_arguments(argument)
            if len(tokens) > 1:
                raise ValueError
            # Port zero asks the OS for a free local port. This avoids opening
            # a stale site that happens to own the conventional port 8000.
            port = int(tokens[0]) if tokens else 0
            if port < 0 or port > 65535:
                raise ValueError
        except (TypeError, ValueError):
            self._write("Usage: /serve [port from 0 to 65535]")
            return
        self.background_tasks.stop_kind("report-server")
        try:
            url = self.report_server.start(self.session.last_report, port=port)
        except ValueError as exc:
            self._write("Report server was not started: " + str(exc))
            self._write("Choose another port, for example /serve 8001.")
            return
        task = self.background_tasks.add(
            "report-server",
            url,
            stop_callback=self.report_server.stop,
            alive_callback=lambda: (
                self.report_server.thread is not None
                and self.report_server.thread.is_alive()),
        )
        self._write("Exact URL for the active scan report: " + url)
        self._write("The filename at the end matters; do not open an older server root URL.")
        self._write(
            f"Background task {task.id} is hosting the report. "
            f"Use /ps to view it or /stop {task.id} to close it.")

    def do_ps(self, argument):
        """List long-lived background services started by this shell."""
        if argument.strip():
            self._write("Usage: /ps")
            return
        tasks = self.background_tasks.active()
        if not tasks:
            self._write("No SANCHAY background tasks are running.")
            return
        lines = [" ID  status   elapsed  kind           details", "-" * 78]
        for task in tasks:
            lines.append(
                f"{task.id:>3}  {task.status:<9} "
                f"{self._elapsed(task.elapsed_seconds):>7}  "
                f"{task.kind:<13}  {task.details}")
        self._write("\n".join(lines))

    def do_stop(self, argument):
        """Stop one or all SANCHAY-managed background services."""
        value = argument.strip().lower()
        if value == "all":
            stopped = self.background_tasks.stop_all()
            if stopped:
                pending = sum(
                    task.cancellable and task.alive_callback()
                    and task.status != "finishing"
                    for task in stopped)
                finishing = sum(
                    task.cancellable and task.alive_callback()
                    and task.status == "finishing"
                    for task in stopped)
                if pending:
                    self._write(
                        f"Stop/cancellation requested for {len(stopped)} background "
                        f"task(s); {pending} will stop at a safe checkpoint.")
                elif finishing:
                    self._write(
                        f"Stopped stoppable services; {finishing} storage task(s) "
                        "had already published and are finishing output.")
                else:
                    self._write(f"Stopped {len(stopped)} background task(s).")
            else:
                self._write("No SANCHAY background tasks are running.")
            return
        try:
            task_id = int(value)
            if task_id <= 0:
                raise ValueError
        except ValueError:
            self._write("Usage: /stop <task-id|all>")
            return
        task = self.background_tasks.stop(task_id)
        if task is None:
            self._write(f"Background task {task_id} is not running. Use /ps to view tasks.")
        else:
            if (task.cancellable and task.alive_callback()
                    and task.status == "finishing"):
                self._write(
                    f"Background task {task.id} is finishing; completed evidence "
                    "has already been published.")
            elif task.cancellable and task.alive_callback():
                self._write(
                    f"Cancellation requested for background task {task.id}: "
                    f"{task.kind}. It will stop at the next safe checkpoint.")
            else:
                self._write(f"Stopped background task {task.id}: {task.kind}.")

    def do_open_report(self, argument):
        """Explicitly open the latest report in the default browser."""
        if argument.strip():
            self._write("Usage: /open-report")
            return
        if not self.session.last_report:
            self._write("Generate a report with /report first.")
            return
        target = self.report_server.url or Path(self.session.last_report).as_uri()
        if webbrowser.open(target):
            self._write("Opened: " + target)
        else:
            self._write("The browser did not open automatically. Use: " + target)

    def do_plan(self, argument):
        """Write the active integrity-checked plan."""
        if not self._require_idle_storage_work("write a plan"):
            return
        if not self._require_fresh_scan():
            return
        parsed = self._artifact_arguments(argument, self._timestamped("sanchay-plan", ".json"))
        if parsed is None:
            self._write("Usage: /plan [out.json] [--replace]")
            return
        output, replace = parsed
        try:
            written = self.session.write_plan(output, overwrite=replace)
        except (OSError, RuntimeError) as exc:
            self._write(f"Plan was not written: {exc}")
            return
        self._write("Review plan created: " + written)

    def do_verify_plan(self, argument):
        """Verify a saved plan without modifying its candidates."""
        try:
            tokens = split_arguments(argument)
            if len(tokens) != 1:
                raise ValueError
            document = plan.read(tokens[0])
            with LoadingIndicator(self.stdout, "Verifying saved plan identities"):
                result = plan.verify(document)
        except (OSError, ValueError):
            self._write("Usage: /verify-plan <plan.json>")
            return
        state = "valid for human review" if result["valid"] else "not valid for review"
        self._write(f"Plan is {state}; {result['checked']:,} recommendations checked.")
        if result.get("reason"):
            self._write("Reason: " + result["reason"])

    def do_verify_archive(self, argument):
        """Verify two separate regular files as byte-identical."""
        try:
            tokens = split_arguments(argument)
            if len(tokens) != 2:
                raise ValueError
            with LoadingIndicator(self.stdout, "Comparing archive contents"):
                result = archive.verify(tokens[0], tokens[1])
        except (OSError, ValueError):
            self._write("Usage: /verify-archive <source> <retained-copy>")
            return
        if result["verified"]:
            self._write(
                "Retained copy verified; manual-review reclaim: "
                + human(result["reclaimable_allocated_bytes"]))
        else:
            self._write("Retained copy not verified: " + result["reason"])

    def do_permissions(self, argument):
        """Inspect, enable, or disable temporary file-action permission."""
        try:
            tokens = split_arguments(argument)
        except ValueError:
            self._write("Permission arguments contain an unmatched quote.")
            return
        if not tokens or tokens == ["status"]:
            self._write(
                "File actions are " + ("authorized." if self.permission.enabled else "disabled."))
            if not self.permission.enabled:
                self._write(
                    "Enable for one action command with: /permissions enable "
                    + actions.AUTHORIZATION_PHRASE)
            return
        if tokens == ["disable"]:
            self.permission.disable()
            self._write("File actions disabled.")
            return
        if len(tokens) == 2 and tokens[0] == "enable":
            if not self._require_idle_storage_work("authorize file actions"):
                return
            if self.permission.enable(tokens[1]):
                self._write(
                    "File actions authorized for one action command. "
                    "Preview the command before adding --execute.")
            else:
                self._write("Authorization phrase did not match; file actions remain disabled.")
            return
        self._write("Usage: /permissions [status|disable|enable "
                    + actions.AUTHORIZATION_PHRASE + "]")

    def do_delete(self, argument):
        """Preview or explicitly delete one active-plan candidate."""
        if not self._require_idle_storage_work("change files"):
            return
        if not self._require_fresh_scan():
            return
        try:
            tokens = split_arguments(argument)
            index = int(tokens[0])
            item = actions.candidate(self.session.active_plan, index)
            execute, confirmation, values = self._execution_options(
                tokens[1:], value_options=("--retain",))
            retained_path = values.get("--retain")
        except (IndexError, TypeError, ValueError, actions.ActionDenied):
            self._write(
                "Usage: /delete <candidate-number> "
                "[--execute --confirm DELETE:number] [--retain <named-peer>]")
            return
        if not execute:
            self._write(
                f"PREVIEW only: permanently delete candidate {index}, "
                f"{human(item['size'])} {item['kind']}: {self._relative(item['path'])}")
            self._write(
                "To execute: authorize actions, then rerun with "
                f"--execute --confirm {actions.expected_confirmation('DELETE', index)}")
            if item["kind"] == "duplicate":
                self._write(
                    "Duplicate retention confirmation required: --retain \""
                    + item["survivor_path"] + "\"")
            return
        try:
            actions.delete(
                self.session.active_plan, index, self.permission, confirmation,
                retained_path=retained_path)
        except (OSError, actions.ActionDenied) as exc:
            self._write("Delete refused: " + str(exc))
        else:
            self._write("Deleted verified candidate: " + item["path"])
            self.session.mark_stale()
            self._write("The active scan is now stale; run /refresh before another action.")
        finally:
            self.permission.disable()

    def do_move(self, argument):
        """Preview or explicitly move one candidate without overwriting."""
        if not self._require_idle_storage_work("change files"):
            return
        if not self._require_fresh_scan():
            return
        try:
            tokens = split_arguments(argument)
            index = int(tokens[0])
            destination = tokens[1]
            item = actions.candidate(self.session.active_plan, index)
            execute, confirmation, _ = self._execution_options(tokens[2:])
        except (IndexError, TypeError, ValueError, actions.ActionDenied):
            self._write(
                "Usage: /move <candidate-number> <destination> "
                "[--execute --confirm MOVE:number]")
            return
        if not execute:
            self._write(
                f"PREVIEW only: move candidate {index}, {human(item['size'])} "
                f"{item['kind']}, to {destination}")
            self._write(
                "Execution refuses overwrites and cross-filesystem moves. "
                "Authorize actions, then rerun with "
                f"--execute --confirm {actions.expected_confirmation('MOVE', index)}")
            return
        try:
            _, written = actions.move(
                self.session.active_plan, index, destination,
                self.permission, confirmation)
        except (OSError, actions.ActionDenied) as exc:
            self._write("Move refused: " + str(exc))
        else:
            self._write("Moved verified candidate to: " + written)
            self.session.mark_stale()
            self._write("The active scan is now stale; run /refresh before another action.")
        finally:
            self.permission.disable()

    def do_clean(self, argument):
        """Preview or explicitly remove disposable active-plan candidates."""
        if not self._require_idle_storage_work("change files"):
            return
        if not self._require_fresh_scan():
            return
        try:
            tokens = split_arguments(argument)
            execute, confirmation, _ = self._execution_options(tokens)
        except ValueError:
            self._write("Usage: /clean [--execute --confirm CLEAN:number]")
            return
        targets = actions.disposable_candidates(self.session.active_plan)
        count = len(targets)
        size = sum(item["size"] for _, item in targets)
        if not targets:
            self._write("The active plan contains no disposable candidates to clean.")
            return
        if not execute:
            self._write(
                f"PREVIEW only: permanently delete {count} regenerable candidates "
                f"({human(size)}). Duplicate, tracked, unique, and hardlinked files are excluded.")
            self._write(
                "To execute: authorize actions, then rerun with "
                f"--execute --confirm CLEAN:{count}")
            return
        try:
            completed = actions.clean(
                self.session.active_plan, self.permission, confirmation)
        except (OSError, actions.ActionDenied) as exc:
            self._write("Clean refused: " + str(exc))
        else:
            self._write(
                f"Deleted {len(completed)} verified regenerable candidates ({human(size)}).")
            self.session.mark_stale()
            self._write("The active scan is now stale; run /refresh before another action.")
        finally:
            self.permission.disable()

    def do_clear(self, argument):
        """Clear the visible terminal without changing scan state."""
        if argument.strip():
            self._write("Usage: /clear")
            return
        with self._output_lock:
            self.stdout.write("\033[2J\033[H")
            self.stdout.flush()

    def do_exit(self, argument):
        """Exit SANCHAY and revoke temporary permissions."""
        if argument.strip():
            self._write("Usage: /exit")
            return False
        self._closing = True
        self.permission.disable()
        self.background_tasks.stop_all()
        self.report_server.stop()
        self._write("SANCHAY closed.")
        return True

    do_quit = do_exit

    def do_EOF(self, argument):
        self._write("")
        return self.do_exit(argument)

    def postloop(self):
        self._closing = True
        self.permission.disable()
        self.background_tasks.stop_all()
        self.report_server.stop()

    def _require_scan(self):
        if self.session.ready:
            return True
        self._write("No active scan. Run /scan <path> first.")
        return False

    def _require_fresh_scan(self):
        if not self._require_scan():
            return False
        if getattr(self.session, "stale", False) is True:
            self._write("The active scan is stale after a file action. Run /refresh first.")
            return False
        return True

    def _ai_status_lines(self):
        config = self.advisor_config.normalized()
        lines = [
            f"Hybrid AI mode: {config.provider}",
            "  usage prediction: sanchay_local_action_classifier v1 (always local)",
        ]
        if self.advisor_config_error:
            lines.append("  configuration warning: " + self.advisor_config_error)
        runtime = advisor.runtime_status(config)
        if runtime["ollama_available"]:
            models = ", ".join(runtime["ollama_models"])
            lines.append(
                "  Ollama: available; selected "
                + runtime["selected_ollama_model"]
                + (f"; installed {models}" if models else ""))
        else:
            lines.append(
                "  Ollama: unavailable; "
                + runtime.get("ollama_error", "no compatible model found"))
        api_state = "configured" if runtime["api_configured"] else "not configured"
        lines.append(
            f"  OpenAI-compatible API: {api_state}; API keys are never printed")
        if self.session.ready:
            last = self.session.active_plan.get("reasoning_model", {})
            provider = last.get("provider") or "local classifier fallback"
            model = f" {last['model']}" if last.get("model") else ""
            lines.append(
                f"  active scan reasoning: {last.get('status', 'unknown')} via "
                f"{provider}{model}")
        lines.append(
            "  safety: reasoning may keep or confirm a review; it cannot delete, "
            "promote an unsafe file, or bypass human approval")
        return lines

    def _require_idle_storage_work(self, purpose):
        task = self.background_tasks.latest_cancellable()
        if task is None:
            return True
        self._write(
            f"Cannot {purpose} while background task {task.id} is {task.status}. "
            f"Use /ps to inspect it or /stop {task.id} to cancel it.")
        return False

    def cancel_latest_background(self):
        """Request cooperative cancellation for the newest storage job."""
        task = self.background_tasks.latest_cancellable()
        if task is None:
            return False
        requested = task.stop_callback()
        if not requested:
            return False
        self._write(
            f"Cancellation requested for background task {task.id}. "
            + self._preserved_scan_message())
        return True

    def _preserved_scan_message(self):
        return (
            "The previous completed scan remains active."
            if self.session.ready else
            "No partial scan will be published."
        )

    def _publish_background_session(self, operation, working):
        """Atomically expose a fully completed scan and revoke action rights."""
        def publish():
            with self._session_lock:
                if self._closing:
                    raise CancelledError
                self.permission.disable()
                self._retire_report_server()
                self.session = working

        operation.publish(publish)

    def _retire_report_server(self):
        """Stop a server tied to evidence that is being replaced."""
        self.background_tasks.stop_kind("report-server")

    def _start_background_operation(self, kind, description, worker):
        """Start one interactive storage operation without blocking the prompt."""
        active = self.background_tasks.latest_cancellable()
        if active is not None:
            self._write(
                f"Background task {active.id} is already {active.status}. "
                f"Use /ps to inspect it or /stop {active.id} to cancel it.")
            return None

        self.permission.disable()
        operation = _BackgroundOperation(description)
        task_holder = {}

        def run_operation():
            task = task_holder["task"]
            try:
                result = worker(operation)
                if operation.cancel_event.is_set():
                    raise CancelledError
            except CancelledError:
                operation.set_phase("cancelled")
                if not self._closing:
                    self._write(
                        f"Background task {task.id} cancelled; "
                        + self._preserved_scan_message().lower())
            except ModuleNotFoundError:
                operation.set_phase("failed")
                if not self._closing:
                    self._write(
                        f"Background task {task.id} failed: report dependencies are "
                        'unavailable; install with: pip install -e ".[viz]"')
            except (OSError, RuntimeError, ValueError) as exc:
                operation.set_phase("failed")
                if not self._closing:
                    self._write(f"Background task {task.id} failed: {exc}")
            except Exception as exc:  # Keep an unexpected worker fault out of the prompt.
                operation.set_phase("failed")
                if not self._closing:
                    self._write(
                        f"Background task {task.id} failed unexpectedly: "
                        f"{type(exc).__name__}: {exc}")
            else:
                operation.set_phase("complete")
                if not self._closing:
                    self._write(
                        f"Background task {task.id} complete in "
                        f"{format_elapsed(task.elapsed_seconds)}.\n{result}")
            finally:
                # Permission is always one-use and must not survive a scan,
                # including a failed or cancelled one.
                self.permission.disable()

        thread = threading.Thread(
            target=run_operation,
            name=f"sanchay-{kind}",
            daemon=True,
        )
        operation.thread = thread
        task = self.background_tasks.add(
            kind,
            description,
            stop_callback=operation.cancel,
            alive_callback=operation.alive,
            status_callback=operation.status,
            details_callback=operation.details,
            cancellable=True,
        )
        task_holder["task"] = task
        self._write(f"Background task {task.id} started: {description}.")
        try:
            thread.start()
        except RuntimeError as exc:
            operation.set_phase("failed")
            self.background_tasks.active()
            self._write(f"Background task {task.id} could not start: {exc}")
            return None
        return task

    def _write(self, value):
        with self._output_lock:
            self.stdout.write(str(value) + "\n")
            self.stdout.flush()

    def _print_summary(self, summary, heading):
        self._write("\n".join(self._summary_lines(summary, heading)))

    @staticmethod
    def _summary_lines(summary, heading):
        lines = [f"{heading}: {summary['root']}"]
        lines.append(
            f"  {summary['file_entries']:,} entries; "
            f"{human(summary['allocated_bytes'])} allocated storage")
        lines.append(
            f"  {summary['duplicate_groups']:,} duplicate groups; "
            f"{human(summary['duplicate_reclaimable_bytes'])} potential reclaim")
        lines.append(
            f"  {summary['candidate_count']:,} reviewable; "
            f"{summary.get('archive_candidate_count', 0):,} archive reviews; "
            f"{summary['protected_unique_files']:,} unique files protected from cleanup")
        reasoning = summary.get("reasoning_model", {})
        if reasoning.get("status") == "completed":
            lines.append(
                f"  reasoning AI: {reasoning.get('provider')}/"
                f"{reasoning.get('model')}; "
                f"{reasoning.get('reviewed_candidate_count', 0):,} reviewed, "
                f"{reasoning.get('kept_count', 0):,} changed to keep")
        elif reasoning.get("status") == "unavailable":
            lines.append(
                "  reasoning AI: unavailable; safe local-classifier fallback used")
        else:
            lines.append("  reasoning AI: off; local usage classifier used")
        coverage = summary["coverage"]
        if coverage["complete"]:
            lines.append("  coverage: complete")
        else:
            lines.append(
                "  coverage: incomplete; "
                f"{coverage['unreadable_directories']:,} directories and "
                f"{coverage['unreadable_files']:,} files unreadable")
        return lines

    @staticmethod
    def _pasted_path(raw):
        """Return a likely pasted local path without treating it as a command."""
        value = raw.strip()
        if value.startswith('/') and len(value) > 1 and value[1] in "\"'":
            value = value[1:]
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        windows_path = len(value) >= 3 and value[1:3] in (":\\", ":/")
        posix_path = (
            value.startswith("/")
            and not value.startswith("//")
            and (value.count("/") >= 2 or os.path.exists(value))
        )
        if windows_path or posix_path:
            return os.path.expanduser(value)
        return None

    @staticmethod
    def _platform_name():
        return "Windows" if os.name == "nt" else "Linux"

    @staticmethod
    def _elapsed(seconds):
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h{minutes:02}m"
        if minutes:
            return f"{minutes}m{seconds:02}s"
        return f"{seconds}s"

    def _relative(self, path):
        try:
            return str(Path(path).resolve().relative_to(Path(self.session.root).resolve()))
        except (OSError, ValueError):
            return str(path)

    def _candidate_lines(self, rows):
        lines = [
            f"Candidates from active scan: {self.session.root}",
            " #  reclaim   kind         AI clean  unchanged  relative path",
            "-" * 90,
        ]
        for index, row in enumerate(rows, start=1):
            path = self._relative(row["path"])
            confidence = row.get("ai_assessment", {}).get("probabilities", {}).get(
                "cleanup_review", 0)
            lines.append(
                f"{index:>2}  {human(row['size']):>8}  {row['kind']:<11} "
                f"{confidence:>7.0%}  {row['staleness'] * 365:>8.1f}d  {path}")
        return lines

    def _archive_lines(self, rows):
        lines = [
            f"AI archive reviews from active scan: {self.session.root}",
            " #  allocated  confidence  unchanged  relative path",
            "-" * 90,
        ]
        for index, row in enumerate(rows, start=1):
            confidence = row["ai_assessment"]["probabilities"]["archive_review"]
            lines.append(
                f"{index:>2}  {human(row['size']):>9}  {confidence:>9.0%}  "
                f"{row['staleness'] * 365:>8.1f}d  {self._relative(row['path'])}")
        lines.append(
            "Archive is a recommendation only: choose a destination, copy separately, "
            "then verify it with /verify-archive.")
        return lines

    def _analyze_arguments(self, argument):
        try:
            tokens = split_arguments(argument)
        except ValueError as exc:
            raise ValueError(f"invalid quoting: {exc}") from exc

        root = None
        output = None
        limit = 10
        limit_seen = False
        replace = False
        cross_filesystems = False
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if (token == "--report" and output is None
                    and index + 1 < len(tokens)
                    and not tokens[index + 1].startswith("--")):
                output = tokens[index + 1]
                index += 2
                continue
            if token == "--limit" and index + 1 < len(tokens):
                if limit_seen:
                    raise ValueError("--limit was supplied more than once")
                try:
                    limit = int(tokens[index + 1])
                except ValueError as exc:
                    raise ValueError("--limit must be a positive whole number") from exc
                if limit <= 0:
                    raise ValueError("--limit must be a positive whole number")
                limit_seen = True
                index += 2
                continue
            if token == "--replace" and not replace:
                replace = True
                index += 1
                continue
            if token == "--cross-filesystems" and not cross_filesystems:
                cross_filesystems = True
                index += 1
                continue
            if token.startswith("--"):
                raise ValueError(f"unsupported or repeated option: {token}")
            if root is not None:
                raise ValueError("only one scan path may be supplied")
            root = token
            index += 1

        if root is None:
            raise ValueError("a scan path is required")
        if output is None:
            output = self._timestamped("sanchay-report", ".html")
        return root, output, limit, replace, cross_filesystems

    @staticmethod
    def _artifact_arguments(argument, default):
        try:
            tokens = split_arguments(argument)
        except ValueError:
            return None
        replace = "--replace" in tokens
        paths = [token for token in tokens if token != "--replace"]
        if len(paths) > 1 or any(token.startswith("--") for token in paths):
            return None
        return (paths[0] if paths else default), replace

    @staticmethod
    def _execution_options(tokens, value_options=()):
        execute = False
        confirmation = None
        values = {}
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token == "--execute" and not execute:
                execute = True
                index += 1
                continue
            if token == "--confirm" and confirmation is None and index + 1 < len(tokens):
                confirmation = tokens[index + 1]
                index += 2
                continue
            if token in value_options and token not in values and index + 1 < len(tokens):
                values[token] = tokens[index + 1]
                index += 2
                continue
            raise ValueError("Unsupported or repeated action option")
        return execute, confirmation, values

    @staticmethod
    def _timestamped(stem, suffix):
        from datetime import datetime
        return f"{stem}-{datetime.now().strftime('%Y%m%d-%H%M%S')}{suffix}"


def run(stdin=None, stdout=None):
    shell = SanchayShell(stdin=stdin, stdout=stdout)
    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        shell._write("\nInterrupted; SANCHAY closed.")
        shell.postloop()
    return 0
