"""
Data validation utilities for R&D Tax Credit Automation Agent.

This module provides common validation functions for:
- Date range validation
- API key format validation
- Text sanitization for LLM prompts

Requirements: 7.2, 8.2
"""

import re
from datetime import datetime, date
from typing import Tuple, Optional
from .exceptions import ValidationError


def validate_date_range(
    start_date: datetime | date | str,
    end_date: datetime | date | str,
    allow_future: bool = False,
    max_range_days: Optional[int] = None
) -> Tuple[datetime, datetime]:
    """
    Validate a date range for data ingestion and processing.
    
    Args:
        start_date: Start date (datetime, date, or ISO format string)
        end_date: End date (datetime, date, or ISO format string)
        allow_future: Whether to allow future dates (default: False)
        max_range_days: Maximum allowed range in days (optional)
    
    Returns:
        Tuple of (start_datetime, end_datetime) as datetime objects
    
    Raises:
        ValidationError: If dates are invalid or violate constraints
    
    Examples:
        >>> validate_date_range("2024-01-01", "2024-12-31")
        (datetime(2024, 1, 1, 0, 0), datetime(2024, 12, 31, 0, 0))
        
        >>> validate_date_range(date(2024, 1, 1), date(2024, 12, 31), max_range_days=365)
        (datetime(2024, 1, 1, 0, 0), datetime(2024, 12, 31, 0, 0))
    """
    # Convert to datetime objects
    try:
        if isinstance(start_date, str):
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        elif isinstance(start_date, date) and not isinstance(start_date, datetime):
            start_dt = datetime.combine(start_date, datetime.min.time())
        elif isinstance(start_date, datetime):
            start_dt = start_date
        else:
            raise ValidationError(
                f"Invalid start_date type: {type(start_date)}. "
                "Expected datetime, date, or ISO format string."
            )
        
        if isinstance(end_date, str):
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        elif isinstance(end_date, date) and not isinstance(end_date, datetime):
            end_dt = datetime.combine(end_date, datetime.min.time())
        elif isinstance(end_date, datetime):
            end_dt = end_date
        else:
            raise ValidationError(
                f"Invalid end_date type: {type(end_date)}. "
                "Expected datetime, date, or ISO format string."
            )
    except (ValueError, TypeError) as e:
        raise ValidationError(f"Failed to parse dates: {str(e)}")
    
    # Validate start_date is before end_date
    if start_dt > end_dt:
        raise ValidationError(
            f"start_date ({start_dt.date()}) must be before or equal to "
            f"end_date ({end_dt.date()})"
        )
    
    # Validate against future dates if not allowed
    if not allow_future:
        now = datetime.now()
        if start_dt > now:
            raise ValidationError(
                f"start_date ({start_dt.date()}) cannot be in the future"
            )
        if end_dt > now:
            raise ValidationError(
                f"end_date ({end_dt.date()}) cannot be in the future"
            )
    
    # Validate maximum range if specified
    if max_range_days is not None:
        range_days = (end_dt - start_dt).days
        if range_days > max_range_days:
            raise ValidationError(
                f"Date range ({range_days} days) exceeds maximum allowed "
                f"range of {max_range_days} days"
            )
    
    return start_dt, end_dt


def validate_api_key(
    api_key: str,
    key_name: str = "API key",
    min_length: int = 20,
    max_length: int = 200,
    allowed_chars: Optional[str] = None
) -> str:
    """
    Validate API key format and structure.
    
    Args:
        api_key: The API key to validate
        key_name: Name of the key for error messages (default: "API key")
        min_length: Minimum allowed length (default: 20)
        max_length: Maximum allowed length (default: 200)
        allowed_chars: Regex pattern for allowed characters (optional)
                      Default allows alphanumeric, hyphens, underscores, and dots
    
    Returns:
        The validated API key (stripped of whitespace)
    
    Raises:
        ValidationError: If API key is invalid
    
    Examples:
        >>> validate_api_key("sk-1234567890abcdefghij")
        'sk-1234567890abcdefghij'
        
        >>> validate_api_key("my_api_key_123", key_name="Clockify API Key", min_length=10)
        'my_api_key_123'
    """
    if not api_key or not isinstance(api_key, str):
        raise ValidationError(f"{key_name} must be a non-empty string")
    
    # Strip whitespace
    api_key = api_key.strip()
    
    # Check if empty after stripping
    if not api_key:
        raise ValidationError(f"{key_name} cannot be empty or whitespace only")
    
    # Validate length
    if len(api_key) < min_length:
        raise ValidationError(
            f"{key_name} is too short. Minimum length: {min_length}, "
            f"provided: {len(api_key)}"
        )
    
    if len(api_key) > max_length:
        raise ValidationError(
            f"{key_name} is too long. Maximum length: {max_length}, "
            f"provided: {len(api_key)}"
        )
    
    # Validate character set
    if allowed_chars is None:
        # Default: alphanumeric, hyphens, underscores, dots
        allowed_chars = r'^[a-zA-Z0-9\-_.]+$'
    
    if not re.match(allowed_chars, api_key):
        raise ValidationError(
            f"{key_name} contains invalid characters. "
            f"Allowed pattern: {allowed_chars}"
        )
    
    return api_key


def sanitize_text(
    text: str,
    max_length: int = 10000,
    remove_special_chars: bool = False,
    preserve_newlines: bool = True,
    strip_html: bool = True
) -> str:
    """
    Sanitize text for safe use in LLM prompts.
    
    This function removes potentially problematic content from user-provided
    text before including it in LLM prompts, preventing prompt injection and
    ensuring clean input.
    
    Args:
        text: The text to sanitize
        max_length: Maximum allowed length (default: 10000)
        remove_special_chars: Remove special characters except basic punctuation
        preserve_newlines: Keep newline characters (default: True)
        strip_html: Remove HTML tags (default: True)
    
    Returns:
        Sanitized text safe for LLM prompts
    
    Raises:
        ValidationError: If text is invalid or too long
    
    Examples:
        >>> sanitize_text("Hello <script>alert('xss')</script> World!")
        'Hello  World!'
        
        >>> sanitize_text("Project\\nDescription", preserve_newlines=True)
        'Project\\nDescription'
    """
    if not isinstance(text, str):
        raise ValidationError(f"Text must be a string, got {type(text)}")
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    # Check if empty
    if not text:
        return ""
    
    # Check length before processing
    if len(text) > max_length:
        raise ValidationError(
            f"Text exceeds maximum length of {max_length} characters "
            f"(provided: {len(text)})"
        )
    
    # Remove HTML tags if requested
    if strip_html:
        # Remove script and style tags with their content first
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.IGNORECASE | re.DOTALL)
        # Remove remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
    
    # Remove common prompt injection patterns
    # Remove excessive special characters that might break prompts
    injection_patterns = [
        r'```[\s\S]*?```',  # Code blocks
        r'<\|.*?\|>',  # Special tokens
        r'\[INST\].*?\[/INST\]',  # Instruction markers
        r'<\|im_start\|>.*?<\|im_end\|>',  # Chat format markers
    ]
    
    for pattern in injection_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Normalize whitespace
    if preserve_newlines:
        # Collapse multiple spaces but preserve newlines
        text = re.sub(r'[ \t]+', ' ', text)
        # Limit consecutive newlines to 2
        text = re.sub(r'\n{3,}', '\n\n', text)
    else:
        # Collapse all whitespace to single spaces
        text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters if requested
    if remove_special_chars:
        # Keep only alphanumeric, basic punctuation, and optionally newlines
        if preserve_newlines:
            text = re.sub(r'[^a-zA-Z0-9\s.,!?;:()\-\'\"\n]', '', text)
        else:
            text = re.sub(r'[^a-zA-Z0-9\s.,!?;:()\-\'\"]', '', text)
    
    # Final trim
    text = text.strip()
    
    return text
