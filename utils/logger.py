"""
Structured logging configuration for R&D Tax Credit Automation Agent.

This module provides centralized logging infrastructure with:
- Daily log rotation with 30-day retention
- Separate loggers for each agent (data_ingestion, qualification, audit_trail)
- File and console handlers
- Structured log formatting
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


# Define log directory
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Define log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class AgentLogger:
    """
    Centralized logging manager for the R&D Tax Credit Automation Agent.
    
    Provides structured logging with file rotation and separate loggers
    for each agent component.
    """
    
    _initialized = False
    _loggers = {}
    
    @classmethod
    def initialize(cls, log_level: str = "INFO") -> None:
        """
        Initialize the logging infrastructure.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if cls._initialized:
            return
        
        # Convert log level string to logging constant
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # Remove any existing handlers
        root_logger.handlers.clear()
        
        # Create formatters
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        
        # Create file handler with daily rotation
        log_filename = LOG_DIR / f"agent_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_filename,
            when="midnight",
            interval=1,
            backupCount=30,  # Keep 30 days of logs
            encoding="utf-8"
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        file_handler.suffix = "%Y%m%d"
        
        # Create console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        
        # Add handlers to root logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        cls._initialized = True
        
        # Log initialization
        root_logger.info("Logging infrastructure initialized")
        root_logger.info(f"Log level: {log_level.upper()}")
        root_logger.info(f"Log directory: {LOG_DIR}")
        root_logger.info(f"Log file: {log_filename}")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get or create a logger with the specified name.
        
        Args:
            name: Logger name (e.g., 'agents.data_ingestion')
        
        Returns:
            Logger instance
        """
        if not cls._initialized:
            cls.initialize()
        
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        
        return cls._loggers[name]
    
    @classmethod
    def get_data_ingestion_logger(cls) -> logging.Logger:
        """Get logger for Data Ingestion Agent."""
        return cls.get_logger("agents.data_ingestion")
    
    @classmethod
    def get_qualification_logger(cls) -> logging.Logger:
        """Get logger for Qualification Agent."""
        return cls.get_logger("agents.qualification")
    
    @classmethod
    def get_audit_trail_logger(cls) -> logging.Logger:
        """Get logger for Audit Trail Agent."""
        return cls.get_logger("agents.audit_trail")
    
    @classmethod
    def get_tool_logger(cls, tool_name: str) -> logging.Logger:
        """
        Get logger for a specific tool.
        
        Args:
            tool_name: Name of the tool (e.g., 'api_connectors', 'rd_knowledge_tool')
        
        Returns:
            Logger instance
        """
        return cls.get_logger(f"tools.{tool_name}")
    
    @classmethod
    def cleanup_old_logs(cls, days: int = 30) -> int:
        """
        Clean up log files older than specified days.
        
        Args:
            days: Number of days to retain logs
        
        Returns:
            Number of files deleted
        """
        if not LOG_DIR.exists():
            return 0
        
        deleted_count = 0
        current_time = datetime.now().timestamp()
        max_age_seconds = days * 24 * 60 * 60
        
        for log_file in LOG_DIR.glob("agent_*.log*"):
            file_age = current_time - log_file.stat().st_mtime
            if file_age > max_age_seconds:
                try:
                    log_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    logging.error(f"Failed to delete old log file {log_file}: {e}")
        
        return deleted_count


# Convenience functions for getting agent-specific loggers
def get_data_ingestion_logger() -> logging.Logger:
    """Get logger for Data Ingestion Agent."""
    return AgentLogger.get_data_ingestion_logger()


def get_qualification_logger() -> logging.Logger:
    """Get logger for Qualification Agent."""
    return AgentLogger.get_qualification_logger()


def get_audit_trail_logger() -> logging.Logger:
    """Get logger for Audit Trail Agent."""
    return AgentLogger.get_audit_trail_logger()


def get_tool_logger(tool_name: str) -> logging.Logger:
    """
    Get logger for a specific tool.
    
    Args:
        tool_name: Name of the tool
    
    Returns:
        Logger instance
    """
    return AgentLogger.get_tool_logger(tool_name)


# Initialize logging on module import
AgentLogger.initialize()
