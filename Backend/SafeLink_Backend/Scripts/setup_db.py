# scripts/setup_db.py

import os
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables from backend .env explicitly
BASE_DIR = Path(__file__).resolve().parents[1]  # Backend/SafeLink_Backend
load_dotenv(BASE_DIR / ".env")

# --- Read DB credentials ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "safelink_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Construct database URL
DATABASE_URL = (
    f"postgresql+psycopg2://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# --- Table schema creation SQL ---
CREATE_ALERTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    module VARCHAR(50) NOT NULL,
    reason TEXT NOT NULL,
    src_ip VARCHAR(50),
    src_mac VARCHAR(50)
);
"""

CREATE_THREAT_INDICATORS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS threat_indicators (
    id SERIAL PRIMARY KEY,
    indicator_type VARCHAR(20) NOT NULL,
    indicator_value VARCHAR(255) NOT NULL UNIQUE,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',
    confidence FLOAT DEFAULT 0.5,
    source VARCHAR(100),
    description TEXT,
    tags TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    false_positive BOOLEAN DEFAULT FALSE,
    hit_count INTEGER DEFAULT 0,
    last_hit TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_indicator_type ON threat_indicators(indicator_type);
CREATE INDEX IF NOT EXISTS idx_indicator_value ON threat_indicators(indicator_value);
"""

def init_db():
    """Initialize the PostgreSQL database and create required tables."""
    print(f"\n[SafeLink] Connecting to database: {DB_NAME}@{DB_HOST}:{DB_PORT} ...")

    try:
        # Create the SQLAlchemy engine
        engine = create_engine(DATABASE_URL, echo=False, future=True)

        with engine.begin() as conn:
            # Create tables if not exists
            conn.execute(text(CREATE_ALERTS_TABLE_SQL))
            conn.execute(text(CREATE_THREAT_INDICATORS_TABLE_SQL))

        print("[SafeLink] ✅ Database initialized successfully.")
        print("[SafeLink] ✅ 'alerts' and 'threat_indicators' tables are ready for use.\n")

    except SQLAlchemyError as e:
        print("[SafeLink] ❌ Database initialization failed.")
        print(f"Error: {e}\n")

    finally:
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    init_db()
