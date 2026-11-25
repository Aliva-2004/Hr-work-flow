"""Module 5: meetings, participants, notes, reminders."""
from datetime import datetime
from sqlalchemy import select
from database.connection import get_session
from database.models import Meeting, MeetingParticipant, Employee
from services import auth_service as auth
from services.audit_service import log
from services.notification_service import notify
from utils.errors import ServiceError
from utils.validators import clean_text

MANAGERS = ("ADMIN", "HR_MANAGER")


def create_meeting(actor: dict, title, agenda, start: datetime, end: datetime | None, participant_ids: list[int]) -> int:
    auth.assert_role(actor, *MANAGERS)
    title = clean_text(title, 200)
    if not title:
        raise ServiceError("Meeting title is required.")
    if end and end <= start:
        raise ServiceError("End time must be after the start time.")
    with get_session() as s:
        m = Meeting(title=title, agenda=clean_text(agenda, 3000) or None, start_time=start,
                    end_time=end, created_by=actor["id"])
        s.add(m)
        s.flush()
        for eid in dict.fromkeys(participant_ids):
            s.add(MeetingParticipant(meeting_id=m.id, employee_id=eid))
            emp = s.get(Employee, eid)
            if emp:
                notify(s, emp.user_id, "Meeting scheduled", f"'{title}' on {start:%d %b %Y %H:%M}.", "meeting")
        log(s, actor["id"], "MEETING_CREATED", "meetings", m.id)
        return m.id


def list_meetings(actor: dict, upcoming_only: bool = True) -> list[dict]:
    now = datetime.now()
    with get_session() as s:
        stmt = select(Meeting)
        if actor["role"] not in MANAGERS:
            stmt = stmt.join(MeetingParticipant).join(Employee, Employee.id == MeetingParticipant.employee_id) \
                       .where(Employee.user_id == actor["id"])
        stmt = stmt.where(Meeting.start_time >= now) if upcoming_only else stmt.where(Meeting.start_time < now)
        stmt = stmt.order_by(Meeting.start_time if upcoming_only else Meeting.start_time.desc())
        out = []
        for m in s.scalars(stmt):
            names = [s.get(Employee, p.employee_id).full_name for p in m.participants]
            out.append({"id": m.id, "title": m.title, "agenda": m.agenda or "", "start": m.start_time,
                        "end": m.end_time, "notes": m.notes or "", "participants": names})
        return out


def save_notes(actor: dict, meeting_id: int, notes: str):
    auth.assert_role(actor, *MANAGERS)
    with get_session() as s:
        m = s.get(Meeting, meeting_id)
        if not m:
            raise ServiceError("Meeting not found.")
        m.notes = clean_text(notes, 5000) or None
        log(s, actor["id"], "MEETING_NOTES", "meetings", m.id)
