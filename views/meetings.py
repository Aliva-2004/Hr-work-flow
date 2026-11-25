"""Meeting scheduler."""
from datetime import datetime, date, time, timedelta
import streamlit as st
from services import meeting_service as ms, employee_service as es
from services.auth_service import has_role
from utils.errors import ServiceError
from utils.ui import flash, fmt_dt


def render(user: dict):
    st.title("Meetings")
    manager = has_role(user, "ADMIN", "HR_MANAGER")
    names = ["Upcoming", "Past & notes"] + (["Schedule meeting"] if manager else [])
    tabs = dict(zip(names, st.tabs(names)))
    with tabs["Upcoming"]:
        _show(user, True, manager)
    with tabs["Past & notes"]:
        _show(user, False, manager)
    if manager:
        with tabs["Schedule meeting"]:
            _create(user)


def _show(user, upcoming, manager):
    meetings = ms.list_meetings(user, upcoming)
    if not meetings:
        st.info("No upcoming meetings." if upcoming else "No past meetings.")
        return
    for m in meetings:
        with st.expander(f"{m['title']} · {fmt_dt(m['start'])}"):
            if m["end"]:
                st.caption(f"Until {m['end']:%H:%M}")
            st.markdown(f"**Agenda:** {m['agenda'] or '—'}")
            st.markdown(f"**Participants:** {', '.join(m['participants']) or '—'}")
            if manager:
                notes = st.text_area("Meeting notes", m["notes"], key=f"notes_{m['id']}")
                if st.button("Save notes", key=f"sn_{m['id']}"):
                    try:
                        ms.save_notes(user, m["id"], notes); flash("Notes saved"); st.rerun()
                    except ServiceError as err:
                        st.error(str(err))
            elif m["notes"]:
                st.markdown(f"**Notes:** {m['notes']}")


def _create(user):
    emps = {f"{e['code']} · {e['name']}": e["id"] for e in es.list_employees()}
    with st.form("new_meeting", clear_on_submit=True):
        title = st.text_input("Title *")
        agenda = st.text_area("Agenda")
        a, b, c = st.columns(3)
        d = a.date_input("Date", date.today() + timedelta(days=1))
        t1 = b.time_input("Start", time(10, 0))
        t2 = c.time_input("End", time(11, 0))
        who = st.multiselect("Participants", list(emps))
        if st.form_submit_button("Schedule"):
            try:
                ms.create_meeting(user, title, agenda, datetime.combine(d, t1), datetime.combine(d, t2),
                                  [emps[w] for w in who])
                flash("Meeting scheduled"); st.rerun()
            except ServiceError as err:
                st.error(str(err))
