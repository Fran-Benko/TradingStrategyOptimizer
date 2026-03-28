"""
Logging utilities for the trading system.

Provides comprehensive logging capabilities including:
- Configurable log levels
- Colored console output for terminals
- File rotation with size limits
- Context manager for temporary log level changes
"""

import logging
import os
import sys
import threading
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from logging.handlers import RotatingFileHandler
from typing import Dict, Generator, Optional, Union


class LogLevel(Enum):
    """Available log levels."""
    
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    
    @classmethod
    def from_string(cls, level: str) -> "LogLevel":
        """
        Convert string to LogLevel.
        
        Args:
            level: String representation of log level
            
        Returns:
            Corresponding LogLevel enum value
            
        Example:
            >>> LogLevel.from_string("DEBUG")
            <LogLevel.DEBUG: 10>
        """
        level_upper = level.upper()
        for member in cls:
            if member.name == level_upper:
                return member
        raise ValueError(f"Invalid log level: {level}. Must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL")


class ColoredFormatter(logging.Formatter):
    """
    Colored log formatter for terminal output.
    
    Adds ANSI color codes to log messages based on log level for better
    readability in terminal environments.
    """
    
    # ANSI color codes
    COLORS: Dict[int, str] = {
        logging.DEBUG: "\033[36m",      # Cyan
        logging.INFO: "\033[32m",       # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",      # Red
        logging.CRITICAL: "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None) -> None:
        """
        Initialize the colored formatter.
        
        Args:
            fmt: Log message format string
            datefmt: Date/time format string
        """
        super().__init__(fmt, datefmt)
        self._is_tty = sys.stdout.isatty() if hasattr(sys.stdout, "isatty") else False
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with colors if output is a terminal.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log message
        """
        if self._is_tty and record.levelno in self.COLORS:
            color = self.COLORS[record.levelno]
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class RotatingLogHandler(RotatingFileHandler):
    """
    Custom rotating file handler with additional features.
    
    Provides automatic rotation of log files when they reach a maximum size,
    keeping a specified number of backup files.
    """
    
    def __init__(
        self,
        filename: str,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5,
        encoding: str = "utf-8",
    ) -> None:
        """
        Initialize the rotating log handler.
        
        Args:
            filename: Path to the log file
            max_bytes: Maximum size of each log file before rotation
            backup_count: Number of backup files to keep
            encoding: File encoding
        """
        # Ensure directory exists
        log_dir = os.path.dirname(filename)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        super().__init__(
            filename=filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=encoding,
        )


# Global logging configuration state
_loggers: Dict[str, logging.Logger] = {}
_logging_lock = threading.Lock()
_global_configured = False


def setup_logging(
    level: Union[str, LogLevel, int] = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    format_string: Optional[str] = None,
    date_format: Optional[str] = None,
    use_colors: bool = True,
) -> None:
    """
    Configure the root logger for the trading system.
    
    Sets up logging with console and optional file output, including rotation.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file for file output
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        format_string: Custom format string for log messages
        date_format: Custom date/time format
        use_colors: Whether to use colored output for console
        
    Example:
        >>> setup_logging(level="DEBUG", log_file="logs/trading.log")
        >>> logger = get_logger(__name__)
        >>> logger.info("System initialized")
    """
    global _global_configured
    
    # Convert level to int if needed
    if isinstance(level, LogLevel):
        level_int = level.value
    elif isinstance(level, str):
        level_int = LogLevel.from_string(level).value
    else:
        level_int = level
    
    # Default format strings
    if format_string is None:
        format_string = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    if date_format is None:
        date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configure root logger
    root_logger = logging.getLogger("trading_system")
    root_logger.setLevel(level_int)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level_int)
    
    if use_colors:
        console_formatter = ColoredFormatter(format_string, date_format)
    else:
        console_formatter = logging.Formatter(format_string, date_format)
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        file_handler = RotatingLogHandler(
            filename=log_file,
            max_bytes=max_bytes,
            backup_count=backup_count,
        )
        file_handler.setLevel(level_int)
        file_formatter = logging.Formatter(format_string, date_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    _global_configured = True


def get_logger(name: str, level: Optional[Union[str, LogLevel, int]] = None) -> logging.Logger:
    """
    Get or create a logger for the specified name.
    
    Creates a logger that is a child of the trading_system logger,
    enabling consistent naming and configuration.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
        level: Optional log level override for this logger
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Debug message")
        >>> logger.info("Info message")
        >>> logger.warning("Warning message")
        >>> logger.error("Error message")
    """
    global _loggers, _global_configured
    
    # Ensure global logging is configured
    if not _global_configured:
        setup_logging()
    
    # Create full logger name under trading_system hierarchy
    full_name = f"trading_system.{name}" if not name.startswith("trading_system.") else name
    
    with _logging_lock:
        if full_name not in _loggers:
            logger = logging.getLogger(full_name)
            _loggers[full_name] = logger
            
            # Set level if specified
            if level is not None:
                if isinstance(level, LogLevel):
                    logger.setLevel(level.value)
                elif isinstance(level, str):
                    logger.setLevel(LogLevel.from_string(level).value)
                else:
                    logger.setLevel(level)
        
        return _loggers[full_name]


class TemporaryLogLevel:
    """
    Context manager for temporarily changing log levels.
    
    Allows changing the log level of one or more loggers within a context
    block, automatically restoring the original level on exit.
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.setLevel("WARNING")
        >>> with TemporaryLogLevel(logger, "DEBUG"):
        ...     logger.debug("This will be logged")
        ... logger.debug("This won't be logged")
    """
    
    def __init__(
        self,
        *loggers: Union[str, logging.Logger],
        level: Union[str, LogLevel, int] = "DEBUG"
    ) -> None:
        """
        Initialize the context manager.
        
        Args:
            *loggers: Logger instances or names to temporarily modify
            level: Temporary log level to set
        """
        self._loggers: list[logging.Logger] = []
        self._original_levels: Dict[logging.Logger, int] = {}
        self._temp_level: int
        
        # Convert level
        if isinstance(level, LogLevel):
            self._temp_level = level.value
        elif isinstance(level, str):
            self._temp_level = LogLevel.from_string(level).value
        else:
            self._temp_level = level
        
        # Convert string names to Logger instances
        for logger in loggers:
            if isinstance(logger, str):
                self._loggers.append(logging.getLogger(logger))
            else:
                self._loggers.append(logger)
    
    def __enter__(self) -> "TemporaryLogLevel":
        """Enter the context and apply temporary log level."""
        for logger in self._loggers:
            self._original_levels[logger] = logger.level
            logger.setLevel(self._temp_level)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context and restore original log levels."""
        for logger in self._loggers:
            logger.setLevel(self._original_levels.get(logger, logging.NOTSET))


@contextmanager
def log_context(
    name: str,
    level: Union[str, LogLevel, int] = "DEBUG",
    log_file: Optional[str] = None,
) -> Generator[logging.Logger, None, None]:
    """
    Context manager for creating a temporary logger with custom configuration.
    
    Creates a logger for a specific context (e.g., a function, a block of code)
    with its own configuration, automatically cleaning up after use.
    
    Args:
        name: Logger name
        level: Log level for this context
        log_file: Optional dedicated log file for this context
        
    Yields:
        Configured logger instance
        
    Example:
        >>> with log_context("data_fetch", "DEBUG") as logger:
        ...     logger.debug("Starting fetch")
        ...     # ... code ...
        ...     logger.debug("Fetch complete")
    """
    logger = logging.getLogger(name)
    
    # Store original state
    original_level = logger.level
    original_handlers = logger.handlers[:]
    
    # Configure for context
    if isinstance(level, LogLevel):
        logger.setLevel(level.value)
    elif isinstance(level, str):
        logger.setLevel(LogLevel.from_string(level).value)
    else:
        logger.setLevel(level)
    
    # Add file handler if specified
    temp_file_handler = None
    if log_file:
        temp_file_handler = RotatingLogHandler(log_file)
        temp_file_handler.setFormatter(
            ColoredFormatter("%(asctime)s | %(levelname)-8s | %(message)s")
        )
        logger.addHandler(temp_file_handler)
    
    try:
        yield logger
    finally:
        # Restore original state
        logger.setLevel(original_level)
        logger.handlers = original_handlers
        if temp_file_handler:
            logger.removeHandler(temp_file_handler)
            temp_file_handler.close()


def set_level(level: Union[str, LogLevel, int], logger_name: Optional[str] = None) -> None:
    """
    Set the log level for a logger or the root logger.
    
    Args:
        level: Log level to set
        logger_name: Optional logger name (None for root logger)
        
    Example:
        >>> set_level("DEBUG")  # Set root logger
        >>> set_level("INFO", "trading_system.data")
    """
    if isinstance(level, LogLevel):
        level_int = level.value
    elif isinstance(level, str):
        level_int = LogLevel.from_string(level).value
    else:
        level_int = level
    
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger("trading_system")
    
    logger.setLevel(level_int)


def add_file_handler(
    filename: str,
    level: Union[str, LogLevel, int] = "INFO",
    format_string: Optional[str] = None,
) -> RotatingLogHandler:
    """
    Add a file handler to the root logger or a specific logger.
    
    Args:
        filename: Path to the log file
        level: Log level for this handler
        format_string: Optional custom format string
        
    Returns:
        The created RotatingLogHandler instance
        
    Example:
        >>> handler = add_file_handler("logs/trading.log")
    """
    if isinstance(level, LogLevel):
        level_int = level.value
    elif isinstance(level, str):
        level_int = LogLevel.from_string(level).value
    else:
        level_int = level
    
    handler = RotatingLogHandler(filename)
    handler.setLevel(level_int)
    
    if format_string:
        handler.setFormatter(logging.Formatter(format_string))
    
    root_logger = logging.getLogger("trading_system")
    root_logger.addHandler(handler)
    
    return handler
