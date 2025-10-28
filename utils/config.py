"""
Centralized configuration management for R&D Tax Credit Automation Agent.

This module provides:
- Environment variable loading and validation
- Type-safe configuration dataclass
- Required API key validation
- Singleton pattern for global config access
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when configuration is invalid or incomplete."""
    pass


@dataclass
class Config:
    """
    Application configuration with type hints and validation.
    
    All configuration values are loaded from environment variables.
    Required API keys are validated on initialization.
    """
    
    # API Keys - Required
    openrouter_api_key: str
    clockify_api_key: str
    unified_to_api_key: str
    youcom_api_key: str
    thesys_api_key: str
    
    # API Workspace IDs - Required
    clockify_workspace_id: str
    unified_to_workspace_id: str
    
    # Optional API Endpoints
    playwright_mcp_endpoint: Optional[str] = None
    
    # Application Settings
    log_level: str = "INFO"
    max_retries: int = 3
    timeout_seconds: int = 30
    
    # RAG Configuration
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k_results: int = 3
    
    # Confidence Thresholds
    confidence_threshold_low: float = 0.7
    confidence_threshold_medium: float = 0.8
    confidence_threshold_high: float = 0.9
    
    # Paths
    knowledge_base_path: Path = field(default_factory=lambda: Path("knowledge_base"))
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    output_dir: Path = field(default_factory=lambda: Path("outputs"))
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_api_keys()
        self._validate_thresholds()
        self._validate_paths()
        self._validate_numeric_values()
    
    def _validate_api_keys(self) -> None:
        """Validate that all required API keys are present and non-empty."""
        required_keys = {
            "openrouter_api_key": self.openrouter_api_key,
            "clockify_api_key": self.clockify_api_key,
            "unified_to_api_key": self.unified_to_api_key,
            "youcom_api_key": self.youcom_api_key,
            "thesys_api_key": self.thesys_api_key,
            "clockify_workspace_id": self.clockify_workspace_id,
            "unified_to_workspace_id": self.unified_to_workspace_id,
        }
        
        missing_keys = []
        placeholder_keys = []
        
        for key_name, key_value in required_keys.items():
            if not key_value:
                missing_keys.append(key_name)
            elif "your_" in key_value.lower() or "_here" in key_value.lower():
                placeholder_keys.append(key_name)
        
        if missing_keys:
            raise ConfigurationError(
                f"Missing required configuration: {', '.join(missing_keys)}. "
                f"Please set these environment variables in your .env file."
            )
        
        if placeholder_keys:
            raise ConfigurationError(
                f"Placeholder values detected for: {', '.join(placeholder_keys)}. "
                f"Please replace with actual API keys in your .env file."
            )
    
    def _validate_thresholds(self) -> None:
        """Validate confidence thresholds are in valid range [0, 1]."""
        thresholds = {
            "confidence_threshold_low": self.confidence_threshold_low,
            "confidence_threshold_medium": self.confidence_threshold_medium,
            "confidence_threshold_high": self.confidence_threshold_high,
        }
        
        for name, value in thresholds.items():
            if not 0 <= value <= 1:
                raise ConfigurationError(
                    f"{name} must be between 0 and 1, got {value}"
                )
        
        # Validate threshold ordering
        if not (self.confidence_threshold_low <= self.confidence_threshold_medium <= self.confidence_threshold_high):
            raise ConfigurationError(
                f"Confidence thresholds must be in ascending order: "
                f"low ({self.confidence_threshold_low}) <= "
                f"medium ({self.confidence_threshold_medium}) <= "
                f"high ({self.confidence_threshold_high})"
            )
    
    def _validate_paths(self) -> None:
        """Ensure paths are Path objects."""
        if not isinstance(self.knowledge_base_path, Path):
            self.knowledge_base_path = Path(self.knowledge_base_path)
        if not isinstance(self.log_dir, Path):
            self.log_dir = Path(self.log_dir)
        if not isinstance(self.output_dir, Path):
            self.output_dir = Path(self.output_dir)
    
    def _validate_numeric_values(self) -> None:
        """Validate numeric configuration values are in valid ranges."""
        if self.max_retries < 0:
            raise ConfigurationError(f"max_retries must be non-negative, got {self.max_retries}")
        
        if self.timeout_seconds <= 0:
            raise ConfigurationError(f"timeout_seconds must be positive, got {self.timeout_seconds}")
        
        if self.chunk_size <= 0:
            raise ConfigurationError(f"chunk_size must be positive, got {self.chunk_size}")
        
        if self.chunk_overlap < 0:
            raise ConfigurationError(f"chunk_overlap must be non-negative, got {self.chunk_overlap}")
        
        if self.chunk_overlap >= self.chunk_size:
            raise ConfigurationError(
                f"chunk_overlap ({self.chunk_overlap}) must be less than chunk_size ({self.chunk_size})"
            )
        
        if self.top_k_results <= 0:
            raise ConfigurationError(f"top_k_results must be positive, got {self.top_k_results}")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            raise ConfigurationError(
                f"log_level must be one of {valid_log_levels}, got {self.log_level}"
            )


class ConfigManager:
    """
    Singleton configuration manager.
    
    Ensures only one configuration instance exists throughout the application.
    Loads configuration from environment variables on first access.
    """
    
    _instance: Optional[Config] = None
    _initialized: bool = False
    
    @classmethod
    def load_config(cls, env_file: Optional[str] = None) -> Config:
        """
        Load configuration from environment variables.
        
        Args:
            env_file: Path to .env file (default: .env in project root)
        
        Returns:
            Config instance
        
        Raises:
            ConfigurationError: If configuration is invalid or incomplete
        """
        if cls._initialized and cls._instance is not None:
            return cls._instance
        
        # Load environment variables from .env file
        if env_file is None:
            # Look for .env in project root (parent of utils directory)
            project_root = Path(__file__).parent.parent
            env_file = project_root / ".env"
        
        if Path(env_file).exists():
            load_dotenv(env_file)
        else:
            # Try to load from current directory
            load_dotenv()
        
        # Load configuration from environment variables
        try:
            config = Config(
                # API Keys
                openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
                clockify_api_key=os.getenv("CLOCKIFY_API_KEY", ""),
                unified_to_api_key=os.getenv("UNIFIED_TO_API_KEY", ""),
                youcom_api_key=os.getenv("YOUCOM_API_KEY", ""),
                thesys_api_key=os.getenv("THESYS_API_KEY", ""),
                
                # Workspace IDs
                clockify_workspace_id=os.getenv("CLOCKIFY_WORKSPACE_ID", ""),
                unified_to_workspace_id=os.getenv("UNIFIED_TO_WORKSPACE_ID", ""),
                
                # Optional endpoints
                playwright_mcp_endpoint=os.getenv("PLAYWRIGHT_MCP_ENDPOINT"),
                
                # Application settings
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                max_retries=int(os.getenv("MAX_RETRIES", "3")),
                timeout_seconds=int(os.getenv("TIMEOUT_SECONDS", "30")),
                
                # RAG configuration
                chunk_size=int(os.getenv("CHUNK_SIZE", "512")),
                chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
                top_k_results=int(os.getenv("TOP_K_RESULTS", "3")),
                
                # Confidence thresholds
                confidence_threshold_low=float(os.getenv("CONFIDENCE_THRESHOLD_LOW", "0.7")),
                confidence_threshold_medium=float(os.getenv("CONFIDENCE_THRESHOLD_MEDIUM", "0.8")),
                confidence_threshold_high=float(os.getenv("CONFIDENCE_THRESHOLD_HIGH", "0.9")),
                
                # Paths
                knowledge_base_path=Path(os.getenv("KNOWLEDGE_BASE_PATH", "knowledge_base")),
                log_dir=Path(os.getenv("LOG_DIR", "logs")),
                output_dir=Path(os.getenv("OUTPUT_DIR", "outputs")),
            )
            
            cls._instance = config
            cls._initialized = True
            
            return config
            
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid configuration value: {e}. "
                f"Please check your .env file for correct data types."
            )
    
    @classmethod
    def get_config(cls) -> Config:
        """
        Get the current configuration instance.
        
        If not already loaded, loads configuration from environment.
        
        Returns:
            Config instance
        
        Raises:
            ConfigurationError: If configuration is invalid or incomplete
        """
        if cls._instance is None:
            return cls.load_config()
        return cls._instance
    
    @classmethod
    def reload_config(cls, env_file: Optional[str] = None) -> Config:
        """
        Reload configuration from environment variables.
        
        Useful for testing or when configuration changes at runtime.
        
        Args:
            env_file: Path to .env file
        
        Returns:
            New Config instance
        """
        cls._instance = None
        cls._initialized = False
        return cls.load_config(env_file)
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Check if configuration has been initialized."""
        return cls._initialized


# Convenience function for getting configuration
def get_config() -> Config:
    """
    Get the application configuration.
    
    This is the primary way to access configuration throughout the application.
    
    Returns:
        Config instance
    
    Raises:
        ConfigurationError: If configuration is invalid or incomplete
    
    Example:
        >>> from utils.config import get_config
        >>> config = get_config()
        >>> print(config.openrouter_api_key)
    """
    return ConfigManager.get_config()
