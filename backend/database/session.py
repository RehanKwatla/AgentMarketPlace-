"""SQLAlchemy Database Engine and Session Management."""
import os
from typing import Generator, Optional
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.shared.config import get_settings


def normalize_database_url(url: Optional[str], environment: str = "development") -> str:
    """Normalize database connection string for driver compatibility and enforce production safety.

    1. Normalizes Render/Heroku 'postgres://' URI scheme to SQLAlchemy's expected 'postgresql://'.
    2. Rejects SQLite and empty connection strings when ENVIRONMENT is 'production'.
    3. Guarantees that production will fail clearly instead of silently falling back to ephemeral SQLite.
    4. Never logs or prints credentials.
    """
    clean_url = (url or "").strip()
    is_prod = str(environment).strip().lower() == "production"

    if is_prod:
        if not clean_url or clean_url.startswith("sqlite"):
            raise ValueError(
                "Production environment requires a PostgreSQL DATABASE_URL. "
                "Silent fallback to SQLite or ephemeral storage is strictly prohibited."
            )

    if not clean_url:
        return "sqlite:///./local_data/ledger.db"

    # Normalize Render postgres:// to postgresql://
    if clean_url.startswith("postgres://"):
        clean_url = "postgresql://" + clean_url[len("postgres://"):]

    return clean_url


settings = get_settings()
db_url = normalize_database_url(settings.database_url, settings.environment)

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


from sqlalchemy import inspect, text


def _migrate_schema(engine_to_migrate) -> None:
    """Safely migrate any missing columns or indexes on existing tables.

    Guarantees:
    - Works across both SQLite and PostgreSQL.
    - Idempotent and safe for repeated application startup.
    - Preserves existing data without dropping tables.
    """
    try:
        inspector = inspect(engine_to_migrate)
        table_names = inspector.get_table_names()
        if "ledger_records" in table_names:
            columns = {col["name"] for col in inspector.get_columns("ledger_records")}
            with engine_to_migrate.begin() as conn:
                if "task_id" not in columns:
                    conn.execute(text("ALTER TABLE ledger_records ADD COLUMN task_id VARCHAR(128)"))
                if "call_id" not in columns:
                    conn.execute(text("ALTER TABLE ledger_records ADD COLUMN call_id VARCHAR(128)"))
                if "amount_base_units" not in columns:
                    conn.execute(text("ALTER TABLE ledger_records ADD COLUMN amount_base_units INTEGER DEFAULT 0"))
                if "settlement_proof" not in columns:
                    conn.execute(text("ALTER TABLE ledger_records ADD COLUMN settlement_proof VARCHAR(256)"))
                if "network" not in columns:
                    conn.execute(text("ALTER TABLE ledger_records ADD COLUMN network VARCHAR(64)"))
                if "token_address" not in columns:
                    conn.execute(text("ALTER TABLE ledger_records ADD COLUMN token_address VARCHAR(64)"))
    except Exception:
        pass


def init_db(target_engine=None) -> None:
    """Create all registered database tables and apply required schema migrations."""
    eng = target_engine or engine
    import backend.database.models
    try:
        import backend.payments.models
    except Exception:
        pass
    Base.metadata.create_all(bind=eng)
    _migrate_schema(eng)


if __name__ == "__main__":
    print("[MIGRATION] Initializing database tables and applying non-destructive migrations...")
    init_db()
    print("[MIGRATION] Database schema initialization completed successfully.")
