"""Small in-process registry for long-lived SANCHAY background tasks."""
from dataclasses import dataclass
import time


@dataclass(frozen=True)
class BackgroundTask:
    id: int
    kind: str
    description: str
    started_at: float
    stop_callback: object
    alive_callback: object

    @property
    def elapsed_seconds(self):
        return max(0, int(time.monotonic() - self.started_at))


class BackgroundTasks:
    """Track stoppable services without pretending they are OS processes."""

    def __init__(self):
        self._next_id = 1
        self._tasks = {}

    def add(self, kind, description, stop_callback, alive_callback=lambda: True):
        task = BackgroundTask(
            id=self._next_id,
            kind=kind,
            description=description,
            started_at=time.monotonic(),
            stop_callback=stop_callback,
            alive_callback=alive_callback,
        )
        self._next_id += 1
        self._tasks[task.id] = task
        return task

    def active(self):
        for task_id, task in list(self._tasks.items()):
            if not task.alive_callback():
                self._tasks.pop(task_id, None)
        return list(self._tasks.values())

    def stop(self, task_id):
        task = self._tasks.pop(task_id, None)
        if task is None:
            return None
        task.stop_callback()
        return task

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
        count = len(self.active())
        if not count:
            return ""
        noun = "task" if count == 1 else "tasks"
        return (
            f" {count} background {noun} running | /ps to view | "
            "/stop <id> to close ")
