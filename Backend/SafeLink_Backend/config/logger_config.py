import logging
import os
from logging.handlers import RotatingFileHandler

# Create the logs directory if it doesn't exist
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# File paths
MAIN_LOG_FILE = os.path.join(LOG_DIR, "safelink.log")
ALERT_LOG_FILE = os.path.join(LOG_DIR, "alerts_log.csv")

def setup_logger(name: str, log_file: str = MAIN_LOG_FILE, level=logging.INFO):
    """
    Creates and returns a configured logger instance.
    
    Args:
        name (str): Logger name.
        log_file (str): Path to log file.
        level (int): Logging level (default: INFO).
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Rotating file handler (to prevent large log files)
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    logger.propagate = False
    return logger


# Example usage: (import in other files like this)
# from config.logger_config import setup_logger
# logger = setup_logger("dfa_filter")

# Optional: Create default main logger
main_logger = setup_logger("SafeLinkMain", MAIN_LOG_FILE)
