"""Cross-platform interactive slash-command palette for SANCHAY."""
from dataclasses import dataclass
import shutil
import sys

from prompt_toolkit import PromptSession, print_formatted_text, prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import CompleteStyle, clear
from prompt_toolkit.styles import Style

from .paths import downloads_directory


@dataclass(frozen=True)
class CommandChoice:
    name: str
    description: str
    accepts_arguments: bool = False


COMMAND_CHOICES = (
    CommandChoice("/analyze", "Scan, show candidates, and create an HTML report", True),
    CommandChoice("/run", "Short alias for /analyze", True),
    CommandChoice("/scan", "Scan a folder and retain its evidence", True),
    CommandChoice("/refresh", "Rescan the active target"),
    CommandChoice("/status", "Show the active scan and artifact status"),
    CommandChoice("/coverage", "Show scan completeness"),
    CommandChoice("/candidates", "Show ranked storage candidates", True),
    CommandChoice("/duplicates", "Show byte-confirmed duplicate groups", True),
    CommandChoice("/target", "Set or clear a reclaim target", True),
    CommandChoice("/report", "Generate an HTML report", True),
    CommandChoice("/serve", "Host the latest report on loopback", True),
    CommandChoice("/ps", "List running background tasks"),
    CommandChoice("/stop", "Stop a background task", True),
    CommandChoice("/open-report", "Open the latest report in a browser"),
    CommandChoice("/plan", "Write the active review plan", True),
    CommandChoice("/verify-plan", "Verify a saved plan", True),
    CommandChoice("/verify-archive", "Verify a retained byte-matched copy", True),
    CommandChoice("/permissions", "Control temporary file-action permission", True),
    CommandChoice("/delete", "Preview or execute one guarded deletion", True),
    CommandChoice("/move", "Preview or execute one guarded move", True),
    CommandChoice("/clean", "Preview or execute regenerable-file cleanup", True),
    CommandChoice("/about", "Explain SANCHAY and its safety boundary"),
    CommandChoice("/clear", "Clear the terminal"),
    CommandChoice("/help", "Show command help"),
    CommandChoice("/exit", "Close SANCHAY"),
    CommandChoice("/quit", "Close SANCHAY"),
)
ARGUMENT_COMMANDS = frozenset(
    choice.name for choice in COMMAND_CHOICES if choice.accepts_arguments)

WORDMARK_TEXT = "SANCHAY"
WORDMARK_GLYPHS = {
    "S": ("#######",
          "##.....",
          "#######",
          ".....##",
          "#######"),
    "A": ("#######",
          "##...##",
          "#######",
          "##...##",
          "##...##"),
    "N": ("##...##",
          "###..##",
          "####.##",
          "##.####",
          "##...##"),
    "C": ("#######",
          "##.....",
          "##.....",
          "##.....",
          "#######"),
    "H": ("##...##",
          "##...##",
          "#######",
          "##...##",
          "##...##"),
    "Y": ("##...##",
          ".#####.",
          "..###..",
          "..###..",
          "..###.."),
}
WORDMARK_GAP = 2
# A single echo, offset one cell down and right and drawn as a thin contour,
# gives the solid letters depth without closing up their counters.
WORDMARK_ECHOES = ((1, 1, "class:welcome-logo-shadow"),)
STORAGE_MARK = (
    (("class:storage-frame", " ╭────────╮ "),),
    (("class:storage-frame", "╭╯"),
     ("class:storage-red", "▓▓▓▓▓"),
     ("class:storage-empty", "░░░"),
     ("class:storage-frame", "╰╮")),
    (("class:storage-frame", "│"),
     ("class:storage-blue", "▓▓▓▓▓▓▓"),
     ("class:storage-empty", "░░░"),
     ("class:storage-frame", "│")),
    (("class:storage-frame", "╰╮"),
     ("class:storage-green", "▓▓▓"),
     ("class:storage-empty", "░░░░░"),
     ("class:storage-frame", "╭╯")),
    (("class:storage-frame", " ╰────────╯ "),),
)
STORAGE_MARK_WIDTH = 12
MARK_GUTTER = 3
CONTINUE_PROMPT = "Press Enter to continue... "


class SlashCommandCompleter(Completer):
    """Offer command choices only while the first slash word is being typed."""

    def get_completions(self, document, complete_event):
        value = document.text_before_cursor
        if not value.startswith("/") or any(character.isspace() for character in value):
            return
        fragment = value.lower()
        for choice in COMMAND_CHOICES:
            if not choice.name.startswith(fragment):
                continue
            # Once a no-argument command is complete, hide the menu so the
            # next Enter executes it instead of selecting it repeatedly.
            if fragment == choice.name and not choice.accepts_arguments:
                continue
            yield Completion(
                choice.name,
                start_position=-len(value),
                display=choice.name,
                display_meta=choice.description,
            )


PALETTE_STYLE = Style.from_dict({
    "prompt": "bold #63b3ff",
    "completion-menu": "bg:#101820 #d8e2ea",
    "completion-menu.completion": "bg:#101820 #d8e2ea",
    "completion-menu.completion.current": "bg:#0969da #ffffff bold",
    "completion-menu.meta.completion": "bg:#101820 #93a4b3",
    "completion-menu.meta.completion.current": "bg:#0969da #ffffff",
    "scrollbar.background": "bg:#253442",
    "scrollbar.button": "bg:#0969da",
    "bottom-toolbar": "bg:#18232d #b8c7d3",
    "welcome-logo": "#e07a5f bold",
    "welcome-logo-shadow": "#a2543f",
    "welcome-rule": "#3b4652",
    "welcome-title": "#f2f2f2 bold",
    "welcome-heading": "#f0b35a bold",
    "welcome-number": "#e07a5f bold",
    "welcome-text": "#d3d7dc",
    "welcome-muted": "#8f969e",
    "welcome-continue": "#8a8cff bold",
    "storage-frame": "#c8d0d8",
    "storage-empty": "#3b4652",
    "storage-red": "#ef6259 bold",
    "storage-blue": "#55a7ff bold",
    "storage-green": "#5fd38d bold",
})


def _wordmark_mask():
    """Build the boolean face of the wordmark, one cell per terminal column."""
    separator = " " * WORDMARK_GAP
    rows = []
    for row in range(len(WORDMARK_GLYPHS[WORDMARK_TEXT[0]])):
        line = separator.join(
            WORDMARK_GLYPHS[letter][row] for letter in WORDMARK_TEXT)
        rows.append([cell == "#" for cell in line])
    return rows


def _shifted(mask, down, right, height, width):
    """Copy a mask into a taller, wider grid at the given offset."""
    moved = [[False] * width for _ in range(height)]
    for row, cells in enumerate(mask):
        for column, filled in enumerate(cells):
            if filled and row + down < height and column + right < width:
                moved[row + down][column + right] = True
    return moved


def _edge_character(mask, row, column, height, width):
    """Draw one echo cell as the outline of the shape it belongs to."""
    def open_side(other_row, other_column):
        return not (0 <= other_row < height
                    and 0 <= other_column < width
                    and mask[other_row][other_column])

    up = open_side(row - 1, column)
    down = open_side(row + 1, column)
    left = open_side(row, column - 1)
    right = open_side(row, column + 1)
    if up and down:
        return "─"
    if left and right:
        return "│"
    if up and left:
        return "╭"
    if up and right:
        return "╮"
    if down and left:
        return "╰"
    if down and right:
        return "╯"
    if up or down:
        return "─"
    if left or right:
        return "│"
    return " "


def _run_fragments(cells):
    """Collapse neighbouring cells that share a style into single fragments."""
    fragments = []
    for style, character in cells:
        style = style or ""
        if fragments and fragments[-1][0] == style:
            fragments[-1] = (style, fragments[-1][1] + character)
        else:
            fragments.append((style, character))
    return fragments


def wordmark_rows():
    """Render the wordmark as a solid face trailed by its contour echo."""
    face = _wordmark_mask()
    height = len(face) + max(down for down, _, _ in WORDMARK_ECHOES)
    width = len(face[0]) + max(right for _, right, _ in WORDMARK_ECHOES)
    face = _shifted(face, 0, 0, height, width)
    cells = [[("", " ")] * width for _ in range(height)]
    for row in range(height):
        for column in range(width):
            if face[row][column]:
                cells[row][column] = ("class:welcome-logo", "█")
    covered = [row[:] for row in face]
    for down, right, style in WORDMARK_ECHOES:
        echo = _shifted(face, down, right, height, width)
        for row in range(height):
            for column in range(width):
                if not echo[row][column] or covered[row][column]:
                    continue
                cells[row][column] = (
                    style, _edge_character(echo, row, column, height, width))
        for row in range(height):
            for column in range(width):
                covered[row][column] = covered[row][column] or echo[row][column]
    return [_run_fragments(row) for row in cells]


def wordmark_width():
    """Report the column span of the rendered wordmark, echoes included."""
    letter_width = len(WORDMARK_GLYPHS[WORDMARK_TEXT[0]][0])
    return (len(WORDMARK_TEXT) * letter_width
            + (len(WORDMARK_TEXT) - 1) * WORDMARK_GAP
            + max(right for _, right, _ in WORDMARK_ECHOES))


def _banner_fragments(columns):
    """Lay out the wordmark, keeping the storage mark only when it fits."""
    rows = wordmark_rows()
    logo_width = wordmark_width()
    show_mark = columns >= logo_width + MARK_GUTTER + STORAGE_MARK_WIDTH
    height = max(len(rows), len(STORAGE_MARK)) if show_mark else len(rows)
    fragments = []
    for index in range(height):
        row = rows[index] if index < len(rows) else []
        fragments.extend(row)
        if show_mark and index < len(STORAGE_MARK):
            drawn = sum(len(text) for _, text in row)
            fragments.append(("", " " * (logo_width - drawn + MARK_GUTTER)))
            fragments.extend(STORAGE_MARK[index])
        fragments.append(("", "\n"))
    if not show_mark:
        return fragments, logo_width
    return fragments, logo_width + MARK_GUTTER + STORAGE_MARK_WIDTH


def _compact_banner_fragments():
    """Fall back to a plain title when the terminal is too narrow to draw."""
    title = " ".join(WORDMARK_TEXT)
    return [("class:welcome-logo", title + "\n")], len(title)


def terminal_columns():
    """Report the usable terminal width, with a safe default when unknown."""
    return shutil.get_terminal_size(fallback=(80, 24)).columns


def welcome_content(columns=None):
    """Build the styled, platform-aware SANCHAY startup screen."""
    report_folder = str(downloads_directory())
    columns = terminal_columns() if columns is None else columns
    if columns >= wordmark_width():
        banner, banner_width = _banner_fragments(columns)
    else:
        banner, banner_width = _compact_banner_fragments()
    body = (
        "Scans local storage, confirms duplicates, and identifies recoverable space.",
        "Protects unique files and creates an auditable HTML report.",
    )
    notes = (
        "Review before action",
        "Unique files stay protected; file actions are disabled by default",
        "Local by default; scanned paths and contents are not uploaded",
    )
    rule_width = min(
        max(banner_width, max(len(line) for line in body) + 2),
        max(columns - 1, 20),
    )
    fragments = list(banner)
    fragments.extend((
        ("", "\n"),
        ("class:welcome-title", "Welcome to SANCHAY"),
        ("class:welcome-muted",
         "   LOCAL SCAN · EVIDENCE-FIRST · GUARDED ACTIONS\n"),
        ("class:welcome-rule", "─" * rule_width + "\n\n"),
        ("class:welcome-heading", "What SANCHAY does\n"),
    ))
    for line in body:
        fragments.append(("class:welcome-text", "  " + line + "\n"))
    fragments.extend((
        ("", "\n"),
        ("class:welcome-heading", "Safety notes\n"),
    ))
    for index, note in enumerate(notes, start=1):
        fragments.append(("class:welcome-number", "  {0}  ".format(index)))
        fragments.append(("class:welcome-text", note + "\n"))
    fragments.extend((
        ("", "\n"),
        ("class:welcome-heading", "Reports   "),
        ("class:welcome-text", report_folder + "\n"),
        ("class:welcome-muted",
         "Type / for commands or /about for details.\n\n"),
    ))
    return FormattedText(fragments)


def show_welcome_screen():
    """Render the interactive splash and wait for acknowledgement."""
    clear()
    print_formatted_text(welcome_content(), style=PALETTE_STYLE)
    try:
        prompt(
            [("class:welcome-continue", CONTINUE_PROMPT)],
            style=PALETTE_STYLE,
        )
    except (EOFError, KeyboardInterrupt):
        return False
    return True


def palette_key_bindings():
    bindings = KeyBindings()

    @bindings.add("enter", eager=True)
    def accept_completion_or_line(event):
        """First Enter accepts the blue choice; the next executes the line."""
        buffer = event.current_buffer
        state = buffer.complete_state
        if state and state.completions:
            selected = state.current_completion or state.completions[0]
            buffer.apply_completion(selected)
            if selected.text in ARGUMENT_COMMANDS:
                buffer.insert_text(" ")
        elif (buffer.cursor_position == len(buffer.text)
              and buffer.text in ARGUMENT_COMMANDS):
            # Some terminals close the completion state as soon as an arrow
            # previews a full command. Preserve the first-Enter-to-insert
            # behavior even when that happens.
            buffer.insert_text(" ")
        else:
            buffer.validate_and_handle()

    return bindings


def can_use_palette(shell):
    """Keep redirected/scripted sessions on cmd.Cmd's plain input loop."""
    return (
        shell.use_rawinput
        and shell.stdin is sys.stdin
        and shell.stdout is sys.stdout
        and getattr(sys.stdin, "isatty", lambda: False)()
        and getattr(sys.stdout, "isatty", lambda: False)()
    )


def run_palette_loop(shell, intro=None):
    """Run a cmd.Cmd-compatible loop with a visible completion menu."""
    shell.preloop()
    stop = None
    intro = shell.intro if intro is None else intro
    if intro:
        if not show_welcome_screen():
            shell.postloop()
            return

    session = PromptSession(
        completer=SlashCommandCompleter(),
        complete_while_typing=True,
        complete_style=CompleteStyle.COLUMN,
        key_bindings=palette_key_bindings(),
        reserve_space_for_menu=12,
    )
    while not stop:
        try:
            line = session.prompt(
                [("class:prompt", shell.prompt)],
                style=PALETTE_STYLE,
                bottom_toolbar=lambda: shell.background_tasks.status_line(),
            )
        except EOFError:
            line = "EOF"
        except KeyboardInterrupt:
            shell._write("^C")
            continue
        line = shell.precmd(line)
        stop = shell.onecmd(line)
        stop = shell.postcmd(stop, line)
    shell.postloop()
