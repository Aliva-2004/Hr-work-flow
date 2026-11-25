"""Client email management with AI reply drafts."""
from datetime import datetime
import pandas as pd
import streamlit as st
from services import email_service as mail, ai_service as ai
from services.auth_service import has_role
from utils.errors import ServiceError
from utils.ui import show_df, flash, fmt_dt
from config.settings import EMAIL_URGENCIES

_BADGE = {"Urgent": "🔴", "High": "🟠", "Normal": "🔵", "Low": "⚪"}


def render(user: dict):
    st.title("Client Emails")
    if not has_role(user, "ADMIN", "HR_MANAGER"):
        st.error("Only Admin and HR Manager can access client emails.")
        return
    t1, t2, t3, t4 = st.tabs(["Inbox & replies", "Log an email", "Clients", "Follow-up history"])
    with t1:
        _inbox(user)
    with t2:
        _log(user)
    with t3:
        _clients(user)
    with t4:
        _history(user)


def _inbox(user):
    c1, c2 = st.columns(2)
    status = c1.selectbox("Status", ["Unanswered", "Follow-up", "Answered", "All"])
    urg = c2.selectbox("Urgency", ["All"] + list(reversed(EMAIL_URGENCIES)))
    emails = [e for e in mail.list_emails(None if status == "All" else status,
                                          urgency=None if urg == "All" else urg) if e["direction"] == "Inbound"]
    if not emails:
        st.info("No emails match. Log incoming client emails in the next tab.")
        return
    for e in emails:
        title = f"{_BADGE[e['urgency']]} {e['urgency']} · {e['client']} · {e['subject']} · {fmt_dt(e['received_at'])} · {e['status']}"
        with st.expander(title):
            st.write(e["body"])
            if e["status"] == "Answered":
                st.caption(f"Replied {fmt_dt(e['replied_at'])}")
                continue
            key = f"draft_{e['id']}"
            if key not in st.session_state:
                st.session_state[key] = e["ai_draft"]
            c1, c2, _ = st.columns([1, 1, 3])
            tone = c2.selectbox("Tone", ["Professional", "Friendly", "Formal", "Apologetic"], key=f"tone_{e['id']}")
            if c1.button("✨ Generate AI reply", key=f"gen_{e['id']}"):
                with st.spinner("Drafting..."):
                    text, used = ai.draft_reply(user, e["id"], tone)
                st.session_state[key] = text
                mail.save_draft(e["id"], text)
                if not used:
                    st.warning("Showing a template reply (no AI key configured or AI unavailable).")
            subj = st.text_input("Subject", f"Re: {e['subject']}", key=f"subj_{e['id']}")
            st.text_area("Reply (edit before sending)", key=key, height=200)
            smtp = st.checkbox("Send by email (SMTP)", value=False, key=f"smtp_{e['id']}",
                               disabled=not mail.smtp_configured(),
                               help=None if mail.smtp_configured() else "Set SMTP_* values in .env to enable sending.")
            a, b, _ = st.columns([1, 1, 3])
            if a.button("Send / record reply", key=f"send_{e['id']}"):
                try:
                    sent = mail.send_reply(user, e["id"], subj, st.session_state[key], smtp)
                    flash("Email sent and recorded" if sent else "Reply recorded (not emailed)")
                    st.rerun()
                except ServiceError as err:
                    st.error(str(err))
            if e["status"] != "Follow-up" and b.button("Mark follow-up", key=f"fu_{e['id']}"):
                try:
                    mail.set_followup(user, e["id"]); flash("Marked for follow-up"); st.rerun()
                except ServiceError as err:
                    st.error(str(err))


def _log(user):
    clients = {f"{c['name']} <{c['email']}>": c["id"] for c in mail.list_clients()}
    if not clients:
        st.info("Add a client first (Clients tab).")
        return
    with st.form("log_email", clear_on_submit=True):
        who = st.selectbox("Client", list(clients))
        direction = st.radio("Direction", ["Inbound", "Outbound"], horizontal=True)
        subject = st.text_input("Subject *")
        body = st.text_area("Message *", height=160)
        if st.form_submit_button("Save email"):
            try:
                mail.log_email(user, clients[who], subject, body, direction)
                flash("Email saved (urgency detected automatically)")
                st.rerun()
            except ServiceError as err:
                st.error(str(err))


def _clients(user):
    rows = mail.list_clients()
    if rows:
        show_df(pd.DataFrame(rows).rename(columns=str.title))
    with st.form("add_client", clear_on_submit=True):
        a, b = st.columns(2)
        name = a.text_input("Name *")
        company = b.text_input("Company")
        email = a.text_input("Email *")
        phone = b.text_input("Phone")
        if st.form_submit_button("Add client"):
            try:
                mail.add_client(user, name, company, email, phone)
                flash("Client added"); st.rerun()
            except ServiceError as err:
                st.error(str(err))


def _history(user):
    clients = {c["name"]: c["id"] for c in mail.list_clients()}
    if not clients:
        st.info("No clients yet.")
        return
    cid = clients[st.selectbox("Client", list(clients), key="hist_client")]
    emails = sorted(mail.list_emails(client_id=cid), key=lambda e: e["received_at"])
    if st.button("Summarise this conversation"):
        text, used = ai.summarize_client(user, cid)
        st.info(text)
    for e in emails:
        arrow = "⬅️ Received" if e["direction"] == "Inbound" else "➡️ Sent"
        st.markdown(f"**{arrow}** · {fmt_dt(e['received_at'])} · {e['subject']} · _{e['status']}_")
        st.caption(e["body"][:300])
