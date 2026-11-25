import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
import pytest
from database.connection import init_db
from services import auth_service as a
from services.analytics_service import get_dashboard_stats
from utils.validators import validate_password


def setup_module():
    init_db()


def test_weak_password_rejected():
    assert validate_password("abc")
    assert validate_password("Strong123") == []


def test_create_and_login():
    a.create_user("admin", "admin@example.com", "Strong123", "ADMIN")
    user = a.authenticate("admin", "Strong123")
    assert user["role"] == "ADMIN" and "password_hash" not in user
    with pytest.raises(a.AuthError):
        a.authenticate("admin", "wrong")


def test_duplicate_user_rejected():
    with pytest.raises(a.AuthError):
        a.create_user("admin", "other@example.com", "Strong123")


def test_stats_on_empty_db():
    assert get_dashboard_stats()["employees"] == 0
