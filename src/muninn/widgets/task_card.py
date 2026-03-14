from __future__ import annotations

from textual.widgets import Static

from muninn.models.task import Task


class TaskCard(Static):
    """Display widget for a single task."""

    DEFAULT_CSS = """
    TaskCard {
        margin: 0 1;
        padding: 0 1;
        border: double $accent;
        width: 1fr;
    }
    """

    def __init__(self, task: Task) -> None:
        self._task_data = task
        content = self._format_task(task)
        super().__init__(content, markup=True)

    @staticmethod
    def _format_task(task: Task) -> str:
        lines = [
            f"[bold cyan]Task #{task.id}[/] — {task.subject}",
            f"  Status: {task.status} | Assigned by: {task.assigned_by}",
        ]
        if task.description:
            desc = task.description[:200] + "…" if len(task.description) > 200 else task.description
            lines.append(f"  {desc}")
        return "\n".join(lines)
