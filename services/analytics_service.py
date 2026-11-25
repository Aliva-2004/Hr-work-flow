"""Module 8: dashboard numbers and chart data, computed from the real database."""
from datetime import datetime, date
import pandas as pd
from sqlalchemy import select, func
from database.connection import get_session
from database.models import (Employee, Task, LeaveApplication, Meeting, MeetingParticipant,
                             Email, Attendance)
from services.task_service import refresh_overdue


def get_dashboard_stats(employee_id: int | None = None) -> dict:
    """employee_id=None -> organisation-wide; otherwise only that employee's own data."""
    refresh_overdue()
    now = datetime.now()
    with get_session() as s:
        def tcount(*conds):
            stmt = select(func.count(Task.id))
            for c in conds:
                stmt = stmt.where(c)
            if employee_id:
                stmt = stmt.where(Task.assigned_to == employee_id)
            return s.scalar(stmt) or 0

        lstmt = select(func.count(LeaveApplication.id)).where(LeaveApplication.status == "Pending")
        mstmt = select(func.count(Meeting.id)).where(Meeting.start_time >= now)
        sstmt = select(Task.status, func.count(Task.id)).group_by(Task.status)
        pstmt = select(Task.priority, func.count(Task.id)).where(Task.status != "Completed").group_by(Task.priority)
        if employee_id:
            lstmt = lstmt.where(LeaveApplication.employee_id == employee_id)
            mstmt = mstmt.join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id) \
                         .where(MeetingParticipant.employee_id == employee_id)
            sstmt = sstmt.where(Task.assigned_to == employee_id)
            pstmt = pstmt.where(Task.assigned_to == employee_id)
        return {
            "employees": s.scalar(select(func.count(Employee.id)).where(Employee.is_active.is_(True))) or 0,
            "pending_tasks": tcount(Task.status.in_(["Pending", "In Progress"])),
            "completed_tasks": tcount(Task.status == "Completed"),
            "overdue_tasks": tcount(Task.status == "Overdue"),
            "pending_leaves": s.scalar(lstmt) or 0,
            "upcoming_meetings": s.scalar(mstmt) or 0,
            "unanswered_emails": s.scalar(select(func.count(Email.id)).where(
                Email.direction == "Inbound", Email.status == "Unanswered")) or 0,
            "present_today": s.scalar(select(func.count(Attendance.id)).where(
                Attendance.date == date.today(), Attendance.status == "Present")) or 0,
            "tasks_by_status": {k: v for k, v in s.execute(sstmt).all()},
            "open_tasks_by_priority": {k: v for k, v in s.execute(pstmt).all()},
        }


def task_trend(freq: str = "W", employee_id: int | None = None) -> pd.DataFrame:
    """Tasks created vs completed per week ('W') or month ('M')."""
    with get_session() as s:
        stmt = select(Task.created_at, Task.completed_at)
        if employee_id:
            stmt = stmt.where(Task.assigned_to == employee_id)
        rows = [(a, b) for a, b in s.execute(stmt).all()]
    if not rows:
        return pd.DataFrame(columns=["Period", "Created", "Completed"])
    df = pd.DataFrame(rows, columns=["created", "completed"])
    created = pd.to_datetime(df["created"]).dt.to_period(freq).value_counts()
    completed = pd.to_datetime(df["completed"].dropna()).dt.to_period(freq).value_counts()
    out = pd.DataFrame({"Created": created, "Completed": completed}).fillna(0).astype(int).sort_index()
    out.index = out.index.astype(str)
    return out.reset_index(names="Period")


def productivity() -> pd.DataFrame:
    """Per-employee assigned / completed / overdue and completion rate."""
    with get_session() as s:
        rows = [(f"{e.first_name} {e.last_name}", st) for e, st in
                s.execute(select(Employee, Task.status).join(Task, Task.assigned_to == Employee.id)).all()]
    if not rows:
        return pd.DataFrame(columns=["Employee", "Assigned", "Completed", "Overdue", "Completion %"])
    df = pd.DataFrame(rows, columns=["Employee", "status"])
    out = df.groupby("Employee").agg(Assigned=("status", "size"),
                                     Completed=("status", lambda x: int((x == "Completed").sum())),
                                     Overdue=("status", lambda x: int((x == "Overdue").sum())))
    out["Completion %"] = (out["Completed"] / out["Assigned"] * 100).round(1)
    return out.reset_index()
