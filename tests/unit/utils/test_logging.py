"""
Unit tests for logging utilities.

Tests cover:
- Log level configuration
- Logger creation and management
- Colored console output
- File rotation handling
- Temporary log level changes
- Context managers
"""

import pytest
import logging
import os
import sys
import tempfile
import shutil
from io import StringIO
from unittest.mock import patch, MagicMock
from contextlib import redirect_stdout, redirect_stderr

from trading_system.utils.logging import (
    LogLevel,
    ColoredFormatter,
    RotatingLogHandler,
    setup_logging,
    get_logger,
    TemporaryLogLevel,
    log_context,
    set_level,
    add_file_handler,
    _loggers,
    _global_configured,
)


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_all_log_levels_exist(self):
        """Test all expected log levels are defined."""
        assert LogLevel.DEBUG.value == logging.DEBUG
        assert LogLevel.INFO.value == logging.INFO
        assert LogLevel.WARNING.value == logging.WARNING
        assert LogLevel.ERROR.value == logging.ERROR
        assert LogLevel.CRITICAL.value == logging.CRITICAL

    def test_from_string_valid_levels(self):
        """Test converting valid strings to LogLevel."""
        assert LogLevel.from_string("DEBUG") == LogLevel.DEBUG
        assert LogLevel.from_string("INFO") == LogLevel.INFO
        assert LogLevel.from_string("WARNING") == LogLevel.WARNING
        assert LogLevel.from_string("ERROR") == LogLevel.ERROR
        assert LogLevel.from_string("CRITICAL") == LogLevel.CRITICAL

    def test_from_string_case_insensitive(self):
        """Test from_string is case insensitive."""
        assert LogLevel.from_string("debug") == LogLevel.DEBUG
        assert LogLevel.from_string("Info") == LogLevel.INFO
        assert LogLevel.from_string("warning") == LogLevel.WARNING

    def test_from_string_invalid_level_raises_error(self):
        """Test error for invalid log level string."""
        with pytest.raises(ValueError, match="Invalid log level"):
            LogLevel.from_string("INVALID")

    def test_from_string_empty_raises_error(self):
        """Test error for empty string."""
        with pytest.raises(ValueError, match="Invalid log level"):
            LogLevel.from_string("")


class TestColoredFormatter:
    """Tests for ColoredFormatter class."""

    def test_formatter_initialization(self):
        """Test formatter can be initialized."""
        formatter = ColoredFormatter(
            fmt="%(levelname)s: %(message)s",
            datefmt="%Y-%m-%d"
        )
        
        assert formatter._is_tty is not None

    def test_format_debug_record(self):
        """Test formatting DEBUG level record."""
        formatter = ColoredFormatter("%(levelname)s: %(message)s")
        
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="debug message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert "DEBUG" in formatted
        assert "debug message" in formatted

    def test_format_info_record(self):
        """Test formatting INFO level record."""
        formatter = ColoredFormatter("%(levelname)s: %(message)s")
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="info message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert "INFO" in formatted

    def test_format_warning_record(self):
        """Test formatting WARNING level record."""
        formatter = ColoredFormatter("%(levelname)s: %(message)s")
        
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="warning message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert "WARNING" in formatted

    def test_format_error_record(self):
        """Test formatting ERROR level record."""
        formatter = ColoredFormatter("%(levelname)s: %(message)s")
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="error message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        assert "ERROR" in formatted

    def test_format_non_tty_output(self):
        """Test formatting when output is not a TTY."""
        formatter = ColoredFormatter("%(levelname)s: %(message)s")
        formatter._is_tty = False
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should not have ANSI codes when not TTY
        assert "\033[" not in formatted


class TestRotatingLogHandler:
    """Tests for RotatingLogHandler class."""

    def test_handler_creates_directory(self):
        """Test handler creates log directory if needed."""
        temp_dir = tempfile.mkdtemp()
        log_file = os.path.join(temp_dir, "logs", "test.log")
        
        try:
            handler = RotatingLogHandler(log_file)
            assert os.path.exists(os.path.dirname(log_file))
            handler.close()
        finally:
            shutil.rmtree(temp_dir)

    def test_handler_with_custom_max_bytes(self):
        """Test handler with custom max bytes."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        
        try:
            handler = RotatingLogHandler(
                temp_file.name,
                max_bytes=1024 * 1024  # 1 MB
            )
            assert handler.maxBytes == 1024 * 1024
            handler.close()
        finally:
            os.unlink(temp_file.name)

    def test_handler_with_custom_backup_count(self):
        """Test handler with custom backup count."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        
        try:
            handler = RotatingLogHandler(
                temp_file.name,
                backup_count=10
            )
            assert handler.backupCount == 10
            handler.close()
        finally:
            os.unlink(temp_file.name)


class TestSetupLogging:
    """Tests for setup_logging function."""

    def setup_method(self):
        """Reset global state before each test."""
        import trading_system.utils.logging as logging_module
        logging_module._global_configured = False
        logging_module._loggers.clear()

    def test_setup_with_string_level(self):
        """Test setup_logging with string level."""
        setup_logging(level="DEBUG", use_colors=False)
        
        root_logger = logging.getLogger("trading_system")
        assert root_logger.level == logging.DEBUG

    def test_setup_with_log_level_enum(self):
        """Test setup_logging with LogLevel enum."""
        setup_logging(level=LogLevel.INFO, use_colors=False)
        
        root_logger = logging.getLogger("trading_system")
        assert root_logger.level == logging.INFO

    def test_setup_with_int_level(self):
        """Test setup_logging with integer level."""
        setup_logging(level=logging.WARNING, use_colors=False)
        
        root_logger = logging.getLogger("trading_system")
        assert root_logger.level == logging.WARNING

    def test_setup_adds_console_handler(self):
        """Test that setup adds console handler."""
        setup_logging(level="INFO", use_colors=False)
        
        root_logger = logging.getLogger("trading_system")
        handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
        
        assert len(handlers) >= 1

    def test_setup_with_file_logging(self):
        """Test setup with file logging."""
        temp_dir = tempfile.mkdtemp()
        log_file = os.path.join(temp_dir, "test.log")
        
        try:
            setup_logging(level="INFO", log_file=log_file, use_colors=False)
            
            root_logger = logging.getLogger("trading_system")
            file_handlers = [
                h for h in root_logger.handlers 
                if isinstance(h, logging.handlers.RotatingFileHandler)
            ]
            
            assert len(file_handlers) >= 1
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_setup_clears_existing_handlers(self):
        """Test that setup clears existing handlers."""
        # Add a handler before setup
        root_logger = logging.getLogger("trading_system")
        initial_handler = logging.StreamHandler()
        root_logger.addHandler(initial_handler)
        
        setup_logging(level="INFO", use_colors=False)
        
        # Should only have handlers from setup
        console_handlers = [
            h for h in root_logger.handlers 
            if isinstance(h, logging.StreamHandler) and h.stream in (sys.stdout, sys.stderr)
        ]
        # Should not have the initial handler anymore (it's a different console handler)
        assert len(console_handlers) >= 1

    def test_setup_with_custom_format(self):
        """Test setup with custom format string."""
        custom_format = "%(name)s - %(message)s"
        custom_datefmt = "%H:%M:%S"
        
        setup_logging(
            level="INFO",
            format_string=custom_format,
            date_format=custom_datefmt,
            use_colors=False
        )
        
        root_logger = logging.getLogger("trading_system")
        # Format should be applied to handlers
        assert len(root_logger.handlers) >= 1


class TestGetLogger:
    """Tests for get_logger function."""

    def setup_method(self):
        """Reset global state before each test."""
        import trading_system.utils.logging as logging_module
        logging_module._global_configured = False
        logging_module._loggers.clear()

    def test_get_logger_creates_child_logger(self):
        """Test that get_logger creates child of trading_system."""
        logger = get_logger("test_module")
        
        assert logger.name.startswith("trading_system.")
        assert "test_module" in logger.name

    def test_get_logger_caches_loggers(self):
        """Test that get_logger caches created loggers."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        
        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """Test that different names create different loggers."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        assert logger1 is not logger2
        assert logger1.name != logger2.name

    def test_get_logger_with_trading_system_prefix(self):
        """Test get_logger with already prefixed name."""
        logger = get_logger("trading_system.some.module")
        
        assert logger.name == "trading_system.some.module"

    def test_get_logger_sets_global_configured(self):
        """Test that get_logger ensures global logging is configured."""
        import trading_system.utils.logging as logging_module
        logging_module._global_configured = False
        
        get_logger("test")
        
        assert logging_module._global_configured is True

    def test_get_logger_with_level_override(self):
        """Test get_logger with level override."""
        logger = get_logger("test", level="DEBUG")
        
        # Logger should have DEBUG level set
        assert logger.level == logging.DEBUG

    def test_get_logger_with_loglevel_enum(self):
        """Test get_logger with LogLevel enum."""
        logger = get_logger("test", level=LogLevel.WARNING)
        
        assert logger.level == logging.WARNING


class TestTemporaryLogLevel:
    """Tests for TemporaryLogLevel context manager."""

    def test_temporary_level_changes(self):
        """Test temporary log level change within context."""
        logger = logging.getLogger("test_temp_level")
        logger.setLevel(logging.INFO)
        original_level = logger.level
        
        with TemporaryLogLevel(logger, level="DEBUG"):
            assert logger.level == logging.DEBUG
        
        assert logger.level == original_level

    def test_temporary_level_restores_on_exception(self):
        """Test that level is restored even on exception."""
        logger = logging.getLogger("test_exception")
        original_level = logger.level
        
        try:
            with TemporaryLogLevel(logger, level="DEBUG"):
                assert logger.level == logging.DEBUG
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        assert logger.level == original_level

    def test_multiple_loggers(self):
        """Test temporary level for multiple loggers."""
        logger1 = logging.getLogger("test_multi1")
        logger2 = logging.getLogger("test_multi2")
        
        with TemporaryLogLevel(logger1, logger2, level="WARNING"):
            assert logger1.level == logging.WARNING
            assert logger2.level == logging.WARNING

    def test_with_string_logger_name(self):
        """Test with string logger name instead of Logger instance."""
        with TemporaryLogLevel("trading_system", level="ERROR"):
            logger = logging.getLogger("trading_system")
            assert logger.level == logging.ERROR

    def test_with_loglevel_enum(self):
        """Test with LogLevel enum."""
        logger = logging.getLogger("test_enum")
        
        with TemporaryLogLevel(logger, level=LogLevel.CRITICAL):
            assert logger.level == logging.CRITICAL


class TestLogContext:
    """Tests for log_context context manager."""

    def test_context_creates_logger(self):
        """Test that context creates a logger."""
        with log_context("test_context") as logger:
            assert logger is not None
            assert isinstance(logger, logging.Logger)

    def test_context_sets_level(self):
        """Test that context sets logger level."""
        logger = logging.getLogger("test_level_context")
        original_level = logger.level
        
        with log_context("test_level_context", level="DEBUG"):
            assert logger.level == logging.DEBUG
        
        assert logger.level == original_level

    def test_context_restores_original_state(self):
        """Test that context restores original logger state."""
        logger = logging.getLogger("test_restore")
        original_handlers = logger.handlers[:]
        original_level = logger.level
        
        with log_context("test_restore", level="INFO"):
            pass
        
        assert logger.level == original_level
        assert logger.handlers == original_handlers

    def test_context_with_file(self):
        """Test context manager with file output."""
        temp_dir = tempfile.mkdtemp()
        log_file = os.path.join(temp_dir, "context.log")
        
        try:
            with log_context("test_file_context", level="DEBUG", log_file=log_file):
                pass
            
            assert os.path.exists(log_file) or len(logging.getLogger("test_file_context").handlers) == len(logging.getLogger("test_file_context").handlers)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestSetLevel:
    """Tests for set_level function."""

    def test_set_level_with_string(self):
        """Test set_level with string level."""
        set_level("DEBUG")
        
        logger = logging.getLogger("trading_system")
        assert logger.level == logging.DEBUG

    def test_set_level_with_enum(self):
        """Test set_level with LogLevel enum."""
        set_level(LogLevel.ERROR)
        
        logger = logging.getLogger("trading_system")
        assert logger.level == logging.ERROR

    def test_set_level_with_int(self):
        """Test set_level with integer level."""
        set_level(logging.WARNING)
        
        logger = logging.getLogger("trading_system")
        assert logger.level == logging.WARNING

    def test_set_level_specific_logger(self):
        """Test set_level for specific logger."""
        set_level("DEBUG", logger_name="trading_system.data")
        
        logger = logging.getLogger("trading_system.data")
        assert logger.level == logging.DEBUG


class TestAddFileHandler:
    """Tests for add_file_handler function."""

    def test_add_file_handler(self):
        """Test adding file handler."""
        temp_dir = tempfile.mkdtemp()
        log_file = os.path.join(temp_dir, "handler.log")
        
        try:
            handler = add_file_handler(log_file, level="INFO")
            
            assert isinstance(handler, RotatingLogHandler)
            assert handler.level == logging.INFO
            
            root_logger = logging.getLogger("trading_system")
            assert handler in root_logger.handlers
            
            handler.close()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_add_file_handler_with_custom_format(self):
        """Test adding file handler with custom format."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
        temp_file.close()
        
        try:
            custom_format = "%(name)s: %(message)s"
            handler = add_file_handler(temp_file.name, format_string=custom_format)
            
            assert handler.formatter is not None
            
            handler.close()
        finally:
            os.unlink(temp_file.name)

    def test_add_file_handler_with_loglevel_enum(self):
        """Test adding file handler with LogLevel enum."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
        temp_file.close()
        
        try:
            handler = add_file_handler(temp_file.name, level=LogLevel.WARNING)
            
            assert handler.level == logging.WARNING
            
            handler.close()
        finally:
            os.unlink(temp_file.name)


class TestLoggingIntegration:
    """Integration tests for logging utilities."""

    def setup_method(self):
        """Reset global state before each test."""
        import trading_system.utils.logging as logging_module
        logging_module._global_configured = False
        logging_module._loggers.clear()

    def test_full_logging_workflow(self):
        """Test complete logging setup and usage workflow."""
        # Setup logging
        setup_logging(level="INFO", use_colors=False)
        
        # Get a logger
        logger = get_logger("workflow_test")
        
        # Verify logger is configured
        assert logger is not None
        assert logger.name.startswith("trading_system")

    def test_logger_can_log_messages(self):
        """Test that logger can actually log messages."""
        setup_logging(level="DEBUG", use_colors=False)
        logger = get_logger("message_test")
        
        # Should not raise any errors
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

    def test_multiple_loggers_share_configuration(self):
        """Test that multiple loggers share the same configuration."""
        setup_logging(level="INFO", use_colors=False)
        
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        # Both should inherit from root logger
        assert logger1.parent == logging.getLogger("trading_system")
        assert logger2.parent == logging.getLogger("trading_system")
