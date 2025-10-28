"""
Application-wide constants and enumerations for the R&D Tax Credit Automation Agent.

This module defines all constant values, enumerations, and configuration parameters
used throughout the application, including IRS-specific values from Form 6765.
"""

from enum import Enum


# ============================================================================
# Enumerations
# ============================================================================

class CostType(str, Enum):
    """
    Types of costs that can be classified for R&D tax credit purposes.
    
    Based on IRS Form 6765 qualified research expenditure categories.
    """
    PAYROLL = "Payroll"
    CONTRACTOR = "Contractor"
    MATERIALS = "Materials"
    CLOUD = "Cloud"
    OTHER = "Other"


class AgentStatus(str, Enum):
    """
    Status values for agent execution tracking.
    
    Used for workflow visualization and progress monitoring.
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


# ============================================================================
# Confidence Thresholds
# ============================================================================

class ConfidenceThreshold:
    """
    Confidence score thresholds for R&D qualification decisions.
    
    These thresholds determine when projects should be flagged for review
    and how qualification results are categorized.
    """
    LOW = 0.7      # Below this threshold, projects are flagged for manual review
    MEDIUM = 0.8   # Moderate confidence level
    HIGH = 0.9     # High confidence level, minimal review needed


# ============================================================================
# IRS Form 6765 Constants
# ============================================================================

class IRSWageCap:
    """
    IRS wage cap constants from Form 6765 instructions.
    
    These values are used to calculate the maximum qualified research expenditures
    for employee wages. Values are based on the Social Security wage base and
    IRS regulations for R&D tax credit calculations.
    
    Note: These values may change annually. Update based on current IRS guidance.
    """
    
    # Social Security Wage Base (updated annually by SSA)
    # For 2024: $168,600
    # For 2023: $160,200
    SOCIAL_SECURITY_WAGE_BASE_2024 = 168_600.00
    SOCIAL_SECURITY_WAGE_BASE_2023 = 160_200.00
    
    # Percentage of wages that can be claimed (typically 100% for qualified research)
    QUALIFIED_WAGE_PERCENTAGE = 1.0
    
    # Maximum percentage of an employee's time that can be allocated to R&D
    # (100% = full-time R&D employee)
    MAX_TIME_ALLOCATION_PERCENTAGE = 100.0
    
    # R&D Tax Credit Rate (as percentage of qualified research expenditures)
    # Regular credit rate: 20%
    # Alternative Simplified Credit (ASC) rate: 14%
    REGULAR_CREDIT_RATE = 0.20
    ALTERNATIVE_SIMPLIFIED_CREDIT_RATE = 0.14
    
    # Minimum hours per day threshold for flagging suspicious entries
    SUSPICIOUS_HOURS_THRESHOLD = 16.0
    
    # Maximum hours per day allowed
    MAX_HOURS_PER_DAY = 24.0


# ============================================================================
# Application Configuration Constants
# ============================================================================

class AppConstants:
    """
    General application configuration constants.
    """
    
    # Default values for data processing
    DEFAULT_CHUNK_SIZE = 512  # tokens for RAG chunking
    DEFAULT_CHUNK_OVERLAP = 50  # tokens overlap between chunks
    DEFAULT_TOP_K_RESULTS = 3  # number of RAG results to retrieve
    
    # API rate limiting
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0  # seconds
    DEFAULT_TIMEOUT = 30  # seconds
    
    # Report generation
    MAX_PROJECTS_PER_REPORT = 50
    MAX_TIME_ENTRIES_PER_INGESTION = 10_000
    PDF_GENERATION_TIMEOUT = 60  # seconds
    
    # Performance targets
    TARGET_INGESTION_TIME = 30  # seconds for 10k records
    TARGET_RAG_QUERY_TIME = 5  # seconds
    TARGET_QUALIFICATION_TIME = 30  # seconds per project


# ============================================================================
# API Endpoint Constants
# ============================================================================

class APIEndpoints:
    """
    External API endpoint base URLs.
    """
    CLOCKIFY_BASE_URL = "https://api.clockify.me/api/v1"
    UNIFIED_TO_BASE_URL = "https://api.unified.to"
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    YOU_COM_BASE_URL = "https://api.you.com"


# ============================================================================
# Model Configuration Constants
# ============================================================================

class ModelConfig:
    """
    LLM model configuration constants.
    """
    
    # DeepSeek model via OpenRouter
    DEEPSEEK_MODEL = "deepseek/deepseek-chat-v3.1:free"
    
    # Embedding model for RAG
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION = 384  # dimension for all-MiniLM-L6-v2
    
    # Default LLM parameters
    DEFAULT_TEMPERATURE = 0.2  # Lower temperature for more deterministic outputs
    DEFAULT_MAX_TOKENS = 2048
    DEFAULT_TOP_P = 0.9


# ============================================================================
# File Path Constants
# ============================================================================

class FilePaths:
    """
    Standard file paths used throughout the application.
    """
    KNOWLEDGE_BASE_DIR = "knowledge_base"
    TAX_DOCS_DIR = "knowledge_base/tax_docs"
    INDEXED_DIR = "knowledge_base/indexed"
    OUTPUTS_DIR = "outputs"
    REPORTS_DIR = "outputs/reports"
    TEMP_DIR = "outputs/temp"
    LOGS_DIR = "logs"


# ============================================================================
# Validation Constants
# ============================================================================

class ValidationRules:
    """
    Data validation rules and constraints.
    """
    
    # Date validation
    MIN_YEAR = 2000  # Minimum valid year for tax data
    MAX_FUTURE_DAYS = 0  # Days in the future allowed (0 = no future dates)
    
    # Numeric validation
    MIN_HOURS = 0.0
    MAX_HOURS = 24.0
    MIN_COST = 0.01  # Minimum cost to be considered valid
    
    # String validation
    MAX_PROJECT_NAME_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 5000
    MIN_EMPLOYEE_ID_LENGTH = 1
    MAX_EMPLOYEE_ID_LENGTH = 50


# ============================================================================
# Export all constants for easy importing
# ============================================================================

__all__ = [
    "CostType",
    "AgentStatus",
    "ConfidenceThreshold",
    "IRSWageCap",
    "AppConstants",
    "APIEndpoints",
    "ModelConfig",
    "FilePaths",
    "ValidationRules",
]
