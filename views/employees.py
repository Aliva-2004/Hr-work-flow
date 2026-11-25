"""Employees page: directory, profile editing, add employee, departments."""
from datetime import date
import pandas as pd
import streamlit as st
from services import employee_service as es
from services.auth_service import has_role
from utils.errors import ServiceError
from utils.ui import show_df, flash
from config.settings import ROLES


def render(user: dict):
    st.title("Employees")
    if not has_role(user, "ADMIN", "HR_MANAGER"):
        st.error("Only Admin and HR Manager can manage employees.")
        return
    t1, t2, t3 = st.tabs(["Directory", "Add employee", "Departments"])
    with t1:
        _directory(user)
    with t2:
        _add(user)
    with t3:
        _departments(user)


def _dept_options():
    depts = es.list_departments()
    return {"— None —": None, **{d["name"]: d["id"] for d in depts}}


def _directory(user):
    c1, c2 = st.columns([3, 1])
    q = c1.text_input("Search by name, ID or designation")
    inactive = c2.checkbox("Show inactive")
    emps = es.list_employees(include_inactive=inactive)
    if q:
        emps = [e for e in emps if q.lower() in f"{e['code']} {e['name']} {e['designation']}".lower()]
    if not emps:
        st.info("No employees found. Add one in the 'Add employee' tab.")
        return
    df = pd.DataFrame(emps)[["code", "name", "department", "designation", "phone", "username", "role", "is_active"]]
    df.columns = ["ID", "Name", "Department", "Designation", "Phone", "Username", "Role", "Active"]
    show_df(df)

    st.subheader("Employee profile")
    labels = {f"{e['code']} · {e['name']}": e for e in emps}
    e = labels[st.selectbox("Select employee", list(labels))]
    depts = _dept_options()
    names = list(depts)
    cur = next((n for n, i in depts.items() if i == e["department_id"]), names[0])
    with st.form(f"edit_{e['id']}"):
        a, b = st.columns(2)
        first = a.text_input("First name", e["first_name"])
        last = b.text_input("Last name", e["last_name"])
        phone = a.text_input("Phone", e["phone"])
        desig = b.text_input("Designation", e["designation"])
        dept = a.selectbox("Department", names, index=names.index(cur))
        doj = b.date_input("Date of joining", e["date_of_joining"] or date.today())
        if st.form_submit_button("Save changes"):
            try:
                es.update_employee(user, e["id"], first, last, phone, depts[dept], desig, doj)
                flash("Employee updated")
                st.rerun()
            except ServiceError as err:
                st.error(str(err))
    st.caption(f"Login: {e['username'] or 'none'} · {e['email']}")
    label = "Deactivate employee" if e["is_active"] else "Reactivate employee"
    if st.button(label, key=f"act_{e['id']}"):
        try:
            es.set_active(user, e["id"], not e["is_active"])
            flash(f"{e['name']} {'deactivated' if e['is_active'] else 'reactivated'}")
            st.rerun()
        except ServiceError as err:
            st.error(str(err))


def _add(user):
    depts = _dept_options()
    with st.form("add_employee", clear_on_submit=True):
        a, b = st.columns(2)
        first = a.text_input("First name *")
        last = b.text_input("Last name *")
        phone = a.text_input("Phone")
        desig = b.text_input("Designation")
        dept = a.selectbox("Department", list(depts))
        doj = b.date_input("Date of joining", date.today())
        st.markdown("**Login account** (optional — leave username blank to skip)")
        c, d = st.columns(2)
        username = c.text_input("Username")
        email = d.text_input("Email")
        pw = c.text_input("Temporary password", type="password")
        roles = [r for r in ROLES if r != "ADMIN" or user["role"] == "ADMIN"]
        role = d.selectbox("Role", roles, index=roles.index("EMPLOYEE"))
        if st.form_submit_button("Add employee"):
            account = {"username": username, "email": email, "password": pw, "role": role} if username.strip() else None
            try:
                es.create_employee(user, first, last, phone, depts[dept], desig, doj, account)
                flash("Employee added")
                st.rerun()
            except ServiceError as err:
                st.error(str(err))


def _departments(user):
    depts = es.list_departments()
    if depts:
        show_df(pd.DataFrame(depts).rename(columns={"id": "ID", "name": "Department"}))
    with st.form("add_dept", clear_on_submit=True):
        name = st.text_input("New department name")
        if st.form_submit_button("Add department"):
            try:
                es.create_department(user, name)
                flash("Department added")
                st.rerun()
            except ServiceError as err:
                st.error(str(err))
