"""
Simple logging configuration for Recall AI
"""
from io import StringIO
import os
import logging
import sys
from pathlib import Path
from typing import Any, Dict

"""
Simple logging configuration for Recall AI (No file logging to prevent logs folder)
"""


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Set up simple logging for the application (console only, no files)"""

    # Check if we should disable file logging
    disable_file_logging = os.getenv(
        'DISABLE_FILE_LOGGING', 'false').lower() == 'true'

    handlers = [logging.StreamHandler(sys.stdout)]

    # Only add file handler if not disabled and not in clean mode
    if not disable_file_logging and not os.getenv('PYTHONDONTWRITEBYTECODE'):
        from pathlib import Path
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        handlers.append(logging.FileHandler(log_dir / "recall_ai.log"))

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True  # Override any existing configuration
    )

    logger = logging.getLogger("recall_ai")

    # Log where we're logging to
    if disable_file_logging or os.getenv('PYTHONDONTWRITEBYTECODE'):
        logger.info("🧹 Clean mode: Logging to console only (no files)")
    else:
        logger.info("📝 Logging to both console and file")

    return logger


def log_user_action(logger: logging.Logger, user_id: int, username: str, action: str, details: Dict[str, Any] = None) -> None:
    """Log user actions"""
    logger.info(
        f"User {username} ({user_id}) performed {action}: {details or {}}")


def log_error(logger: logging.Logger, error: Exception, context: Dict[str, Any] = None) -> None:
    """Log errors with context"""
    logger.error(f"Error: {error} | Context: {context or {}}", exc_info=True)
