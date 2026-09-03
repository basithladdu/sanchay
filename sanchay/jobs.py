"""Small in-process registry for long-lived SANCHAY background tasks."""
from dataclasses import dataclass
import threading
import time


@dataclass(frozen=True)
class BackgroundTask:
    id: int
    kind: str
    description: str
    started_at: float
    stop_callback: object
    alive_callback: object
    status_callback: object
    details_callback: object
    cancellable: bool

    @property
    def elapsed_seconds(self):
        return max(0, int(time.monotonic() - self.started_at))

    @property
    def status(self):
        return str(self.status_callback())

    @property
    def details(self):
        return str(self.details_callback())


class BackgroundTasks:
    """Track stoppable services without pretending they are OS processes."""

    def __init__(self):
        self._next_id = 1
        self._tasks = {}
        self._lock = threading.RLock()

    def add(self, kind, description, stop_callback, alive_callback=lambda: True,
            status_callback=lambda: "running", details_callback=None,
            cancellable=False):
        with self._lock:
            task = BackgroundTask(
                id=self._next_id,
                kind=kind,
                description=description,
                started_at=time.monotonic(),
                stop_callback=stop_callback,
                alive_callback=alive_callback,
                status_callback=status_callback,
                details_callback=(details_callback or (lambda: description)),
                cancellable=bool(cancellable),
            )
            self._next_id += 1
            self._tasks[task.id] = task
        return task

    def active(self):
        with self._lock:
            for task_id, task in list(self._tasks.items()):
                if not task.alive_callback():
                    self._tasks.pop(task_id, None)
            return list(self._tasks.values())

    def stop(self, task_id):
        with self._lock:
            task = self._tasks.get(task_id)
        if task is None:
            return None
        task.stop_callback()
        with self._lock:
            if not task.cancellable or not task.alive_callback():
                self._tasks.pop(task_id, None)
        return task

    def latest_cancellable(self):
        candidates = [task for task in self.active() if task.cancellable]
        return max(candidates, key=lambda task: task.id) if candidates else None

    def stop_kind(self, kind):
        stopped = []
        for task in list(self.active()):
            if task.kind == kind:
                stopped_task = self.stop(task.id)
                if stopped_task is not None:
                    stopped.append(stopped_task)
        return stopped

    def stop_all(self):
        stopped = []
        for task in list(self.active()):
            stopped_task = self.stop(task.id)
            if stopped_task is not None:
                stopped.append(stopped_task)
        return stopped

    def status_line(self):
        tasks = self.active()
        count = len(tasks)
        if not count:
            return ""
        noun = "task" if count == 1 else "tasks"
        interrupt = (
            " | Esc to interrupt latest work"
            if any(task.cancellable and task.status != "finishing"
                   for task in tasks) else ""
        )
        return f" {count} background {noun} running | /ps to view{interrupt} "
