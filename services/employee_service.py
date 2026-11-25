"""Module 1: employee and department management."""
from datetime import date
from sqlalchemy import select, func
from database.connection import get_session
from database.models import Employee, Department, User
from services import auth_service as auth
from services import leave_service
from services.audit_service import log
from utils.errors import ServiceError
from utils.validators import validate_phone, clean_text

MANAGERS = ("ADMIN", "HR_MANAGER")


def _dict(e: Employee) -> dict:
    return {"id": e.id, "code": e.employee_code, "name": e.full_name,
            "first_name": e.first_name, "last_name": e.last_name, "phone": e.phone or "",
            "department_id": e.department_id,
            "department": e.department.name if e.department else "",
            "designation": e.designation or "", "date_of_joining": e.date_of_joining,
            "is_active": e.is_active, "user_id": e.user_id,
            "username": e.user.username if e.user else "",
            "email": e.user.email if e.user else "", "role": e.user.role if e.user else ""}


def get_employee_id(user_id: int) -> int | None:
    with get_session() as s:
        return s.scalar(select(Employee.id).where(Employee.user_id == user_id))


def list_departments() -> list[dict]:
    with get_session() as s:
        return [{"id": d.id, "name": d.name} for d in s.scalars(select(Department).order_by(Department.name))]


def create_department(actor: dict, name: str) -> int:
    auth.assert_role(actor, *MANAGERS)
    name = clean_text(name, 100)
    if not name:
        raise ServiceError("Department name is required.")
    with get_session() as s:
        if s.scalar(select(Department).where(func.lower(Department.name) == name.lower())):
            raise ServiceError("That department already exists.")
        d = Department(name=name)
        s.add(d)
        s.flush()
        log(s, actor["id"], "DEPARTMENT_CREATED", "departments", d.id, name)
        return d.id


def _next_code(s) -> str:
    return f"EMP{(s.scalar(select(func.max(Employee.id))) or 0) + 1:04d}"


def _check_fields(first, last, phone):
    first, last, phone = clean_text(first, 60), clean_text(last, 60), clean_text(phone, 20)
    if not first or not last:
        raise ServiceError("First and last name are required.")
    if phone and not validate_phone(phone):
        raise ServiceError("Phone number looks invalid (7-15 digits, may start with +).")
    return first, last, phone


def create_employee(actor: dict, first_name, last_name, phone, department_id, designation,
                    date_of_joining: date, account: dict | None = None) -> int:
    """account = {"username","email","password","role"} creates a login at the same time."""
    auth.assert_role(actor, *MANAGERS)
    first, last, phone = _check_fields(first_name, last_name, phone)
    user_id = None
    if account:
        if account["role"] == "ADMIN" and actor["role"] != "ADMIN":
            raise ServiceError("Only an Admin can create Admin accounts.")
        user_id = auth.create_user(account["username"], account["email"],
                                   account["password"], account["role"])
    with get_session() as s:
        emp = Employee(employee_code=_next_code(s), user_id=user_id, first_name=first,
                       last_name=last, phone=phone or None, department_id=department_id,
                       designation=clean_text(designation, 100) or None,
                       date_of_joining=date_of_joining)
        s.add(emp)
        s.flush()
        leave_service.ensure_balances(s, emp.id)
        log(s, actor["id"], "EMPLOYEE_CREATED", "employees", emp.id, emp.employee_code)
        return emp.id


def list_employees(include_inactive: bool = False) -> list[dict]:
    with get_session() as s:
        stmt = select(Employee).order_by(Employee.employee_code)
        if not include_inactive:
            stmt = stmt.where(Employee.is_active.is_(True))
        return [_dict(e) for e in s.scalars(stmt)]


def update_employee(actor: dict, employee_id: int, first_name, last_name, phone,
                    department_id, designation, date_of_joining):
    auth.assert_role(actor, *MANAGERS)
    first, last, phone = _check_fields(first_name, last_name, phone)
    with get_session() as s:
        e = s.get(Employee, employee_id)
        if not e:
            raise ServiceError("Employee not found.")
        e.first_name, e.last_name, e.phone = first, last, phone or None
        e.department_id = department_id
        e.designation = clean_text(designation, 100) or None
        e.date_of_joining = date_of_joining
        log(s, actor["id"], "EMPLOYEE_UPDATED", "employees", e.id)


def set_active(actor: dict, employee_id: int, active: bool):
    auth.assert_role(actor, *MANAGERS)
    with get_session() as s:
        e = s.get(Employee, employee_id)
        if not e:
            raise ServiceError("Employee not found.")
        if e.user_id == actor["id"]:
            raise ServiceError("You cannot deactivate your own account.")
        e.is_active = active
        if e.user:
            e.user.is_active = active
        log(s, actor["id"], "EMPLOYEE_ACTIVE_CHANGED", "employees", e.id, f"active={active}")
