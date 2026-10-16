"""SQLAlchemy Database Engine and Session Management."""
import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.shared.config import get_settings

settings = get_settings()
db_url = settings.database_url

# If using SQLite locally, ensure target directory exists
if db_url.startswith("sqlite"):
    db_path = db_url.replace("sqlite:///", "")
    dir_name = os.path.dirname(db_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency providing database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from sqlalchemy import text


def init_db() -> None:
    """Create all registered database tables and apply lightweight migrations if needed."""
    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            # Check if ledger_records table exists and needs added columns
            res = conn.execute(text("PRAGMA table_info(ledger_records)"))
            cols = {row[1] for row in res.fetchall()}
            if cols:
                if "payment_id" not in cols:
                    conn.execute(text("ALTER TABLE ledger_records ADD COLUMN payment_id VARCHAR(64)"))
                if "listed_price_units" not in cols:
                    conn.execute(text("ALTER TABLE ledger_records ADD COLUMN listed_price_units INTEGER"))
                if "amount_paid_units" not in cols:
                    conn.execute(text("ALTER TABLE ledger_records ADD COLUMN amount_paid_units INTEGER"))
                if "network" not in cols:
                    conn.execute(text("ALTER TABLE ledger_records ADD COLUMN network VARCHAR(64)"))
                if "token" not in cols:
                    conn.execute(text("ALTER TABLE ledger_records ADD COLUMN token VARCHAR(64)"))
                conn.commit()
    except Exception:
        pass

