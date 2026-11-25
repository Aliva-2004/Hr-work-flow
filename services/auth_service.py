"""Authentication and role-based access control."""
from datetime import datetime
import bcrypt
from sqlalchemy import select, func
from database.connection import get_session
from database.models import User, AuditLog
from config.settings import ROLES
from utils.validators import validate_email, validate_username, validate_password
from utils.errors import ServiceError
from services.audit_service import log


class AuthError(ServiceError):
    """Raised for any validation/authentication problem; message is safe to show."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def has_users() -> bool:
    with get_session() as s:
        return (s.scalar(select(func.count(User.id))) or 0) > 0


def create_user(username: str, email: str, password: str, role: str = "EMPLOYEE") -> int:
    username, email = username.strip(), email.strip().lower()
    if not validate_username(username):
        raise AuthError("Username must be 3-50 characters: letters, numbers, _ or .")
    if not validate_email(email):
        raise AuthError("Please enter a valid email address.")
    problems = validate_password(password)
    if problems:
        raise AuthError("Password needs: " + ", ".join(problems))
    if role not in ROLES:
        raise AuthError("Invalid role.")
    with get_session() as s:
        exists = s.scalar(select(User).where((User.username == username) | (User.email == email)))
        if exists:
            raise AuthError("Username or email already in use.")
        user = User(username=username, email=email,
                    password_hash=hash_password(password), role=role)
        s.add(user)
        s.flush()
        s.add(AuditLog(user_id=user.id, action="USER_CREATED", entity="users",
                       entity_id=user.id, details=f"role={role}"))
        return user.id


def authenticate(username: str, password: str) -> dict:
    """Return a safe user dict (no password hash) or raise AuthError."""
    with get_session() as s:
        user = s.scalar(select(User).where(User.username == username.strip()))
        # Same message for unknown user / wrong password: don't leak which is wrong.
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            raise AuthError("Invalid username or password.")
        user.last_login = datetime.now()
        s.add(AuditLog(user_id=user.id, action="LOGIN", entity="users", entity_id=user.id))
        return {"id": user.id, "username": user.username, "email": user.email, "role": user.role}


def has_role(user: dict | None, *allowed: str) -> bool:
    return bool(user) and user["role"] in allowed


def assert_role(actor: dict | None, *allowed: str):
    if not has_role(actor, *allowed):
        raise ServiceError("You do not have permission to do this.")


def change_password(user_id: int, old: str, new: str):
    problems = validate_password(new)
    if problems:
        raise AuthError("New password needs: " + ", ".join(problems))
    with get_session() as s:
        u = s.get(User, user_id)
        if not u or not verify_password(old, u.password_hash):
            raise AuthError("Current password is incorrect.")
        u.password_hash = hash_password(new)
        log(s, user_id, "PASSWORD_CHANGED", "users", user_id)


def list_users() -> list[dict]:
    with get_session() as s:
        return [{"id": u.id, "username": u.username, "email": u.email, "role": u.role,
                 "is_active": u.is_active, "last_login": u.last_login}
                for u in s.scalars(select(User).order_by(User.username))]


def set_user_role(actor: dict, user_id: int, role: str):
    assert_role(actor, "ADMIN")
    if role not in ROLES:
        raise AuthError("Invalid role.")
    if user_id == actor["id"]:
        raise AuthError("You cannot change your own role.")
    with get_session() as s:
        u = s.get(User, user_id)
        u.role = role
        log(s, actor["id"], "ROLE_CHANGED", "users", user_id, f"role={role}")


def set_user_active(actor: dict, user_id: int, active: bool):
    assert_role(actor, "ADMIN")
    if user_id == actor["id"]:
        raise AuthError("You cannot deactivate your own account.")
    with get_session() as s:
        u = s.get(User, user_id)
        u.is_active = active
        log(s, actor["id"], "USER_ACTIVE_CHANGED", "users", user_id, f"active={active}")


def admin_reset_password(actor: dict, user_id: int, new_password: str):
    assert_role(actor, "ADMIN")
    problems = validate_password(new_password)
    if problems:
        raise AuthError("Password needs: " + ", ".join(problems))
    with get_session() as s:
        s.get(User, user_id).password_hash = hash_password(new_password)
        log(s, actor["id"], "PASSWORD_RESET", "users", user_id)
