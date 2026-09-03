"""TTY-only elapsed-time loading indicator for foreground SANCHAY work."""
import threading
import time


FRAMES = ("|", "/", "-", "\\")


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
