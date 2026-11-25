"""Module 4: clients, email records, urgency, replies, follow-ups (SMTP optional)."""
import smtplib
from datetime import datetime
from email.message import EmailMessage
from sqlalchemy import select
from database.connection import get_session
from database.models import Client, Email
from services import auth_service as auth
from services.audit_service import log
from utils.errors import ServiceError
from utils.validators import validate_email, validate_phone, clean_text
from config import settings

MANAGERS = ("ADMIN", "HR_MANAGER")
_URGENT = ("urgent", "asap", "immediately", "escalat", "complaint", "legal", "unacceptable", "emergency")
_HIGH = ("deadline", "payment", "invoice", "issue", "problem", "delay", "today", "tomorrow", "overdue", "reminder")
_ORDER = {"Urgent": 0, "High": 1, "Normal": 2, "Low": 3}


def classify_urgency(subject: str, body: str) -> str:
    text = f"{subject} {body}".lower()
    if any(k in text for k in _URGENT):
        return "Urgent"
    if any(k in text for k in _HIGH):
        return "High"
    return "Normal"


def smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def _smtp_send(to: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = " ".join(subject.split())  # no newlines => no header injection
    msg.set_content(body)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as srv:
        srv.starttls()
        srv.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        srv.send_message(msg)


def list_clients() -> list[dict]:
    with get_session() as s:
        return [{"id": c.id, "name": c.name, "company": c.company or "", "email": c.email,
                 "phone": c.phone or ""} for c in s.scalars(select(Client).order_by(Client.name))]


def add_client(actor: dict, name, company, email, phone) -> int:
    auth.assert_role(actor, *MANAGERS)
    name, email = clean_text(name, 120), clean_text(email, 120).lower()
    phone = clean_text(phone, 20)
    if not name:
        raise ServiceError("Client name is required.")
    if not validate_email(email):
        raise ServiceError("Enter a valid client email.")
    if phone and not validate_phone(phone):
        raise ServiceError("Phone number looks invalid.")
    with get_session() as s:
        if s.scalar(select(Client.id).where(Client.email == email)):
            raise ServiceError("A client with this email already exists.")
        c = Client(name=name, company=clean_text(company, 120) or None, email=email, phone=phone or None)
        s.add(c)
        s.flush()
        log(s, actor["id"], "CLIENT_ADDED", "clients", c.id)
        return c.id


def _dict(e: Email, c: Client) -> dict:
    return {"id": e.id, "client_id": c.id, "client": c.name, "client_email": c.email,
            "subject": e.subject, "body": e.body, "direction": e.direction, "urgency": e.urgency,
            "status": e.status, "received_at": e.received_at, "replied_at": e.replied_at,
            "ai_draft": e.ai_draft or ""}


def log_email(actor: dict, client_id: int, subject, body, direction="Inbound", received_at=None) -> int:
    auth.assert_role(actor, *MANAGERS)
    subject, body = clean_text(subject, 250), clean_text(body, 10000)
    if not subject or not body:
        raise ServiceError("Subject and message are required.")
    if direction not in ("Inbound", "Outbound"):
        raise ServiceError("Invalid direction.")
    with get_session() as s:
        if not s.get(Client, client_id):
            raise ServiceError("Select a client first.")
        e = Email(client_id=client_id, subject=subject, body=body, direction=direction,
                  urgency=classify_urgency(subject, body) if direction == "Inbound" else "Normal",
                  status="Unanswered" if direction == "Inbound" else "Answered",
                  received_at=received_at or datetime.now(), handled_by=actor["id"])
        s.add(e)
        s.flush()
        log(s, actor["id"], "EMAIL_LOGGED", "emails", e.id)
        return e.id


def list_emails(status=None, client_id=None, urgency=None) -> list[dict]:
    with get_session() as s:
        stmt = select(Email, Client).join(Client, Client.id == Email.client_id)
        if status:
            stmt = stmt.where(Email.status == status)
        if client_id:
            stmt = stmt.where(Email.client_id == client_id)
        if urgency:
            stmt = stmt.where(Email.urgency == urgency)
        out = [_dict(e, c) for e, c in s.execute(stmt).all()]
    out.sort(key=lambda d: (_ORDER.get(d["urgency"], 9), d["received_at"]))
    return out


def get_email(email_id: int) -> dict | None:
    with get_session() as s:
        row = s.execute(select(Email, Client).join(Client, Client.id == Email.client_id)
                        .where(Email.id == email_id)).first()
        return _dict(*row) if row else None


def save_draft(email_id: int, draft: str):
    with get_session() as s:
        e = s.get(Email, email_id)
        if e:
            e.ai_draft = clean_text(draft, 10000)


def set_followup(actor: dict, email_id: int):
    auth.assert_role(actor, *MANAGERS)
    with get_session() as s:
        e = s.get(Email, email_id)
        if not e:
            raise ServiceError("Email not found.")
        e.status = "Follow-up"
        log(s, actor["id"], "EMAIL_FOLLOWUP", "emails", e.id)


def send_reply(actor: dict, email_id: int, subject: str, body: str, use_smtp: bool = False) -> bool:
    """Record the reply, mark the original answered. Returns True if actually emailed."""
    auth.assert_role(actor, *MANAGERS)
    subject, body = clean_text(subject, 250), clean_text(body, 10000)
    if not subject or not body:
        raise ServiceError("Reply subject and body are required.")
    sent = False
    with get_session() as s:
        orig = s.get(Email, email_id)
        if not orig:
            raise ServiceError("Email not found.")
        client = s.get(Client, orig.client_id)
        if use_smtp:
            if not smtp_configured():
                raise ServiceError("SMTP is not configured in .env, so the email cannot be sent.")
            try:
                _smtp_send(client.email, subject, body)
                sent = True
            except Exception as exc:  # network/auth errors
                raise ServiceError(f"Could not send the email: {exc}")
        now = datetime.now()
        s.add(Email(client_id=client.id, subject=subject, body=body, direction="Outbound",
                    urgency="Normal", status="Answered", received_at=now, replied_at=now,
                    handled_by=actor["id"]))
        orig.status, orig.replied_at = "Answered", now
        log(s, actor["id"], "EMAIL_REPLIED", "emails", orig.id, "sent" if sent else "recorded only")
    return sent
