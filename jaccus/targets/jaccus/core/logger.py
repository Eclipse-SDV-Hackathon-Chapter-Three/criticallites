"""
Logging utilities for JACCUS system.

This module provides standardized logging functionality with the format:
[timestamp] [level] [module.file]

Classes:
    JaccusLogger: Thread-safe logger with standardized formatting
"""

import datetime
import threading
import os
import inspect
from typing import Optional


class JaccusLogger:
    """
    JACCUS standardized logging system with thread-safe operations.

    Implements logging format: [timestamp] [level] [module.file]

    Attributes:
        log_file (str): Path to log file
        _lock (threading.Lock): Thread synchronization lock
        _initialized (bool): Initialization status
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, log_file: str = "jaccus_run.log"):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_file: str = "jaccus_run.log"):
        """Initialize logger if not already initialized."""
        if not hasattr(self, '_initialized'):
            self.log_file = log_file
            self._lock = threading.Lock()
            self._initialized = True
            self._initialize_log_file()

    def _initialize_log_file(self):
        """Initialize log file with header."""
        try:
            with self._lock:
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"JACCUS RUN LOG - {timestamp}\n")
                    f.write("=" * 80 + "\n\n")
        except Exception as e:
            print(f"Failed to initialize log file: {e}")

    def _get_caller_info(self) -> str:
        """
        Get caller module and file information.

        Returns:
            str: Formatted module.file string
        """
        try:
            # Get the stack frame of the caller (skip _log_message and the actual log method)
            frame = inspect.currentframe()
            for _ in range(3):  # Skip _get_caller_info, _log_message, and the actual log method
                if frame.f_back:
                    frame = frame.f_back
                else:
                    break

            if frame:
                # Get filename without extension
                filename = os.path.basename(frame.f_code.co_filename)
                if filename.endswith('.py'):
                    filename = filename[:-3]

                # Get module name from frame's globals if available
                module_name = frame.f_globals.get('__name__', 'unknown')
                if module_name == '__main__':
                    module_name = filename
                elif '.' in module_name:
                    # Use the last part of the module path
                    module_name = module_name.split('.')[-1]

                return f"{module_name}.{filename}"

        except Exception:
            pass

        return "unknown.unknown"

    def _log_message(self, level: str, message: str, module_file: Optional[str] = None):
        """
        Internal logging method with thread safety.

        Args:
            level (str): Log level (INF, WAR, ERR, EMR)
            message (str): Message to log
            module_file (str, optional): Override module.file detection
        """
        try:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

            # Get caller info if not provided
            if module_file is None:
                module_file = self._get_caller_info()

            # Format: [timestamp] [level] [module.file] message
            log_entry = f"[{timestamp}] [{level}] [{module_file}] {message}\n"

            # Thread-safe file writing
            with self._lock:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
                    f.flush()

        except Exception as e:
            # Fallback to console if file logging fails
            print(f"[{level}] [{module_file or 'logger.logger'}] {message}")
            print(f"[ERR] [logger.logger] Logging error: {e}")

    def info(self, message: str, module_file: Optional[str] = None):
        """
        Log informational message.

        Args:
            message (str): Information message
            module_file (str, optional): Override automatic module.file detection
        """
        self._log_message("INF", message, module_file)

    def warning(self, message: str, module_file: Optional[str] = None):
        """
        Log warning message.

        Args:
            message (str): Warning message
            module_file (str, optional): Override automatic module.file detection
        """
        self._log_message("WAR", message, module_file)

    def error(self, message: str, module_file: Optional[str] = None):
        """
        Log error message.

        Args:
            message (str): Error message
            module_file (str, optional): Override automatic module.file detection
        """
        self._log_message("ERR", message, module_file)

    def emergency(self, message: str, module_file: Optional[str] = None):
        """
        Log emergency message.

        Args:
            message (str): Emergency message
            module_file (str, optional): Override automatic module.file detection
        """
        self._log_message("EMR", message, module_file)

    def debug(self, message: str, module_file: Optional[str] = None):
        """
        Log debug message.

        Args:
            message (str): Debug message
            module_file (str, optional): Override automatic module.file detection
        """
        self._log_message("DBG", message, module_file)


# Global logger instance for easy access
logger = JaccusLogger()

# Convenience functions for global access
def log_info(message: str, module_file: Optional[str] = None):
    """Global info logging function."""
    logger.info(message, module_file)

def log_warning(message: str, module_file: Optional[str] = None):
    """Global warning logging function."""
    logger.warning(message, module_file)

def log_error(message: str, module_file: Optional[str] = None):
    """Global error logging function."""
    logger.error(message, module_file)

def log_emergency(message: str, module_file: Optional[str] = None):
    """Global emergency logging function."""
    logger.emergency(message, module_file)

def log_debug(message: str, module_file: Optional[str] = None):
    """Global debug logging function."""
    logger.debug(message, module_file)
