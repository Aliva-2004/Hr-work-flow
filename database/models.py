"""SQLAlchemy models for all 13 FlowHR AI tables."""
from datetime import datetime, date
from sqlalchemy import (String, Integer, Boolean, Date, DateTime, Text, Float,
                        ForeignKey, UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    employees: Mapped[list["Employee"]] = relationship(back_populates="department")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="EMPLOYEE")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_login: Mapped[datetime | None] = mapped_column(DateTime)
    employee: Mapped["Employee | None"] = relationship(back_populates="user", uselist=False)
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), unique=True)
    first_name: Mapped[str] = mapped_column(String(60))
    last_name: Mapped[str] = mapped_column(String(60))
    phone: Mapped[str | None] = mapped_column(String(20))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    designation: Mapped[str | None] = mapped_column(String(100))
    date_of_joining: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    user: Mapped["User | None"] = relationship(back_populates="employee")
    department: Mapped["Department | None"] = relationship(back_populates="employees")
    leave_applications: Mapped[list["LeaveApplication"]] = relationship(back_populates="employee")
    leave_balances: Mapped[list["LeaveBalance"]] = relationship(back_populates="employee")
    tasks: Mapped[list["Task"]] = relationship(back_populates="assignee")
    attendance: Mapped[list["Attendance"]] = relationship(back_populates="employee")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class LeaveApplication(Base):
    __tablename__ = "leave_applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    leave_type: Mapped[str] = mapped_column(String(30))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending/Approved/Rejected
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    employee: Mapped["Employee"] = relationship(back_populates="leave_applications")


class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    __table_args__ = (UniqueConstraint("employee_id", "leave_type", "year"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    leave_type: Mapped[str] = mapped_column(String(30))
    year: Mapped[int] = mapped_column(Integer)
    total_days: Mapped[float] = mapped_column(Float, default=0)
    used_days: Mapped[float] = mapped_column(Float, default=0)
    employee: Mapped["Employee"] = relationship(back_populates="leave_balances")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    priority: Mapped[str] = mapped_column(String(10), default="Medium")
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    deadline: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    assignee: Mapped["Employee | None"] = relationship(back_populates="tasks")


class Client(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    company: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    emails: Mapped[list["Email"]] = relationship(back_populates="client")


class Email(Base):
    __tablename__ = "emails"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    subject: Mapped[str] = mapped_column(String(250))
    body: Mapped[str] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(String(10), default="Inbound")  # Inbound/Outbound
    urgency: Mapped[str] = mapped_column(String(10), default="Normal")  # Low/Normal/High/Urgent
    status: Mapped[str] = mapped_column(String(20), default="Unanswered")  # Unanswered/Answered/Follow-up
    ai_draft: Mapped[str | None] = mapped_column(Text)
    handled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime)
    client: Mapped["Client"] = relationship(back_populates="emails")


class Meeting(Base):
    __tablename__ = "meetings"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    agenda: Mapped[str | None] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    participants: Mapped[list["MeetingParticipant"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan")


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"
    __table_args__ = (UniqueConstraint("meeting_id", "employee_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    meeting: Mapped["Meeting"] = relationship(back_populates="participants")


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(150))
    message: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30))  # leave/task/overdue/meeting/email
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    user: Mapped["User"] = relationship(back_populates="notifications")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    date: Mapped[date] = mapped_column(Date)
    check_in: Mapped[datetime | None] = mapped_column(DateTime)
    check_out: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="Present")
    employee: Mapped["Employee"] = relationship(back_populates="attendance")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
