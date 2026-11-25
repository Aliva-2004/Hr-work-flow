"""Dashboard: organisation-wide for Admin/HR, personal for employees."""
import pandas as pd
import plotly.express as px
import streamlit as st
from services import analytics_service as an, employee_service, leave_service
from services.auth_service import has_role
from utils.ui import kpi_card, show_chart, show_df, NAVY


def render(user: dict):
    st.title("Dashboard")
    st.caption(f"Welcome back, {user['username']} · {user['role'].replace('_', ' ').title()}")
    manager = has_role(user, "ADMIN", "HR_MANAGER")
    eid = None if manager else employee_service.get_employee_id(user["id"])
    if not manager and eid is None:
        st.warning("Your login is not linked to an employee profile yet. Ask HR to link it.")
        return
    stats = an.get_dashboard_stats(eid)

    if manager:
        cells = [("Total Employees", stats["employees"]), ("Pending Tasks", stats["pending_tasks"]),
                 ("Completed Tasks", stats["completed_tasks"]), ("Overdue Tasks", stats["overdue_tasks"]),
                 ("Pending Leaves", stats["pending_leaves"]), ("Upcoming Meetings", stats["upcoming_meetings"]),
                 ("Unanswered Emails", stats["unanswered_emails"]), ("Present Today", stats["present_today"])]
    else:
        left = sum(b["remaining"] for b in leave_service.get_balances(eid) if b["type"] != "Unpaid")
        cells = [("My Pending Tasks", stats["pending_tasks"]), ("My Completed Tasks", stats["completed_tasks"]),
                 ("My Overdue Tasks", stats["overdue_tasks"]), ("Leave Days Left", f"{left:g}"),
                 ("My Pending Leaves", stats["pending_leaves"]), ("Upcoming Meetings", stats["upcoming_meetings"])]
    for i in range(0, len(cells), 4):
        cols = st.columns(4)
        for col, (label, val) in zip(cols, cells[i:i + 4]):
            kpi_card(label, val, col)
        st.write("")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Tasks by status")
        if stats["tasks_by_status"]:
            df = pd.DataFrame(list(stats["tasks_by_status"].items()), columns=["Status", "Tasks"])
            show_chart(px.pie(df, names="Status", values="Tasks", hole=0.5,
                              color_discrete_sequence=px.colors.sequential.Blues_r))
        else:
            st.info("No tasks yet.")
    with c2:
        st.subheader("Open tasks by priority")
        if stats["open_tasks_by_priority"]:
            df = pd.DataFrame(list(stats["open_tasks_by_priority"].items()), columns=["Priority", "Tasks"])
            show_chart(px.bar(df, x="Priority", y="Tasks", color_discrete_sequence=[NAVY]))
        else:
            st.info("No open tasks.")

    st.subheader("Task statistics")
    period = st.radio("View", ["Weekly", "Monthly"], horizontal=True, label_visibility="collapsed")
    trend = an.task_trend("W" if period == "Weekly" else "M", eid)
    if trend.empty:
        st.info("Statistics appear once tasks exist.")
    else:
        show_chart(px.bar(trend, x="Period", y=["Created", "Completed"], barmode="group",
                          color_discrete_sequence=[NAVY, "#7FB3E6"]))
    if manager:
        st.subheader("Employee productivity")
        prod = an.productivity()
        if prod.empty:
            st.info("Productivity appears once tasks are assigned.")
        else:
            show_chart(px.bar(prod, x="Employee", y="Completion %", color_discrete_sequence=[NAVY], range_y=[0, 100]))
            show_df(prod)
