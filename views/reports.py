"""Reports: analytics, CSV exports, audit log."""
import pandas as pd
import plotly.express as px
import streamlit as st
from services import (analytics_service as an, employee_service as es, leave_service as ls,
                      task_service as ts, email_service as mail, attendance_service as att, audit_service)
from services.auth_service import has_role
from utils.ui import show_chart, show_df, NAVY


def render(user: dict):
    st.title("Reports")
    if not has_role(user, "ADMIN", "HR_MANAGER"):
        st.error("Only Admin and HR Manager can view reports.")
        return
    names = ["Analytics", "Export data"] + (["Audit log"] if user["role"] == "ADMIN" else [])
    tabs = dict(zip(names, st.tabs(names)))
    with tabs["Analytics"]:
        _analytics()
    with tabs["Export data"]:
        _export(user)
    if "Audit log" in tabs:
        with tabs["Audit log"]:
            logs = audit_service.list_logs()
            show_df(pd.DataFrame(logs)) if logs else st.info("No activity yet.")


def _analytics():
    freq = st.radio("Task statistics", ["Weekly", "Monthly"], horizontal=True)
    trend = an.task_trend("W" if freq == "Weekly" else "M")
    if trend.empty:
        st.info("No task data yet.")
    else:
        show_chart(px.line(trend, x="Period", y=["Created", "Completed"], markers=True,
                           color_discrete_sequence=[NAVY, "#7FB3E6"]))
    prod = an.productivity()
    st.subheader("Employee productivity")
    if prod.empty:
        st.info("No assigned tasks yet.")
    else:
        show_chart(px.bar(prod, x="Employee", y=["Completed", "Overdue"], barmode="stack",
                          color_discrete_sequence=[NAVY, "#E57373"]))
        show_df(prod)


def _export(user):
    emps = pd.DataFrame(es.list_employees(include_inactive=True))
    sets = {
        "Employees": emps.drop(columns=["id", "department_id", "user_id", "first_name", "last_name"], errors="ignore"),
        "Leave applications": pd.DataFrame(ls.list_leaves(user)),
        "Tasks": pd.DataFrame(ts.list_tasks(user)),
        "Client emails": pd.DataFrame(mail.list_emails()),
        "Attendance (this month)": pd.DataFrame(att.list_attendance(user, pd.Timestamp.today().replace(day=1).date())),
    }
    for name, df in sets.items():
        with st.expander(f"{name} ({len(df)} rows)"):
            if df.empty:
                st.caption("No data.")
                continue
            show_df(df)
            st.download_button(f"Download {name} (CSV)", df.to_csv(index=False).encode("utf-8"),
                               file_name=f"{name.lower().replace(' ', '_')}.csv", mime="text/csv",
                               key=f"dl_{name}")
