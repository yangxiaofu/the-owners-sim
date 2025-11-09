"""
Logging Configuration for The Owner's Sim

This module provides production-grade logging configuration with:
- Rotating file handlers (prevents unbounded log growth)
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured formatting with timestamps and context
- Module-specific loggers for granular control
- Console and file output with different levels

Usage Example:
    from logging_config import setup_logging, get_logger

    # Setup logging at application startup
    setup_logging(
        level="INFO",
        log_dir="logs",
        enable_console=True,
        enable_file=True
    )

    # Get logger in any module
    logger = get_logger(__name__)
    logger.info("Application started")
    logger.error("An error occurred", exc_info=True)

Log Files Created:
- logs/the_owners_sim.log: Main application log (INFO+)
- logs/the_owners_sim_debug.log: Debug log (DEBUG+)
- logs/the_owners_sim_error.log: Error log (ERROR+)

Each file rotates at 10MB with 5 backup files (max ~50MB per log type).
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


# Log format templates
DETAILED_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - "
    "[%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"
)

SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

CONSOLE_FORMAT = "%(levelname)s - %(name)s - %(message)s"

# Date format
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for console output.

    Adds ANSI color codes to log levels for better readability.
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        """Add color to levelname"""
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            )
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_dir: str = "logs",
    enable_console: bool = True,
    enable_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    format_style: str = "detailed"
) -> None:
    """
    Setup application-wide logging configuration.

    This function should be called once at application startup.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        enable_console: Whether to log to console
        enable_file: Whether to log to file
        max_bytes: Maximum size per log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        format_style: "detailed" or "simple" format

    Example:
        >>> setup_logging(level="DEBUG", log_dir="logs", enable_console=True)
        >>> logger = get_logger(__name__)
        >>> logger.info("Logging configured successfully")
    """
    # Create log directory if needed
    if enable_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Select format
    log_format = DETAILED_FORMAT if format_style == "detailed" else SIMPLE_FORMAT

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level.upper()))

        # Use colored formatter for console
        console_formatter = ColoredFormatter(CONSOLE_FORMAT, datefmt=DATE_FORMAT)
        console_handler.setFormatter(console_formatter)

        root_logger.addHandler(console_handler)

    # File handlers
    if enable_file:
        # Main log (INFO+)
        main_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, "the_owners_sim.log"),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.INFO)
        main_formatter = logging.Formatter(log_format, datefmt=DATE_FORMAT)
        main_handler.setFormatter(main_formatter)
        root_logger.addHandler(main_handler)

        # Debug log (DEBUG+)
        debug_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, "the_owners_sim_debug.log"),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_formatter = logging.Formatter(DETAILED_FORMAT, datefmt=DATE_FORMAT)
        debug_handler.setFormatter(debug_formatter)
        root_logger.addHandler(debug_handler)

        # Error log (ERROR+)
        error_handler = logging.handlers.RotatingFileHandler(
            filename=os.path.join(log_dir, "the_owners_sim_error.log"),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(DETAILED_FORMAT, datefmt=DATE_FORMAT)
        error_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_handler)

    # Log startup message
    root_logger.info(
        f"Logging initialized - Level: {level}, "
        f"Console: {enable_console}, File: {enable_file}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Module initialized")
        >>> logger.debug("Debug information", extra={"user_id": 123})
    """
    return logging.getLogger(name)


def log_exception(
    logger: logging.Logger,
    exception: Exception,
    context: Optional[dict] = None,
    level: str = "ERROR"
) -> None:
    """
    Log an exception with full traceback and context.

    Args:
        logger: Logger instance
        exception: Exception to log
        context: Additional context dict (dynasty_id, date, etc.)
        level: Log level (default: ERROR)

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     log_exception(
        ...         logger,
        ...         e,
        ...         context={"dynasty_id": "1st", "operation": "advance_day"}
        ...     )
    """
    log_level = getattr(logging, level.upper())

    # Build context string
    context_str = ""
    if context:
        context_items = [f"{k}={v}" for k, v in context.items()]
        context_str = f" [{', '.join(context_items)}]"

    # Log with traceback
    logger.log(
        log_level,
        f"Exception occurred{context_str}: {type(exception).__name__}: {str(exception)}",
        exc_info=True
    )


def configure_module_logger(
    module_name: str,
    level: Optional[str] = None,
    propagate: bool = True
) -> logging.Logger:
    """
    Configure logging for a specific module.

    Useful for setting different log levels for different modules
    (e.g., DEBUG for playoff_system, INFO for everything else).

    Args:
        module_name: Module name (e.g., "playoff_system.playoff_controller")
        level: Log level for this module (None = inherit from root)
        propagate: Whether to propagate to parent loggers

    Returns:
        Configured logger

    Example:
        >>> # Enable DEBUG logging only for playoff system
        >>> playoff_logger = configure_module_logger(
        ...     "playoff_system",
        ...     level="DEBUG"
        ... )
    """
    logger = logging.getLogger(module_name)

    if level:
        logger.setLevel(getattr(logging, level.upper()))

    logger.propagate = propagate

    return logger


class LogContext:
    """
    Context manager for temporary log level changes.

    Useful for verbose logging in specific code blocks.

    Example:
        >>> logger = get_logger(__name__)
        >>> with LogContext(logger, "DEBUG"):
        ...     logger.debug("This will be logged even if global level is INFO")
        ...     complex_operation()
    """

    def __init__(self, logger: logging.Logger, level: str):
        """
        Initialize log context.

        Args:
            logger: Logger to modify
            level: Temporary log level
        """
        self.logger = logger
        self.new_level = getattr(logging, level.upper())
        self.original_level = logger.level

    def __enter__(self):
        """Set temporary level"""
        self.logger.setLevel(self.new_level)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original level"""
        self.logger.setLevel(self.original_level)


# Module-specific logger configurations

def setup_playoff_logging(level: str = "INFO") -> None:
    """
    Configure logging for playoff system.

    Args:
        level: Log level for playoff modules

    Example:
        >>> setup_playoff_logging(level="DEBUG")
    """
    configure_module_logger("playoff_system", level=level)
    configure_module_logger("playoff_system.playoff_controller", level=level)
    configure_module_logger("playoff_system.playoff_scheduler", level=level)
    configure_module_logger("playoff_system.seeding", level=level)


def setup_database_logging(level: str = "WARNING") -> None:
    """
    Configure logging for database operations.

    Database operations are typically verbose, so default to WARNING.

    Args:
        level: Log level for database modules
    """
    configure_module_logger("database", level=level)
    configure_module_logger("database.api", level=level)
    configure_module_logger("database.connection", level=level)


def setup_calendar_logging(level: str = "INFO") -> None:
    """
    Configure logging for calendar system.

    Args:
        level: Log level for calendar modules
    """
    configure_module_logger("calendar", level=level)
    configure_module_logger("calendar.calendar_manager", level=level)
    configure_module_logger("calendar.event_manager", level=level)


# Quick setup presets

def setup_production_logging(log_dir: str = "logs") -> None:
    """
    Setup logging for production environment.

    Configuration:
    - Level: INFO
    - Console: No
    - File: Yes
    - Rotating files with 10MB limit
    """
    setup_logging(
        level="INFO",
        log_dir=log_dir,
        enable_console=False,
        enable_file=True,
        format_style="simple"
    )


def setup_development_logging(log_dir: str = "logs") -> None:
    """
    Setup logging for development environment.

    Configuration:
    - Level: DEBUG
    - Console: Yes (colored)
    - File: Yes
    - Detailed format with file/line numbers
    """
    setup_logging(
        level="DEBUG",
        log_dir=log_dir,
        enable_console=True,
        enable_file=True,
        format_style="detailed"
    )


def setup_testing_logging() -> None:
    """
    Setup logging for testing environment.

    Configuration:
    - Level: WARNING
    - Console: Yes
    - File: No
    - Minimal output to avoid cluttering test output
    """
    setup_logging(
        level="WARNING",
        log_dir="logs",
        enable_console=True,
        enable_file=False,
        format_style="simple"
    )


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("Logging Configuration Examples")
    print("=" * 80)

    # Example 1: Basic setup
    print("\n1. Basic Logging Setup:")
    setup_development_logging(log_dir="example_logs")

    logger = get_logger(__name__)
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    # Example 2: Exception logging
    print("\n" + "=" * 80)
    print("\n2. Exception Logging:")

    try:
        result = 1 / 0
    except Exception as e:
        log_exception(
            logger,
            e,
            context={
                "dynasty_id": "test_dynasty",
                "operation": "calculate_standings"
            }
        )

    # Example 3: Log context
    print("\n" + "=" * 80)
    print("\n3. Temporary Log Level:")

    logger.setLevel(logging.INFO)
    logger.debug("This won't be logged (level=INFO)")

    with LogContext(logger, "DEBUG"):
        logger.debug("This WILL be logged (temporary DEBUG level)")

    logger.debug("This won't be logged again (back to INFO)")

    # Example 4: Module-specific logging
    print("\n" + "=" * 80)
    print("\n4. Module-Specific Logging:")

    setup_playoff_logging(level="DEBUG")
    playoff_logger = get_logger("playoff_system.playoff_controller")
    playoff_logger.debug("Playoff debug message (DEBUG enabled)")

    setup_database_logging(level="WARNING")
    db_logger = get_logger("database.api")
    db_logger.info("Database info message (won't be logged - WARNING level)")
    db_logger.warning("Database warning message (will be logged)")

    print("\n" + "=" * 80)
    print("\nLogging configuration examples completed!")
    print(f"Check 'example_logs/' directory for generated log files")
