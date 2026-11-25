"""Notifications centre."""
import streamlit as st
from services import notification_service as ns
from utils.ui import flash, fmt_dt

_ICON = {"leave": "🌴", "task": "⏰", "overdue": "🚨", "meeting": "📅", "email": "📧"}


def render(user: dict):
    st.title("Notifications")
    a, b, _ = st.columns([1, 1, 4])
    if a.button("Check for new alerts"):
        n = ns.generate_alerts(user)
        flash(f"{n} new alert(s)" if n else "No new alerts")
        st.rerun()
    if b.button("Mark all read"):
        ns.mark_all_read(user["id"])
        st.rerun()
    only_unread = st.checkbox("Unread only")
    items = ns.list_notifications(user["id"], only_unread)
    if not items:
        st.info("You're all caught up.")
        return
    for n in items:
        with st.container(border=True):
            c1, c2 = st.columns([8, 1])
            mark = "" if n["is_read"] else "🔵 "
            c1.markdown(f"{mark}{_ICON.get(n['category'], '🔔')} **{n['title']}**  \n{n['message']}  \n"
                        f"<small>{fmt_dt(n['created_at'])}</small>", unsafe_allow_html=True)
            if not n["is_read"] and c2.button("Read", key=f"r_{n['id']}"):
                ns.mark_read(user["id"], n["id"])
                st.rerun()
