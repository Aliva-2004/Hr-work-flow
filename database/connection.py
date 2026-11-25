"""Database engine and session handling (SQLite now, MySQL later via DATABASE_URL)."""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from config.settings import DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    _kwargs = {"connect_args": {"check_same_thread": False}}
    if ":memory:" in DATABASE_URL:  # keep one shared connection so tests see the same DB
        _kwargs["poolclass"] = StaticPool
else:
    _kwargs = {}
engine = create_engine(DATABASE_URL, future=True, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def get_session():
    """Yield a session; commit on success, roll back on error, always close."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Create all tables if they don't exist."""
    from database.models import Base
    Base.metadata.create_all(engine)
