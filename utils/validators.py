"""Input validation helpers. Every form should pass its data through these."""
import re
from config.settings import MIN_PASSWORD_LENGTH

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,50}$")


def validate_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email or ""))


def validate_username(username: str) -> bool:
    return bool(_USERNAME_RE.match(username or ""))


def validate_password(password: str) -> list[str]:
    """Return a list of problems (empty list = password is OK)."""
    problems = []
    if len(password or "") < MIN_PASSWORD_LENGTH:
        problems.append(f"At least {MIN_PASSWORD_LENGTH} characters")
    if not re.search(r"[A-Z]", password or ""):
        problems.append("One uppercase letter")
    if not re.search(r"[a-z]", password or ""):
        problems.append("One lowercase letter")
    if not re.search(r"\d", password or ""):
        problems.append("One number")
    return problems


_PHONE_RE = re.compile(r"^\+?[0-9 \-]{7,15}$")


def validate_phone(phone: str) -> bool:
    return bool(_PHONE_RE.match((phone or "").strip()))


def clean_text(value: str, max_len: int = 500) -> str:
    """Trim whitespace and cap length (stops oversized / blank-only input)."""
    return (value or "").strip()[:max_len]
