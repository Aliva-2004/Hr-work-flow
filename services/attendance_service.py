"""Attendance tracking (check in/out for employees, corrections for HR)."""
from datetime import date, datetime
from sqlalchemy import select
from database.connection import get_session
from database.models import Attendance, Employee
from services import auth_service as auth
from services.audit_service import log
from utils.errors import ServiceError
from config.settings import ATTENDANCE_STATUSES


def _my_employee(s, actor):
    emp = s.scalar(select(Employee).where(Employee.user_id == actor["id"]))
    if not emp:
        raise ServiceError("You have no employee profile, so attendance cannot be recorded.")
    return emp


def check_in(actor: dict):
    with get_session() as s:
        emp = _my_employee(s, actor)
        if s.scalar(select(Attendance.id).where(Attendance.employee_id == emp.id,
                                                Attendance.date == date.today())):
            raise ServiceError("You already checked in today.")
        s.add(Attendance(employee_id=emp.id, date=date.today(), check_in=datetime.now(), status="Present"))


def check_out(actor: dict):
    with get_session() as s:
        emp = _my_employee(s, actor)
        rec = s.scalar(select(Attendance).where(Attendance.employee_id == emp.id,
                                                Attendance.date == date.today()))
        if not rec or rec.check_in is None:
            raise ServiceError("Check in first.")
        if rec.check_out:
            raise ServiceError("You already checked out today.")
        rec.check_out = datetime.now()


def today_status(actor: dict) -> dict | None:
    with get_session() as s:
        emp = s.scalar(select(Employee).where(Employee.user_id == actor["id"]))
        if not emp:
            return None
        rec = s.scalar(select(Attendance).where(Attendance.employee_id == emp.id,
                                                Attendance.date == date.today()))
        return {"check_in": rec.check_in, "check_out": rec.check_out} if rec else {"check_in": None, "check_out": None}


def list_attendance(actor: dict, month_start: date | None = None) -> list[dict]:
    with get_session() as s:
        stmt = select(Attendance, Employee).join(Employee, Employee.id == Attendance.employee_id)
        if actor["role"] not in ("ADMIN", "HR_MANAGER"):
            stmt = stmt.where(Employee.user_id == actor["id"])
        if month_start:
            stmt = stmt.where(Attendance.date >= month_start)
        rows = s.execute(stmt.order_by(Attendance.date.desc(), Employee.employee_code).limit(500)).all()
        return [{"date": a.date, "employee": e.full_name, "code": e.employee_code,
                 "check_in": a.check_in, "check_out": a.check_out, "status": a.status} for a, e in rows]


def mark_attendance(actor: dict, employee_id: int, day: date, status: str):
    auth.assert_role(actor, "ADMIN", "HR_MANAGER")
    if status not in ATTENDANCE_STATUSES:
        raise ServiceError("Invalid status.")
    with get_session() as s:
        rec = s.scalar(select(Attendance).where(Attendance.employee_id == employee_id, Attendance.date == day))
        if rec:
            rec.status = status
        else:
            s.add(Attendance(employee_id=employee_id, date=day, status=status))
        log(s, actor["id"], "ATTENDANCE_MARKED", "attendance", employee_id, f"{day} {status}")
