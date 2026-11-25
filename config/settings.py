"""Central configuration. Secrets are read from environment variables / .env only."""
import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "FlowHR AI"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///flowhr.db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

ROLES = ("ADMIN", "HR_MANAGER", "EMPLOYEE")
TASK_PRIORITIES = ("Low", "Medium", "High", "Critical")
TASK_STATUSES = ("Pending", "In Progress", "Completed", "Overdue")
LEAVE_TYPES = ("Casual", "Sick", "Earned", "Unpaid")
MIN_PASSWORD_LENGTH = 8

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or 587)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "") or SMTP_USER

LEAVE_ALLOTMENT = {"Casual": 12, "Sick": 10, "Earned": 15, "Unpaid": 0}
EMAIL_URGENCIES = ("Low", "Normal", "High", "Urgent")
ATTENDANCE_STATUSES = ("Present", "Absent", "Half Day", "On Leave")
