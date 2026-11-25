"""Notifications: create, read, and auto-generate reminders/alerts (Module 7)."""
from datetime import datetime, timedelta, date
from sqlalchemy import select, func, update
from database.connection import get_session
from database.models import (Notification, User, Employee, Task, Meeting, MeetingParticipant,
                             Email, LeaveApplication)


def notify(s, user_id, title, message, category):
    if user_id:
        s.add(Notification(user_id=user_id, title=title[:150], message=message, category=category))


def notify_roles(s, roles, title, message, category):
    ids = list(s.scalars(select(User.id).where(User.role.in_(roles), User.is_active.is_(True))))
    for uid in ids:
        notify(s, uid, title, message, category)


def list_notifications(user_id: int, unread_only: bool = False, limit: int = 100) -> list[dict]:
    with get_session() as s:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        rows = s.scalars(stmt.order_by(Notification.id.desc()).limit(limit))
        return [{"id": n.id, "title": n.title, "message": n.message, "category": n.category,
                 "is_read": n.is_read, "created_at": n.created_at} for n in rows]


def unread_count(user_id: int) -> int:
    with get_session() as s:
        return s.scalar(select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.is_read.is_(False))) or 0


def mark_read(user_id: int, notification_id: int):
    with get_session() as s:
        s.execute(update(Notification).where(Notification.id == notification_id,
                                             Notification.user_id == user_id).values(is_read=True))


def mark_all_read(user_id: int):
    with get_session() as s:
        s.execute(update(Notification).where(Notification.user_id == user_id,
                                             Notification.is_read.is_(False)).values(is_read=True))


def generate_alerts(actor: dict) -> int:
    """Create deadline / overdue / meeting / pending-email alerts (max once per day each)."""
    now = datetime.now()
    day_start = datetime.combine(date.today(), datetime.min.time())
    created = 0
    with get_session() as s:
        def add_once(title, message, category):
            nonlocal created
            exists = s.scalar(select(Notification.id).where(
                Notification.user_id == actor["id"], Notification.title == title,
                Notification.message == message, Notification.created_at >= day_start))
            if not exists:
                notify(s, actor["id"], title, message, category)
                created += 1

        emp = s.scalar(select(Employee).where(Employee.user_id == actor["id"]))
        if emp:
            tasks = s.scalars(select(Task).where(Task.assigned_to == emp.id,
                                                 Task.status != "Completed",
                                                 Task.deadline.is_not(None)))
            for t in tasks:
                if t.deadline < now:
                    add_once("Overdue task", f"'{t.title}' was due {t.deadline:%d %b %Y %H:%M}.", "overdue")
                elif t.deadline <= now + timedelta(hours=24):
                    add_once("Deadline reminder", f"'{t.title}' is due {t.deadline:%d %b %Y %H:%M}.", "task")
            meetings = s.scalars(select(Meeting).join(MeetingParticipant).where(
                MeetingParticipant.employee_id == emp.id, Meeting.start_time >= now,
                Meeting.start_time <= now + timedelta(hours=24)))
            for m in meetings:
                add_once("Meeting reminder", f"'{m.title}' starts {m.start_time:%d %b %Y %H:%M}.", "meeting")

        if actor["role"] in ("ADMIN", "HR_MANAGER"):
            pend = s.scalar(select(func.count(Email.id)).where(
                Email.direction == "Inbound", Email.status == "Unanswered")) or 0
            urgent = s.scalar(select(func.count(Email.id)).where(
                Email.direction == "Inbound", Email.status == "Unanswered",
                Email.urgency.in_(["High", "Urgent"]))) or 0
            if pend:
                add_once("Pending client emails",
                         f"{pend} client email(s) waiting for a reply ({urgent} high/urgent).", "email")
            od = s.scalar(select(func.count(Task.id)).where(
                Task.status != "Completed", Task.deadline < now)) or 0
            if od:
                add_once("Overdue tasks across the organisation", f"{od} task(s) are overdue.", "overdue")
            pl = s.scalar(select(func.count(LeaveApplication.id)).where(
                LeaveApplication.status == "Pending")) or 0
            if pl:
                add_once("Leave applications awaiting review", f"{pl} application(s) need a decision.", "leave")
    return created
