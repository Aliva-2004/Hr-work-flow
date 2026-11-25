"""Module 3: tasks, priorities, deadlines, overdue detection."""
from datetime import datetime
from sqlalchemy import select, update
from database.connection import get_session
from database.models import Task, Employee
from services import auth_service as auth
from services.audit_service import log
from services.notification_service import notify
from utils.errors import ServiceError
from utils.validators import clean_text
from config.settings import TASK_PRIORITIES, TASK_STATUSES

MANAGERS = ("ADMIN", "HR_MANAGER")
_PRIO = {p: i for i, p in enumerate(reversed(TASK_PRIORITIES))}  # Critical = 0


def refresh_overdue() -> int:
    """Mark unfinished tasks whose deadline has passed as Overdue."""
    with get_session() as s:
        res = s.execute(update(Task).where(
            Task.deadline.is_not(None), Task.deadline < datetime.now(),
            Task.status.in_(["Pending", "In Progress"])).values(status="Overdue"))
        return res.rowcount or 0


def create_task(actor: dict, title, description, assigned_to: int | None, priority, deadline: datetime | None) -> int:
    auth.assert_role(actor, *MANAGERS)
    title = clean_text(title, 200)
    if not title:
        raise ServiceError("Task title is required.")
    if priority not in TASK_PRIORITIES:
        raise ServiceError("Invalid priority.")
    with get_session() as s:
        t = Task(title=title, description=clean_text(description, 2000) or None,
                 assigned_to=assigned_to, created_by=actor["id"], priority=priority, deadline=deadline)
        s.add(t)
        s.flush()
        if assigned_to:
            emp = s.get(Employee, assigned_to)
            when = f" Deadline: {deadline:%d %b %Y %H:%M}." if deadline else ""
            notify(s, emp.user_id, "New task assigned", f"'{title}' ({priority} priority).{when}", "task")
        log(s, actor["id"], "TASK_CREATED", "tasks", t.id)
        return t.id


def list_tasks(actor: dict, status=None, priority=None, employee_id=None) -> list[dict]:
    refresh_overdue()
    with get_session() as s:
        stmt = select(Task, Employee).outerjoin(Employee, Employee.id == Task.assigned_to)
        if actor["role"] not in MANAGERS:
            stmt = stmt.where(Employee.user_id == actor["id"])
        elif employee_id:
            stmt = stmt.where(Task.assigned_to == employee_id)
        if status:
            stmt = stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
        rows = s.execute(stmt).all()
        out = [{"id": t.id, "title": t.title, "description": t.description or "",
                "assignee": e.full_name if e else "Unassigned", "assigned_to": t.assigned_to,
                "priority": t.priority, "status": t.status, "deadline": t.deadline,
                "created_at": t.created_at, "completed_at": t.completed_at} for t, e in rows]
    out.sort(key=lambda d: (d["status"] == "Completed", _PRIO.get(d["priority"], 9),
                            d["deadline"] or datetime.max))
    return out


def update_status(actor: dict, task_id: int, status: str):
    if status not in TASK_STATUSES or status == "Overdue":
        raise ServiceError("Choose Pending, In Progress or Completed.")
    with get_session() as s:
        t = s.get(Task, task_id)
        if not t:
            raise ServiceError("Task not found.")
        emp = s.get(Employee, t.assigned_to) if t.assigned_to else None
        if actor["role"] not in MANAGERS and not (emp and emp.user_id == actor["id"]):
            raise ServiceError("You can only update your own tasks.")
        t.status = status
        t.completed_at = datetime.now() if status == "Completed" else None
        log(s, actor["id"], "TASK_STATUS", "tasks", t.id, status)
