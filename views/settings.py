"""Settings: password, user accounts (admin), system status."""
import pandas as pd
import streamlit as st
from services import auth_service as auth
from services import ai_service, email_service
from utils.errors import ServiceError
from utils.ui import show_df, flash
from config.settings import ROLES, DATABASE_URL


def render(user: dict):
    st.title("Settings")
    names = ["My account"] + (["User accounts", "System status"] if user["role"] == "ADMIN" else [])
    tabs = dict(zip(names, st.tabs(names)))
    with tabs["My account"]:
        st.write(f"**Username:** {user['username']}  \n**Email:** {user['email']}  \n**Role:** {user['role']}")
        with st.form("pw", clear_on_submit=True):
            old = st.text_input("Current password", type="password")
            new = st.text_input("New password", type="password")
            again = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Change password"):
                if new != again:
                    st.error("New passwords do not match.")
                else:
                    try:
                        auth.change_password(user["id"], old, new)
                        flash("Password changed")
                        st.rerun()
                    except ServiceError as err:
                        st.error(str(err))
    if user["role"] != "ADMIN":
        return
    with tabs["User accounts"]:
        users = auth.list_users()
        show_df(pd.DataFrame(users).drop(columns=["id"]))
        labels = {u["username"]: u for u in users}
        u = labels[st.selectbox("Select account", list(labels))]
        c1, c2 = st.columns(2)
        role = c1.selectbox("Role", ROLES, index=ROLES.index(u["role"]))
        if c1.button("Update role"):
            try:
                auth.set_user_role(user, u["id"], role); flash("Role updated"); st.rerun()
            except ServiceError as err:
                st.error(str(err))
        if c2.button("Deactivate account" if u["is_active"] else "Reactivate account"):
            try:
                auth.set_user_active(user, u["id"], not u["is_active"]); flash("Account updated"); st.rerun()
            except ServiceError as err:
                st.error(str(err))
        with st.form("reset_pw", clear_on_submit=True):
            pw = st.text_input("Set a new password for this account", type="password")
            if st.form_submit_button("Reset password"):
                try:
                    auth.admin_reset_password(user, u["id"], pw); flash("Password reset"); st.rerun()
                except ServiceError as err:
                    st.error(str(err))
    with tabs["System status"]:
        st.write(f"**Database:** {'SQLite' if DATABASE_URL.startswith('sqlite') else DATABASE_URL.split(':')[0]}")
        st.write(f"**AI (Gemini) configured:** {'Yes' if ai_service.ai_enabled() else 'No — add GEMINI_API_KEY to .env'}")
        st.write(f"**Email sending (SMTP) configured:** {'Yes' if email_service.smtp_configured() else 'No — add SMTP_* to .env'}")
