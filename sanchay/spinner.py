"""TTY-only elapsed-time loading indicator for foreground SANCHAY work."""
import threading
import time


FRAMES = ("|", "/", "-", "\\")
SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴",
                  "⠦", "⠧", "⠇", "⠏")
TICKS_PER_SECOND = 8


def animation_tick(now=None):
    """Derive one animation frame number from the clock, not a call count."""
    moment = time.monotonic() if now is None else now
    return int(moment * TICKS_PER_SECOND)


def format_elapsed(seconds):
    """Format a live task age like a compact working indicator."""
    minutes, seconds = divmod(max(0, int(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02}m"
    if minutes:
        return f"{minutes}m {seconds:02}s"
    return f"{seconds}s"


def shimmer_fragments(word, tick, base, mid, glow):
    """Sweep a highlight across a word so live work reads as still moving."""
    period = len(word) + 6
    head = tick % period - 3
    fragments = []
    for index, character in enumerate(word):
        distance = abs(index - head)
        style = glow if distance == 0 else mid if distance == 1 else base
        if fragments and fragments[-1][0] == style:
            fragments[-1] = (style, fragments[-1][1] + character)
        else:
            fragments.append((style, character))
    return fragments


def loading_text(message, frame="|", elapsed_seconds=0):
    return (
        f"[{frame}] Working ({int(elapsed_seconds)}s) | {message} | "
        "Ctrl+C to cancel")


class LoadingIndicator:
    """Animate only on a terminal; redirected output remains deterministic."""

    def __init__(self, stream, message, interval=0.12):
        self.stream = stream
        self.message = message
        self.interval = interval
        self.enabled = bool(getattr(stream, "isatty", lambda: False)())
        self._stop_event = threading.Event()
        self._thread = None
        self._started_at = None
        self._last_width = 0

    def __enter__(self):
        if not self.enabled:
            return self
        self._started_at = time.monotonic()
        self._draw(FRAMES[0])
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        if not self.enabled:
            return False
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval * 3))
        try:
            self.stream.write("\r" + " " * self._last_width + "\r")
            self.stream.flush()
        except (OSError, ValueError):
            pass
        return False

    def _animate(self):
        index = 1
        while not self._stop_event.wait(self.interval):
            self._draw(FRAMES[index % len(FRAMES)])
            index += 1

    def _draw(self, frame):
        elapsed = time.monotonic() - self._started_at
        line = loading_text(self.message, frame, elapsed)
        self._last_width = max(self._last_width, len(line))
        try:
            self.stream.write("\r" + line)
            self.stream.flush()
        except (OSError, ValueError):
            self._stop_event.set()
