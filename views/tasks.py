"""Tasks & deadlines."""
from datetime import datetime, date, time
import pandas as pd
import streamlit as st
from services import task_service as ts, employee_service as es
from services.auth_service import has_role
from utils.errors import ServiceError
from utils.ui import show_df, flash
from config.settings import TASK_PRIORITIES, TASK_STATUSES

_ICON = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}


def render(user: dict):
    st.title("Tasks & Deadlines")
    manager = has_role(user, "ADMIN", "HR_MANAGER")
    names = ["Task list"] + (["Create task"] if manager else [])
    tabs = dict(zip(names, st.tabs(names)))
    with tabs["Task list"]:
        _list(user, manager)
    if manager:
        with tabs["Create task"]:
            _create(user)


def _due(t):
    if not t["deadline"] or t["status"] == "Completed":
        return ""
    delta = t["deadline"] - datetime.now()
    hrs = int(delta.total_seconds() // 3600)
    if hrs < 0:
        return f"{abs(hrs) // 24}d {abs(hrs) % 24}h overdue" if abs(hrs) >= 24 else f"{abs(hrs)}h overdue"
    return f"in {hrs // 24}d {hrs % 24}h" if hrs >= 24 else f"in {hrs}h"


def _list(user, manager):
    c1, c2, c3 = st.columns(3)
    status = c1.selectbox("Status", ["All"] + list(TASK_STATUSES))
    prio = c2.selectbox("Priority", ["All"] + list(TASK_PRIORITIES))
    emp_id = None
    if manager:
        emps = {e["name"]: e["id"] for e in es.list_employees()}
        pick = c3.selectbox("Assignee", ["All"] + list(emps))
        emp_id = emps.get(pick)
    tasks = ts.list_tasks(user, None if status == "All" else status, None if prio == "All" else prio, emp_id)
    if not tasks:
        st.info("No tasks found.")
        return
    df = pd.DataFrame([{"ID": t["id"], "Priority": f"{_ICON[t['priority']]} {t['priority']}", "Title": t["title"],
                        "Assignee": t["assignee"], "Status": t["status"],
                        "Deadline": f"{t['deadline']:%d %b %Y %H:%M}" if t["deadline"] else "",
                        "Time left": _due(t)} for t in tasks])
    show_df(df)

    st.subheader("Update a task")
    options = {f"#{t['id']} · {t['title']} ({t['status']})": t for t in tasks if t["status"] != "Completed" or manager}
    if not options:
        return
    pick = options[st.selectbox("Task", list(options))]
    if pick["description"]:
        st.caption(pick["description"])
    choices = ["Pending", "In Progress", "Completed"]
    new = st.selectbox("New status", choices, index=choices.index(pick["status"]) if pick["status"] in choices else 0)
    if st.button("Update status"):
        try:
            ts.update_status(user, pick["id"], new)
            flash("Task updated")
            st.rerun()
        except ServiceError as err:
            st.error(str(err))


def _create(user):
    emps = {f"{e['code']} · {e['name']}": e["id"] for e in es.list_employees()}
    with st.form("create_task", clear_on_submit=True):
        title = st.text_input("Title *")
        desc = st.text_area("Description")
        a, b = st.columns(2)
        who = a.selectbox("Assign to", ["Unassigned"] + list(emps))
        prio = b.selectbox("Priority", TASK_PRIORITIES, index=1)
        c, d = st.columns(2)
        due_d = c.date_input("Deadline date", date.today())
        due_t = d.time_input("Deadline time", time(17, 0))
        if st.form_submit_button("Create task"):
            try:
                ts.create_task(user, title, desc, emps.get(who), prio, datetime.combine(due_d, due_t))
                flash("Task created")
                st.rerun()
            except ServiceError as err:
                st.error(str(err))
