import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
from datetime import date, datetime, timedelta
import pytest
from database.connection import init_db
from services import (auth_service as auth, employee_service as es, leave_service as ls,
                      task_service as ts, email_service as mail, meeting_service as ms,
                      notification_service as ns, analytics_service as an, ai_service as ai)
from utils.errors import ServiceError

ctx = {}


def setup_module():
    init_db()
    auth.create_user("boss", "boss@example.com", "Strong123", "ADMIN")
    ctx["admin"] = auth.authenticate("boss", "Strong123")
    es.create_department(ctx["admin"], "Engineering")
    dept = es.list_departments()[0]["id"]
    es.create_employee(ctx["admin"], "Asha", "Rao", "9876543210", dept, "Developer", date.today(),
                       {"username": "asha", "email": "asha@example.com", "password": "Strong123", "role": "EMPLOYEE"})
    ctx["emp"] = auth.authenticate("asha", "Strong123")
    ctx["eid"] = es.get_employee_id(ctx["emp"]["id"])


def test_employee_code_and_permissions():
    assert es.list_employees()[0]["code"] == "EMP0001"
    with pytest.raises(ServiceError):
        es.create_department(ctx["emp"], "Hacking")


def test_leave_flow():
    start = date.today() + timedelta(days=5)
    ls.apply_leave(ctx["emp"], ctx["eid"], "Casual", start, start + timedelta(days=1), "Family")
    with pytest.raises(ServiceError):  # overlap
        ls.apply_leave(ctx["emp"], ctx["eid"], "Casual", start, start, "Again")
    lid = ls.list_leaves(ctx["admin"], "Pending")[0]["id"]
    with pytest.raises(ServiceError):  # employee cannot approve
        ls.review_leave(ctx["emp"], lid, True)
    ls.review_leave(ctx["admin"], lid, True, "ok")
    casual = next(b for b in ls.get_balances(ctx["eid"]) if b["type"] == "Casual")
    assert casual["remaining"] == 10


def test_tasks_overdue_and_scope():
    ts.create_task(ctx["admin"], "Old task", "", ctx["eid"], "High", datetime.now() - timedelta(days=1))
    ts.create_task(ctx["admin"], "Unassigned", "", None, "Low", None)
    mine = ts.list_tasks(ctx["emp"])
    assert [t["title"] for t in mine] == ["Old task"] and mine[0]["status"] == "Overdue"
    assert an.get_dashboard_stats()["overdue_tasks"] == 1
    ts.update_status(ctx["emp"], mine[0]["id"], "Completed")
    assert an.get_dashboard_stats(ctx["eid"])["completed_tasks"] == 1


def test_email_urgency_and_reply():
    cid = mail.add_client(ctx["admin"], "Acme", "Acme Ltd", "c@acme.com", "")
    eid = mail.log_email(ctx["admin"], cid, "URGENT: payment issue", "Please respond asap")
    assert mail.get_email(eid)["urgency"] == "Urgent"
    assert mail.send_reply(ctx["admin"], eid, "Re: URGENT", "We are on it") is False
    assert mail.get_email(eid)["status"] == "Answered"


def test_meetings_notifications_ai_fallback():
    start = datetime.now() + timedelta(hours=3)
    ms.create_meeting(ctx["admin"], "Sync", "Agenda", start, start + timedelta(hours=1), [ctx["eid"]])
    assert len(ms.list_meetings(ctx["emp"])) == 1
    assert ns.unread_count(ctx["emp"]["id"]) >= 1
    text, used = ai.ask(ctx["admin"], "summary")
    assert used is False and "Daily summary" in text
