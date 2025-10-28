"""
Unit tests for setup utilities.

This module tests logger configuration, config loading and validation,
retry decorator, and validation functions to ensure proper setup and
error handling behavior.
"""

import pytest
import logging
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from utils.logger import AgentLogger, get_data_ingestion_logger, get_qualification_logger
from utils.config import Config, ConfigManager, ConfigurationError, get_config
from utils.retry import retry_with_backoff
from utils.validators import validate_date_range, validate_api_key, sanitize_text
from utils.exceptions import ValidationError


class TestAgentLogger:
    """Test suite for AgentLogger configuration and output."""
    
    def setup_method(self):
        """Reset logger state before each test."""
        AgentLogger._initialized = False
        AgentLogger._loggers = {}
        # Clear root logger handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
    
    def test_logger_initialization(self):
        """Test that logger initializes correctly."""
        AgentLogger.initialize(log_level="INFO")
        
        assert AgentLogger._initialized is True
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) >= 2  # File and console handlers
    
    def test_logger_initialization_only_once(self):
        """Test that logger only initializes once."""
        AgentLogger.initialize(log_level="INFO")
        first_init = AgentLogger._initialized
        
        AgentLogger.initialize(log_level="DEBUG")
        second_init = AgentLogger._initialized
        
        assert first_init is True
        assert second_init is True
        # Log level should remain INFO (not changed to DEBUG)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
    
    def test_logger_custom_log_level(self):
        """Test logger with custom log level."""
        AgentLogger.initialize(log_level="DEBUG")
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    def test_get_logger_creates_new_logger(self):
        """Test that get_logger creates a new logger."""
        logger = AgentLogger.get_logger("test.logger")
        
        assert logger is not None
        assert logger.name == "test.logger"
        assert "test.logger" in AgentLogger._loggers
    
    def test_get_logger_returns_cached_logger(self):
        """Test that get_logger returns cached logger."""
        logger1 = AgentLogger.get_logger("test.logger")
        logger2 = AgentLogger.get_logger("test.logger")
        
        assert logger1 is logger2
    
    def test_get_data_ingestion_logger(self):
        """Test getting data ingestion logger."""
        logger = AgentLogger.get_data_ingestion_logger()
        
        assert logger.name == "agents.data_ingestion"
    
    def test_get_qualification_logger(self):
        """Test getting qualification logger."""
        logger = AgentLogger.get_qualification_logger()
        
        assert logger.name == "agents.qualification"
    
    def test_get_audit_trail_logger(self):
        """Test getting audit trail logger."""
        logger = AgentLogger.get_audit_trail_logger()
        
        assert logger.name == "agents.audit_trail"
    
    def test_get_tool_logger(self):
        """Test getting tool logger."""
        logger = AgentLogger.get_tool_logger("api_connectors")
        
        assert logger.name == "tools.api_connectors"
    
    def test_logger_output_to_file(self, tmp_path):
        """Test that logger writes to file."""
        # Create temporary log directory
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        
        with patch('utils.logger.LOG_DIR', log_dir):
            AgentLogger._initialized = False
            AgentLogger.initialize(log_level="INFO")
            
            logger = AgentLogger.get_logger("test.file")
            logger.info("Test message")
            
            # Check that log file was created
            log_files = list(log_dir.glob("agent_*.log"))
            assert len(log_files) > 0
    
    def test_cleanup_old_logs(self, tmp_path):
        """Test cleanup of old log files."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        
        # Create some old log files
        old_file1 = log_dir / "agent_20230101.log"
        old_file2 = log_dir / "agent_20230102.log"
        recent_file = log_dir / f"agent_{datetime.now().strftime('%Y%m%d')}.log"
        
        old_file1.touch()
        old_file2.touch()
        recent_file.touch()
        
        # Set old modification times
        old_time = datetime(2023, 1, 1).timestamp()
        os.utime(old_file1, (old_time, old_time))
        os.utime(old_file2, (old_time, old_time))
        
        with patch('utils.logger.LOG_DIR', log_dir):
            deleted_count = AgentLogger.cleanup_old_logs(days=30)
            
            assert deleted_count == 2
            assert not old_file1.exists()
            assert not old_file2.exists()
            assert recent_file.exists()
    
    def test_convenience_functions(self):
        """Test convenience functions for getting loggers."""
        logger1 = get_data_ingestion_logger()
        logger2 = get_qualification_logger()
        
        assert logger1.name == "agents.data_ingestion"
        assert logger2.name == "agents.qualification"


class TestConfig:
    """Test suite for Config dataclass validation."""
    
    def test_valid_config_creation(self):
        """Test creating a valid config."""
        config = Config(
            openrouter_api_key="sk-test-key-123",
            clockify_api_key="clockify-key-456",
            unified_to_api_key="unified-key-789",
            youcom_api_key="youcom-key-abc",
            thesys_api_key="thesys-key-def",
            clockify_workspace_id="workspace-123",
            unified_to_workspace_id="workspace-456"
        )
        
        assert config.openrouter_api_key == "sk-test-key-123"
        assert config.max_retries == 3
        assert config.log_level == "INFO"
    
    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Missing required configuration"):
            Config(
                openrouter_api_key="",  # Empty key
                clockify_api_key="clockify-key",
                unified_to_api_key="unified-key",
                youcom_api_key="youcom-key",
                thesys_api_key="thesys-key",
                clockify_workspace_id="workspace-123",
                unified_to_workspace_id="workspace-456"
            )
    
    def test_placeholder_api_key_raises_error(self):
        """Test that placeholder API key raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Placeholder values detected"):
            Config(
                openrouter_api_key="your_api_key_here",
                clockify_api_key="clockify-key",
                unified_to_api_key="unified-key",
                youcom_api_key="youcom-key",
                thesys_api_key="thesys-key",
                clockify_workspace_id="workspace-123",
                unified_to_workspace_id="workspace-456"
            )
    
    def test_invalid_confidence_threshold_raises_error(self):
        """Test that invalid confidence threshold raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="must be between 0 and 1"):
            Config(
                openrouter_api_key="sk-test-key",
                clockify_api_key="clockify-key",
                unified_to_api_key="unified-key",
                youcom_api_key="youcom-key",
                thesys_api_key="thesys-key",
                clockify_workspace_id="workspace-123",
                unified_to_workspace_id="workspace-456",
                confidence_threshold_low=1.5  # Invalid
            )
    
    def test_threshold_ordering_validation(self):
        """Test that threshold ordering is validated."""
        with pytest.raises(ConfigurationError, match="must be in ascending order"):
            Config(
                openrouter_api_key="sk-test-key",
                clockify_api_key="clockify-key",
                unified_to_api_key="unified-key",
                youcom_api_key="youcom-key",
                thesys_api_key="thesys-key",
                clockify_workspace_id="workspace-123",
                unified_to_workspace_id="workspace-456",
                confidence_threshold_low=0.9,
                confidence_threshold_medium=0.7,  # Out of order
                confidence_threshold_high=0.95
            )
    
    def test_negative_max_retries_raises_error(self):
        """Test that negative max_retries raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="max_retries must be non-negative"):
            Config(
                openrouter_api_key="sk-test-key",
                clockify_api_key="clockify-key",
                unified_to_api_key="unified-key",
                youcom_api_key="youcom-key",
                thesys_api_key="thesys-key",
                clockify_workspace_id="workspace-123",
                unified_to_workspace_id="workspace-456",
                max_retries=-1
            )
    
    def test_invalid_timeout_raises_error(self):
        """Test that invalid timeout raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="timeout_seconds must be positive"):
            Config(
                openrouter_api_key="sk-test-key",
                clockify_api_key="clockify-key",
                unified_to_api_key="unified-key",
                youcom_api_key="youcom-key",
                thesys_api_key="thesys-key",
                clockify_workspace_id="workspace-123",
                unified_to_workspace_id="workspace-456",
                timeout_seconds=0
            )
    
    def test_invalid_chunk_size_raises_error(self):
        """Test that invalid chunk size raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="chunk_size must be positive"):
            Config(
                openrouter_api_key="sk-test-key",
                clockify_api_key="clockify-key",
                unified_to_api_key="unified-key",
                youcom_api_key="youcom-key",
                thesys_api_key="thesys-key",
                clockify_workspace_id="workspace-123",
                unified_to_workspace_id="workspace-456",
                chunk_size=-10
            )
    
    def test_chunk_overlap_exceeds_size_raises_error(self):
        """Test that chunk overlap >= chunk size raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="chunk_overlap.*must be less than chunk_size"):
            Config(
                openrouter_api_key="sk-test-key",
                clockify_api_key="clockify-key",
                unified_to_api_key="unified-key",
                youcom_api_key="youcom-key",
                thesys_api_key="thesys-key",
                clockify_workspace_id="workspace-123",
                unified_to_workspace_id="workspace-456",
                chunk_size=100,
                chunk_overlap=100
            )
    
    def test_invalid_log_level_raises_error(self):
        """Test that invalid log level raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="log_level must be one of"):
            Config(
                openrouter_api_key="sk-test-key",
                clockify_api_key="clockify-key",
                unified_to_api_key="unified-key",
                youcom_api_key="youcom-key",
                thesys_api_key="thesys-key",
                clockify_workspace_id="workspace-123",
                unified_to_workspace_id="workspace-456",
                log_level="INVALID"
            )
    
    def test_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        config = Config(
            openrouter_api_key="sk-test-key",
            clockify_api_key="clockify-key",
            unified_to_api_key="unified-key",
            youcom_api_key="youcom-key",
            thesys_api_key="thesys-key",
            clockify_workspace_id="workspace-123",
            unified_to_workspace_id="workspace-456",
            knowledge_base_path="custom/path"
        )
        
        assert isinstance(config.knowledge_base_path, Path)
        # Path normalization is platform-specific
        assert config.knowledge_base_path == Path("custom/path")


class TestConfigManager:
    """Test suite for ConfigManager singleton and loading."""
    
    def setup_method(self):
        """Reset ConfigManager state before each test."""
        ConfigManager._instance = None
        ConfigManager._initialized = False
    
    def test_load_config_from_env_file(self, tmp_path):
        """Test loading config from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("""
OPENROUTER_API_KEY=sk-test-key-123
CLOCKIFY_API_KEY=clockify-key-456
UNIFIED_TO_API_KEY=unified-key-789
YOUCOM_API_KEY=youcom-key-abc
THESYS_API_KEY=thesys-key-def
CLOCKIFY_WORKSPACE_ID=workspace-123
UNIFIED_TO_WORKSPACE_ID=workspace-456
LOG_LEVEL=DEBUG
MAX_RETRIES=5
        """)
        
        config = ConfigManager.load_config(env_file=str(env_file))
        
        assert config.openrouter_api_key == "sk-test-key-123"
        assert config.log_level == "DEBUG"
        assert config.max_retries == 5
    
    def test_singleton_pattern(self, tmp_path):
        """Test that ConfigManager returns same instance."""
        env_file = tmp_path / ".env"
        env_file.write_text("""
OPENROUTER_API_KEY=sk-test-key
CLOCKIFY_API_KEY=clockify-key
UNIFIED_TO_API_KEY=unified-key
YOUCOM_API_KEY=youcom-key
THESYS_API_KEY=thesys-key
CLOCKIFY_WORKSPACE_ID=workspace-123
UNIFIED_TO_WORKSPACE_ID=workspace-456
        """)
        
        config1 = ConfigManager.load_config(env_file=str(env_file))
        config2 = ConfigManager.get_config()
        
        assert config1 is config2
    
    def test_reload_config(self, tmp_path):
        """Test reloading configuration."""
        # Clear any existing environment variables
        env_vars_to_clear = ['OPENROUTER_API_KEY', 'CLOCKIFY_API_KEY', 'UNIFIED_TO_API_KEY', 
                             'YOUCOM_API_KEY', 'THESYS_API_KEY', 'MAX_RETRIES', 'LOG_LEVEL',
                             'CLOCKIFY_WORKSPACE_ID', 'UNIFIED_TO_WORKSPACE_ID']
        for key in env_vars_to_clear:
            os.environ.pop(key, None)
        
        env_file = tmp_path / ".env"
        env_file.write_text("""
OPENROUTER_API_KEY=sk-test-key-reload
CLOCKIFY_API_KEY=clockify-key-reload
UNIFIED_TO_API_KEY=unified-key-reload
YOUCOM_API_KEY=youcom-key-reload
THESYS_API_KEY=thesys-key-reload
CLOCKIFY_WORKSPACE_ID=workspace-123
UNIFIED_TO_WORKSPACE_ID=workspace-456
MAX_RETRIES=3
        """)
        
        config1 = ConfigManager.load_config(env_file=str(env_file))
        assert config1.max_retries == 3
        
        # Clear environment variables again before reload
        for key in env_vars_to_clear:
            os.environ.pop(key, None)
        
        # Update env file
        env_file.write_text("""
OPENROUTER_API_KEY=sk-test-key-reload
CLOCKIFY_API_KEY=clockify-key-reload
UNIFIED_TO_API_KEY=unified-key-reload
YOUCOM_API_KEY=youcom-key-reload
THESYS_API_KEY=thesys-key-reload
CLOCKIFY_WORKSPACE_ID=workspace-123
UNIFIED_TO_WORKSPACE_ID=workspace-456
MAX_RETRIES=10
        """)
        
        config2 = ConfigManager.reload_config(env_file=str(env_file))
        assert config2.max_retries == 10
        assert config1 is not config2
    
    def test_is_initialized(self, tmp_path):
        """Test is_initialized method."""
        assert ConfigManager.is_initialized() is False
        
        env_file = tmp_path / ".env"
        env_file.write_text("""
OPENROUTER_API_KEY=sk-test-key
CLOCKIFY_API_KEY=clockify-key
UNIFIED_TO_API_KEY=unified-key
YOUCOM_API_KEY=youcom-key
THESYS_API_KEY=thesys-key
CLOCKIFY_WORKSPACE_ID=workspace-123
UNIFIED_TO_WORKSPACE_ID=workspace-456
        """)
        
        ConfigManager.load_config(env_file=str(env_file))
        assert ConfigManager.is_initialized() is True
    
    def test_get_config_convenience_function(self, tmp_path):
        """Test get_config convenience function."""
        # Clear any existing environment variables
        for key in ['OPENROUTER_API_KEY', 'CLOCKIFY_API_KEY', 'UNIFIED_TO_API_KEY', 
                    'YOUCOM_API_KEY', 'THESYS_API_KEY']:
            os.environ.pop(key, None)
        
        env_file = tmp_path / ".env"
        env_file.write_text("""
OPENROUTER_API_KEY=sk-test-key-conv
CLOCKIFY_API_KEY=clockify-key-conv
UNIFIED_TO_API_KEY=unified-key-conv
YOUCOM_API_KEY=youcom-key-conv
THESYS_API_KEY=thesys-key-conv
CLOCKIFY_WORKSPACE_ID=workspace-123
UNIFIED_TO_WORKSPACE_ID=workspace-456
        """)
        
        ConfigManager.reload_config(env_file=str(env_file))
        config = get_config()
        
        assert config.openrouter_api_key == "sk-test-key-conv"
    
    def test_invalid_numeric_value_raises_error(self, tmp_path):
        """Test that invalid numeric value raises ConfigurationError."""
        # Clear any existing environment variables
        for key in ['OPENROUTER_API_KEY', 'CLOCKIFY_API_KEY', 'UNIFIED_TO_API_KEY', 
                    'YOUCOM_API_KEY', 'THESYS_API_KEY', 'MAX_RETRIES']:
            os.environ.pop(key, None)
        
        env_file = tmp_path / ".env"
        env_file.write_text("""
OPENROUTER_API_KEY=sk-test-key-numeric
CLOCKIFY_API_KEY=clockify-key-numeric
UNIFIED_TO_API_KEY=unified-key-numeric
YOUCOM_API_KEY=youcom-key-numeric
THESYS_API_KEY=thesys-key-numeric
CLOCKIFY_WORKSPACE_ID=workspace-123
UNIFIED_TO_WORKSPACE_ID=workspace-456
MAX_RETRIES=not_a_number
        """)
        
        ConfigManager._instance = None
        ConfigManager._initialized = False
        
        with pytest.raises(ConfigurationError, match="Invalid configuration value"):
            ConfigManager.load_config(env_file=str(env_file))


class TestRetryDecoratorIntegration:
    """Test suite for retry decorator with mock failures."""
    
    def test_retry_with_eventual_success(self):
        """Test retry decorator with eventual success."""
        call_count = 0
        
        @retry_with_backoff(max_attempts=3, initial_delay=0.01, jitter=False)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"
        
        result = flaky_function()
        
        assert result == "success"
        assert call_count == 2
    
    def test_retry_exhausts_attempts(self):
        """Test retry decorator exhausts all attempts."""
        call_count = 0
        
        @retry_with_backoff(max_attempts=3, initial_delay=0.01, jitter=False)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent failure")
        
        with pytest.raises(ValueError, match="Permanent failure"):
            always_fails()
        
        assert call_count == 3


class TestValidationFunctionsIntegration:
    """Test suite for validation functions with edge cases."""
    
    def test_validate_date_range_edge_cases(self):
        """Test date range validation with edge cases."""
        from datetime import datetime, timedelta
        
        # Same date
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1)
        result_start, result_end = validate_date_range(start, end, allow_future=True)
        assert result_start == start
        assert result_end == end
        
        # Start after end - use dates that will trigger the error
        start_later = datetime(2024, 12, 31)
        end_earlier = datetime(2024, 1, 1)
        with pytest.raises(ValidationError, match="must be before or equal to"):
            validate_date_range(start_later, end_earlier)
    
    def test_validate_api_key_edge_cases(self):
        """Test API key validation with edge cases."""
        # Empty string
        with pytest.raises(ValidationError):
            validate_api_key("")
        
        # Whitespace only
        with pytest.raises(ValidationError):
            validate_api_key("   ")
        
        # Valid key with whitespace (must meet min_length requirement)
        result = validate_api_key("  sk-valid-key-1234567890  ", min_length=10)
        assert result == "sk-valid-key-1234567890"
    
    def test_sanitize_text_edge_cases(self):
        """Test text sanitization with edge cases."""
        # HTML injection
        text = "<script>alert('xss')</script>Normal text"
        result = sanitize_text(text)
        assert "<script>" not in result
        assert "Normal text" in result
        
        # Empty string
        result = sanitize_text("")
        assert result == ""
        
        # Multiple spaces
        result = sanitize_text("Text  with    spaces")
        assert result == "Text with spaces"
