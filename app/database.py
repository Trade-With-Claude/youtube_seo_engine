from sqlmodel import SQLModel, Session, create_engine

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


def init_db():
    # Enable WAL mode for better concurrent read performance
    import sqlite3

    db_path = settings.database_url.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.close()

    # Import models so SQLModel knows about them
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
