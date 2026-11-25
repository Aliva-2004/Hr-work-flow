"""Leave management + attendance."""
from datetime import date, datetime
import pandas as pd
import streamlit as st
from services import leave_service as ls, attendance_service as att, employee_service as es
from services.auth_service import has_role
from utils.errors import ServiceError
from utils.ui import show_df, flash, fmt_dt
from config.settings import LEAVE_TYPES, ATTENDANCE_STATUSES


def render(user: dict):
    st.title("Leave Management")
    manager = has_role(user, "ADMIN", "HR_MANAGER")
    eid = es.get_employee_id(user["id"])
    names = []
    if eid:
        names += ["Apply for leave", "My balance"]
    names += ["Leave history"]
    if manager:
        names += ["Approvals"]
    names += ["Attendance"]
    tabs = dict(zip(names, st.tabs(names)))
    if eid:
        with tabs["Apply for leave"]:
            _apply(user, eid)
        with tabs["My balance"]:
            _balance(eid)
    with tabs["Leave history"]:
        _history(user)
    if manager:
        with tabs["Approvals"]:
            _approvals(user)
    with tabs["Attendance"]:
        _attendance(user, manager, eid)


def _apply(user, eid):
    with st.form("apply_leave", clear_on_submit=True):
        a, b, c = st.columns(3)
        ltype = a.selectbox("Leave type", LEAVE_TYPES)
        start = b.date_input("From", date.today())
        end = c.date_input("To", date.today())
        reason = st.text_area("Reason")
        if st.form_submit_button("Submit application"):
            try:
                ls.apply_leave(user, eid, ltype, start, end, reason)
                flash("Leave application submitted")
                st.rerun()
            except ServiceError as err:
                st.error(str(err))


def _balance(eid):
    bal = ls.get_balances(eid)
    cols = st.columns(len(bal))
    for col, b in zip(cols, bal):
        if b["type"] == "Unpaid":
            col.metric("Unpaid", f"{b['used']:g} taken")
        else:
            col.metric(b["type"], f"{b['remaining']:g} left", f"of {b['total']:g}", delta_color="off")


def _history(user):
    rows = ls.list_leaves(user)
    if not rows:
        st.info("No leave applications yet.")
        return
    df = pd.DataFrame(rows)[["employee", "type", "start", "end", "days", "status", "reason", "review_note"]]
    df.columns = ["Employee", "Type", "From", "To", "Days", "Status", "Reason", "HR note"]
    show_df(df)


def _approvals(user):
    pending = ls.list_leaves(user, status="Pending")
    if not pending:
        st.success("No applications waiting for review.")
        return
    for l in pending:
        with st.expander(f"{l['employee']} · {l['type']} · {l['start']:%d %b} – {l['end']:%d %b} ({l['days']:g} days)"):
            st.write(l["reason"])
            note = st.text_input("Note (optional)", key=f"note_{l['id']}")
            a, b, _ = st.columns([1, 1, 4])
            for col, label, ok in ((a, "Approve", True), (b, "Reject", False)):
                if col.button(label, key=f"{label}_{l['id']}"):
                    try:
                        ls.review_leave(user, l["id"], ok, note)
                        flash(f"Application {label.lower()}d")
                        st.rerun()
                    except ServiceError as err:
                        st.error(str(err))


def _attendance(user, manager, eid):
    if eid:
        status = att.today_status(user)
        c1, c2, c3 = st.columns([1, 1, 3])
        if c1.button("Check in", disabled=bool(status and status["check_in"])):
            try:
                att.check_in(user); flash("Checked in"); st.rerun()
            except ServiceError as err:
                st.error(str(err))
        if c2.button("Check out", disabled=not (status and status["check_in"]) or bool(status and status["check_out"])):
            try:
                att.check_out(user); flash("Checked out"); st.rerun()
            except ServiceError as err:
                st.error(str(err))
        if status and status["check_in"]:
            c3.caption(f"Today: in {status['check_in']:%H:%M}" +
                       (f" · out {status['check_out']:%H:%M}" if status["check_out"] else ""))
    rows = att.list_attendance(user, date.today().replace(day=1))
    if rows:
        df = pd.DataFrame(rows)
        df["check_in"] = df["check_in"].apply(lambda v: f"{v:%H:%M}" if v else "")
        df["check_out"] = df["check_out"].apply(lambda v: f"{v:%H:%M}" if v else "")
        df.columns = ["Date", "Employee", "ID", "In", "Out", "Status"]
        show_df(df)
    else:
        st.info("No attendance records this month.")
    if manager:
        st.subheader("Mark / correct attendance")
        emps = es.list_employees()
        if emps:
            with st.form("mark_att"):
                labels = {f"{e['code']} · {e['name']}": e["id"] for e in emps}
                who = st.selectbox("Employee", list(labels))
                day = st.date_input("Date", date.today())
                status = st.selectbox("Status", ATTENDANCE_STATUSES)
                if st.form_submit_button("Save"):
                    try:
                        att.mark_attendance(user, labels[who], day, status)
                        flash("Attendance saved"); st.rerun()
                    except ServiceError as err:
                        st.error(str(err))
