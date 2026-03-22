"""
Logging and output formatting utilities for testing module.

Provides structured logging with configurable verbosity levels and
consistent output formatting.
"""

import logging
import sys
from enum import Enum
from typing import Optional


class VerbosityLevel(Enum):
    """Verbosity levels for test output."""
    QUIET = 0    # Only errors and final results
    NORMAL = 1   # Key progress and results
    VERBOSE = 2  # Detailed progress
    DEBUG = 3    # All debug information


class TestLogger:
    """
    Centralized logger for testing module with verbosity control.
    """
    
    def __init__(self, name: str = "testing", verbosity: VerbosityLevel = VerbosityLevel.NORMAL):
        """
        Initialize logger with specified verbosity.
        
        Args:
            name: Logger name
            verbosity: Verbosity level
        """
        self.logger = logging.getLogger(name)
        self.verbosity = verbosity
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure logging handlers and formatters."""
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._get_log_level())
        
        # Format: simple for normal, detailed for debug
        if self.verbosity == VerbosityLevel.DEBUG:
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%H:%M:%S'
            )
        else:
            formatter = logging.Formatter('%(message)s')
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _get_log_level(self) -> int:
        """Map verbosity level to logging level."""
        mapping = {
            VerbosityLevel.QUIET: logging.WARNING,
            VerbosityLevel.NORMAL: logging.INFO,
            VerbosityLevel.VERBOSE: logging.INFO,
            VerbosityLevel.DEBUG: logging.DEBUG,
        }
        return mapping[self.verbosity]
    
    def set_verbosity(self, verbosity: VerbosityLevel):
        """Update verbosity level."""
        self.verbosity = verbosity
        self._setup_logger()
    
    def debug(self, msg: str):
        """Log debug message (only in DEBUG mode)."""
        if self.verbosity == VerbosityLevel.DEBUG:
            self.logger.debug(msg)
    
    def info(self, msg: str):
        """Log info message (NORMAL, VERBOSE, DEBUG)."""
        if self.verbosity.value >= VerbosityLevel.NORMAL.value:
            self.logger.info(msg)
    
    def verbose(self, msg: str):
        """Log verbose message (VERBOSE, DEBUG)."""
        if self.verbosity.value >= VerbosityLevel.VERBOSE.value:
            self.logger.info(msg)
    
    def warning(self, msg: str):
        """Log warning message (all levels)."""
        self.logger.warning(msg)
    
    def error(self, msg: str):
        """Log error message (all levels)."""
        self.logger.error(msg)
    
    def section(self, title: str, width: int = 80):
        """Print section header."""
        if self.verbosity.value >= VerbosityLevel.NORMAL.value:
            self.logger.info("\n" + "=" * width)
            self.logger.info(title)
            self.logger.info("=" * width)
    
    def subsection(self, title: str, width: int = 80):
        """Print subsection header."""
        if self.verbosity.value >= VerbosityLevel.VERBOSE.value:
            self.logger.info("\n" + "-" * width)
            self.logger.info(title)
            self.logger.info("-" * width)
    
    def progress(self, current: int, total: int, prefix: str = "Progress"):
        """Log progress update."""
        if self.verbosity.value >= VerbosityLevel.NORMAL.value:
            self.logger.info(f"{prefix}: {current}/{total}")


class OutputFormatter:
    """Utilities for formatting test output consistently."""
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable form."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}min"
        else:
            return f"{seconds/3600:.1f}h"
    
    @staticmethod
    def format_percentage(value: float, total: float) -> str:
        """Format value/total as percentage."""
        if total == 0:
            return "0.0%"
        return f"{value/total*100:.1f}%"
    
    @staticmethod
    def format_ratio(numerator: float, denominator: float) -> str:
        """Format ratio with proper handling of division by zero."""
        if denominator == 0 or denominator is None:
            return "N/A"
        return f"{numerator/denominator:.2f}x"
    
    @staticmethod
    def format_metric(name: str, value, unit: Optional[str] = None) -> str:
        """Format metric for display."""
        if value is None:
            return f"{name}: N/A"
        
        if isinstance(value, float):
            formatted_value = f"{value:.2f}"
        else:
            formatted_value = str(value)
        
        if unit:
            return f"{name}: {formatted_value}{unit}"
        return f"{name}: {formatted_value}"
    
    @staticmethod
    def format_comparison(name: str, value1, value2, match: bool) -> str:
        """Format comparison between two values."""
        status = "MATCH" if match else "MISMATCH"
        return f"{name}: {value1} vs {value2} [{status}]"
    
    @staticmethod
    def format_status_indicator(success: bool) -> str:
        """Format success/failure indicator."""
        return "PASS" if success else "FAIL"


def setup_file_logging(log_file_path: str, level: int = logging.DEBUG):
    """
    Add file handler to root logger for persistent logging.
    
    Args:
        log_file_path: Path to log file
        level: Logging level for file output
    """
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add to root logger
    logging.getLogger().addHandler(file_handler)


# Global logger instance (can be reconfigured)
_default_logger: Optional[TestLogger] = None


def get_logger(name: str = "testing") -> TestLogger:
    """Get or create the default logger instance."""
    global _default_logger
    if _default_logger is None:
        _default_logger = TestLogger(name)
    return _default_logger


def set_verbosity(level: VerbosityLevel):
    """Set global verbosity level."""
    logger = get_logger()
    logger.set_verbosity(level)
