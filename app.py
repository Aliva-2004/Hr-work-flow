"""FlowHR AI entry point: first-run setup, login, sidebar navigation, page routing."""
import streamlit as st
from config.settings import APP_NAME
from database.connection import init_db
from services.auth_service import authenticate, create_user, has_users, AuthError
from services import notification_service as ns
from utils.ui import inject_css, show_flash
from views import (dashboard, employees, leave, tasks, client_emails, meetings,
                   ai_assistant, notifications, reports, settings)

st.set_page_config(page_title=APP_NAME, page_icon="🧭", layout="wide")
init_db()
inject_css()

PAGES = {
    "Dashboard": dashboard, "Employees": employees, "Leave Management": leave,
    "Tasks & Deadlines": tasks, "Client Emails": client_emails, "Meetings": meetings,
    "AI Assistant": ai_assistant, "Notifications": notifications, "Reports": reports,
    "Settings": settings,
}
EMPLOYEE_PAGES = ["Dashboard", "Leave Management", "Tasks & Deadlines", "Meetings",
                  "AI Assistant", "Notifications", "Settings"]


def setup_screen():
    st.title(f"Welcome to {APP_NAME}")
    st.subheader("First-time setup: create the administrator account")
    with st.form("setup"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        if st.form_submit_button("Create admin"):
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    create_user(username, email, password, role="ADMIN")
                    st.rerun()
                except AuthError as e:
                    st.error(str(e))


def login_screen():
    st.title(f"{APP_NAME} · Sign in")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Sign in"):
            try:
                st.session_state["user"] = authenticate(username, password)
                st.rerun()
            except AuthError as e:
                st.error(str(e))


def main_app(user: dict):
    if not st.session_state.get("alerts_checked"):
        ns.generate_alerts(user)
        st.session_state["alerts_checked"] = True
    pages = list(PAGES) if user["role"] in ("ADMIN", "HR_MANAGER") else EMPLOYEE_PAGES
    unread = ns.unread_count(user["id"])
    with st.sidebar:
        st.markdown(f"## 🧭 {APP_NAME}")
        page = st.radio("Navigation", pages, label_visibility="collapsed")
        st.divider()
        st.caption(f"👤 {user['username']} · {user['role'].replace('_', ' ').title()}")
        if unread:
            st.caption(f"🔔 {unread} unread notification(s)")
        if st.button("Log out"):
            for k in ("user", "alerts_checked", "ai_chat"):
                st.session_state.pop(k, None)
            st.rerun()
    show_flash()
    PAGES[page].render(user)


if not has_users():
    setup_screen()
elif "user" not in st.session_state:
    login_screen()
else:
    main_app(st.session_state["user"])
