"""Audit trail: who did what, when."""
from sqlalchemy import select
from database.connection import get_session
from database.models import AuditLog, User


def log(session, user_id, action, entity=None, entity_id=None, details=None):
    """Add an audit row inside the caller's session (committed with the caller's work)."""
    session.add(AuditLog(user_id=user_id, action=action, entity=entity,
                         entity_id=entity_id, details=details))


def list_logs(limit: int = 300) -> list[dict]:
    with get_session() as s:
        rows = s.execute(select(AuditLog, User.username)
                         .outerjoin(User, User.id == AuditLog.user_id)
                         .order_by(AuditLog.id.desc()).limit(limit)).all()
        return [{"time": a.created_at, "user": u or "-", "action": a.action,
                 "entity": a.entity or "", "entity_id": a.entity_id, "details": a.details or ""}
                for a, u in rows]
