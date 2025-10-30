from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

# Check if DATABASE_URL is set (for Docker/SQLite), otherwise use PostgreSQL settings
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # PostgreSQL configuration (fallback)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "safelink_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    
    # Quote credentials so special characters (e.g. @, :) stay valid in the URL
    DATABASE_URL = (
        f"postgresql+psycopg2://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}@"
        f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

MODELS_DIR = Path(os.getenv("MODELS_DIR", BASE_DIR / "models"))
MODELS_DIR.mkdir(parents=True, exist_ok=True)

PLOTS_DIR = Path(os.getenv("PLOTS_DIR", MODELS_DIR / "plots"))
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_FILENAME = Path(os.getenv("MODEL_FILENAME", MODELS_DIR / "ann_model.pt"))
DATASET_CSV = Path(os.getenv("DATASET_CSV", BASE_DIR / "data" / "All_Labelled.csv"))

DEVICE = os.getenv("DEVICE", "cpu")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "256"))
NUM_EPOCHS = int(os.getenv("NUM_EPOCHS", "50"))
LEARNING_RATE = float(os.getenv("LEARNING_RATE", "0.001"))
WEIGHT_DECAY = float(os.getenv("WEIGHT_DECAY", "0.0001"))
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
_hidden_dims_env = os.getenv("HIDDEN_DIMS", "512,256,128,64")
HIDDEN_DIMS = tuple(int(x.strip()) for x in _hidden_dims_env.split(",") if x.strip())
DROPOUT_RATE = float(os.getenv("DROPOUT_RATE", "0.35"))
EARLY_STOP_PATIENCE = int(os.getenv("EARLY_STOP_PATIENCE", "6"))
EARLY_STOP_DELTA = float(os.getenv("EARLY_STOP_DELTA", "1e-4"))

TRAINING_PROGRESS_FILE = Path(
	os.getenv("TRAINING_PROGRESS_FILE", BASE_DIR / "logs" / "training_progress.json")
)
TRAINING_PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)

# Security Settings
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_WORKERS = int(os.getenv("API_WORKERS", "4"))

# Celery Settings
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Threat Intelligence
ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY", "")
MAC_VENDOR_CACHE_TTL = int(os.getenv("MAC_VENDOR_CACHE_TTL", "86400"))

# SIEM Export
SIEM_ENABLED = os.getenv("SIEM_ENABLED", "false").lower() == "true"
SIEM_FORMAT = os.getenv("SIEM_FORMAT", "syslog")
SIEM_HOST = os.getenv("SIEM_HOST", "localhost")
SIEM_PORT = int(os.getenv("SIEM_PORT", "514"))
SIEM_PROTOCOL = os.getenv("SIEM_PROTOCOL", "udp")

# Mitigation
MITIGATION_AUTO_APPROVE = os.getenv("MITIGATION_AUTO_APPROVE", "false").lower() == "true"
MITIGATION_BACKEND = os.getenv("MITIGATION_BACKEND", "snmp")
MITIGATION_SNMP_COMMUNITY = os.getenv("MITIGATION_SNMP_COMMUNITY", "private")

# Monitoring
ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
