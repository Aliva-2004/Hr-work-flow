"""Module 2: leave applications, balances, approvals."""
from datetime import date
from sqlalchemy import select
from database.connection import get_session
from database.models import LeaveApplication, LeaveBalance, Employee
from services import auth_service as auth
from services.audit_service import log
from services.notification_service import notify, notify_roles
from utils.errors import ServiceError
from utils.validators import clean_text
from config.settings import LEAVE_ALLOTMENT, LEAVE_TYPES

MANAGERS = ("ADMIN", "HR_MANAGER")


def ensure_balances(s, employee_id: int, year: int | None = None):
    year = year or date.today().year
    have = set(s.scalars(select(LeaveBalance.leave_type).where(
        LeaveBalance.employee_id == employee_id, LeaveBalance.year == year)))
    for leave_type, days in LEAVE_ALLOTMENT.items():
        if leave_type not in have:
            s.add(LeaveBalance(employee_id=employee_id, leave_type=leave_type, year=year,
                               total_days=days, used_days=0))
    s.flush()


def get_balances(employee_id: int, year: int | None = None) -> list[dict]:
    year = year or date.today().year
    with get_session() as s:
        ensure_balances(s, employee_id, year)
        rows = s.scalars(select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id, LeaveBalance.year == year))
        return [{"type": b.leave_type, "total": b.total_days, "used": b.used_days,
                 "remaining": b.total_days - b.used_days} for b in rows]


def _remaining(s, employee_id, leave_type, year) -> float:
    ensure_balances(s, employee_id, year)
    b = s.scalar(select(LeaveBalance).where(
        LeaveBalance.employee_id == employee_id, LeaveBalance.leave_type == leave_type,
        LeaveBalance.year == year))
    return b.total_days - b.used_days


def apply_leave(actor: dict, employee_id: int, leave_type: str, start: date, end: date, reason: str) -> int:
    reason = clean_text(reason, 1000)
    if leave_type not in LEAVE_TYPES:
        raise ServiceError("Invalid leave type.")
    if end < start:
        raise ServiceError("End date cannot be before start date.")
    if not reason:
        raise ServiceError("Please enter a reason.")
    days = (end - start).days + 1
    with get_session() as s:
        emp = s.get(Employee, employee_id)
        if not emp:
            raise ServiceError("Employee profile not found.")
        if emp.user_id != actor["id"] and actor["role"] not in MANAGERS:
            raise ServiceError("You can only apply for your own leave.")
        clash = s.scalar(select(LeaveApplication.id).where(
            LeaveApplication.employee_id == employee_id,
            LeaveApplication.status.in_(["Pending", "Approved"]),
            LeaveApplication.start_date <= end, LeaveApplication.end_date >= start))
        if clash:
            raise ServiceError("You already have a leave application overlapping these dates.")
        if leave_type != "Unpaid" and _remaining(s, employee_id, leave_type, start.year) < days:
            raise ServiceError(f"Not enough {leave_type} leave balance for {days} day(s).")
        app = LeaveApplication(employee_id=employee_id, leave_type=leave_type, start_date=start,
                               end_date=end, days=days, reason=reason)
        s.add(app)
        s.flush()
        notify_roles(s, MANAGERS, "New leave application",
                     f"{emp.full_name} applied for {days} day(s) of {leave_type} leave "
                     f"({start:%d %b} - {end:%d %b}).", "leave")
        log(s, actor["id"], "LEAVE_APPLIED", "leave_applications", app.id)
        return app.id


def list_leaves(actor: dict, status: str | None = None) -> list[dict]:
    with get_session() as s:
        stmt = select(LeaveApplication, Employee).join(Employee, Employee.id == LeaveApplication.employee_id)
        if actor["role"] not in MANAGERS:
            stmt = stmt.where(Employee.user_id == actor["id"])
        if status:
            stmt = stmt.where(LeaveApplication.status == status)
        rows = s.execute(stmt.order_by(LeaveApplication.id.desc())).all()
        return [{"id": a.id, "employee_id": e.id, "employee": e.full_name, "type": a.leave_type,
                 "start": a.start_date, "end": a.end_date, "days": a.days, "reason": a.reason,
                 "status": a.status, "review_note": a.review_note or "",
                 "created_at": a.created_at} for a, e in rows]


def review_leave(actor: dict, leave_id: int, approve: bool, note: str = ""):
    auth.assert_role(actor, *MANAGERS)
    with get_session() as s:
        app = s.get(LeaveApplication, leave_id)
        if not app or app.status != "Pending":
            raise ServiceError("This application is no longer pending.")
        emp = s.get(Employee, app.employee_id)
        if emp.user_id == actor["id"]:
            raise ServiceError("You cannot review your own leave application.")
        if approve and app.leave_type != "Unpaid":
            if _remaining(s, emp.id, app.leave_type, app.start_date.year) < app.days:
                raise ServiceError("Employee does not have enough balance to approve this.")
            bal = s.scalar(select(LeaveBalance).where(
                LeaveBalance.employee_id == emp.id, LeaveBalance.leave_type == app.leave_type,
                LeaveBalance.year == app.start_date.year))
            bal.used_days += app.days
        app.status = "Approved" if approve else "Rejected"
        app.reviewed_by = actor["id"]
        app.review_note = clean_text(note, 500) or None
        notify(s, emp.user_id, f"Leave {app.status.lower()}",
               f"Your {app.leave_type} leave ({app.start_date:%d %b} - {app.end_date:%d %b}) was "
               f"{app.status.lower()}." + (f" Note: {app.review_note}" if app.review_note else ""), "leave")
        log(s, actor["id"], f"LEAVE_{app.status.upper()}", "leave_applications", app.id)
