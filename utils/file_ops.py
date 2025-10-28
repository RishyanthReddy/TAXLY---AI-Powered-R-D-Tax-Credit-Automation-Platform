"""
Safe file operations utility for R&D Tax Credit Automation Agent.

This module provides utilities for safe file handling including:
- Atomic writes to prevent data corruption
- Encoding detection for safe file reading
- Temporary file cleanup and management
- Error handling for file operations

All file operations are designed to be safe, atomic, and resilient to failures.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Union, List
import chardet
from datetime import datetime, timedelta

from .logger import AgentLogger
from .exceptions import RDTaxAgentError


# Get logger for file operations
logger = AgentLogger.get_logger("utils.file_ops")


class FileOperationError(RDTaxAgentError):
    """
    Exception raised when file operations fail.
    
    This exception is used for all file operation failures including
    read errors, write errors, permission issues, and disk space problems.
    
    Attributes:
        file_path: Path to the file that caused the error
        operation: Type of operation that failed (e.g., 'read', 'write', 'delete')
    """
    
    def __init__(
        self,
        message: str,
        file_path: str = None,
        operation: str = None,
        details: dict = None
    ):
        """
        Initialize file operation error.
        
        Args:
            message: Human-readable error message
            file_path: Path to the file that caused the error
            operation: Type of operation that failed
            details: Additional error context
        """
        error_details = details or {}
        error_details.update({
            'file_path': file_path,
            'operation': operation
        })
        super().__init__(message, error_details)
        self.file_path = file_path
        self.operation = operation


def safe_write_file(
    file_path: Union[str, Path],
    content: Union[str, bytes],
    encoding: str = "utf-8",
    create_dirs: bool = True
) -> None:
    """
    Write content to a file atomically to prevent data corruption.
    
    This function uses atomic write operations by writing to a temporary file
    first and then moving it to the target location. This ensures that the
    target file is never left in a partially written state.
    
    Args:
        file_path: Path to the target file
        content: Content to write (string or bytes)
        encoding: Character encoding for text content (default: utf-8)
        create_dirs: Whether to create parent directories if they don't exist
    
    Raises:
        FileOperationError: If the write operation fails
    
    Example:
        >>> safe_write_file("output.txt", "Hello, World!")
        >>> safe_write_file("data.bin", b"\\x00\\x01\\x02", encoding=None)
    """
    file_path = Path(file_path)
    
    try:
        # Create parent directories if needed
        if create_dirs and not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created parent directories for {file_path}")
        
        # Determine if content is binary or text
        is_binary = isinstance(content, bytes)
        
        # Create temporary file in the same directory as target
        # This ensures atomic move works (same filesystem)
        temp_fd, temp_path = tempfile.mkstemp(
            dir=file_path.parent,
            prefix=f".{file_path.name}.",
            suffix=".tmp"
        )
        
        try:
            # Write content to temporary file
            if is_binary:
                os.write(temp_fd, content)
            else:
                os.write(temp_fd, content.encode(encoding))
            
            # Ensure data is written to disk
            os.fsync(temp_fd)
            os.close(temp_fd)
            
            # Atomically move temporary file to target location
            # This is atomic on POSIX systems and Windows (Python 3.3+)
            shutil.move(temp_path, file_path)
            
            logger.debug(f"Successfully wrote file: {file_path}")
            
        except Exception as e:
            # Clean up temporary file on error
            os.close(temp_fd)
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
            
    except Exception as e:
        error_msg = f"Failed to write file {file_path}: {str(e)}"
        logger.error(error_msg)
        raise FileOperationError(
            message=error_msg,
            file_path=str(file_path),
            operation="write",
            details={"error": str(e)}
        )


def safe_read_file(
    file_path: Union[str, Path],
    encoding: Optional[str] = None,
    detect_encoding: bool = True
) -> Union[str, bytes]:
    """
    Read content from a file with automatic encoding detection.
    
    This function safely reads file content with optional automatic encoding
    detection. If encoding is not specified and detect_encoding is True,
    it will attempt to detect the file encoding using chardet.
    
    Args:
        file_path: Path to the file to read
        encoding: Character encoding (if None and detect_encoding=True, auto-detect)
        detect_encoding: Whether to auto-detect encoding if not specified
    
    Returns:
        File content as string (if encoding specified/detected) or bytes
    
    Raises:
        FileOperationError: If the read operation fails
        FileNotFoundError: If the file does not exist
    
    Example:
        >>> content = safe_read_file("input.txt")
        >>> binary_content = safe_read_file("data.bin", encoding=None, detect_encoding=False)
    """
    file_path = Path(file_path)
    
    try:
        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read file in binary mode first
        with open(file_path, "rb") as f:
            raw_content = f.read()
        
        # If no encoding specified and detection disabled, return bytes
        if encoding is None and not detect_encoding:
            logger.debug(f"Read file as binary: {file_path}")
            return raw_content
        
        # Detect encoding if needed
        if encoding is None and detect_encoding:
            detection_result = chardet.detect(raw_content)
            encoding = detection_result.get("encoding", "utf-8")
            confidence = detection_result.get("confidence", 0)
            
            logger.debug(
                f"Detected encoding for {file_path}: {encoding} "
                f"(confidence: {confidence:.2%})"
            )
            
            # Fall back to utf-8 if confidence is too low
            if confidence < 0.7:
                logger.warning(
                    f"Low encoding detection confidence ({confidence:.2%}), "
                    f"falling back to utf-8"
                )
                encoding = "utf-8"
        
        # Decode content
        try:
            content = raw_content.decode(encoding)
            logger.debug(f"Successfully read file: {file_path}")
            return content
        except UnicodeDecodeError as e:
            # Try utf-8 as fallback
            if encoding != "utf-8":
                logger.warning(
                    f"Failed to decode with {encoding}, trying utf-8 fallback"
                )
                try:
                    content = raw_content.decode("utf-8")
                    return content
                except UnicodeDecodeError:
                    pass
            
            # If all else fails, return with error replacement
            logger.warning(
                f"Failed to decode {file_path}, using error replacement"
            )
            return raw_content.decode(encoding, errors="replace")
            
    except FileNotFoundError:
        raise
    except Exception as e:
        error_msg = f"Failed to read file {file_path}: {str(e)}"
        logger.error(error_msg)
        raise FileOperationError(
            message=error_msg,
            file_path=str(file_path),
            operation="read",
            details={"error": str(e)}
        )


def cleanup_temp_files(
    temp_dir: Union[str, Path],
    max_age_hours: int = 24,
    pattern: str = "*",
    dry_run: bool = False
) -> int:
    """
    Clean up temporary files older than specified age.
    
    This function removes temporary files from a directory that are older
    than the specified age. Useful for cleaning up stale temporary files
    from processing operations.
    
    Args:
        temp_dir: Directory containing temporary files
        max_age_hours: Maximum age of files to keep (in hours)
        pattern: Glob pattern for files to clean (default: all files)
        dry_run: If True, only report what would be deleted without deleting
    
    Returns:
        Number of files deleted (or would be deleted in dry_run mode)
    
    Raises:
        FileOperationError: If cleanup operation fails
    
    Example:
        >>> # Clean up temp files older than 24 hours
        >>> deleted = cleanup_temp_files("outputs/temp", max_age_hours=24)
        >>> print(f"Deleted {deleted} temporary files")
    """
    temp_dir = Path(temp_dir)
    
    try:
        # Check if directory exists
        if not temp_dir.exists():
            logger.warning(f"Temp directory does not exist: {temp_dir}")
            return 0
        
        if not temp_dir.is_dir():
            raise FileOperationError(
                message=f"Path is not a directory: {temp_dir}",
                file_path=str(temp_dir),
                operation="cleanup"
            )
        
        # Calculate cutoff time
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cutoff_timestamp = cutoff_time.timestamp()
        
        deleted_count = 0
        total_size = 0
        
        # Find and delete old files
        for file_path in temp_dir.glob(pattern):
            if not file_path.is_file():
                continue
            
            try:
                # Check file age
                file_mtime = file_path.stat().st_mtime
                
                if file_mtime < cutoff_timestamp:
                    file_size = file_path.stat().st_size
                    
                    if dry_run:
                        logger.info(
                            f"Would delete: {file_path} "
                            f"(age: {(datetime.now().timestamp() - file_mtime) / 3600:.1f}h, "
                            f"size: {file_size} bytes)"
                        )
                    else:
                        file_path.unlink()
                        logger.debug(
                            f"Deleted temp file: {file_path} "
                            f"(age: {(datetime.now().timestamp() - file_mtime) / 3600:.1f}h, "
                            f"size: {file_size} bytes)"
                        )
                    
                    deleted_count += 1
                    total_size += file_size
                    
            except Exception as e:
                logger.warning(f"Failed to delete {file_path}: {e}")
                continue
        
        action = "Would delete" if dry_run else "Deleted"
        logger.info(
            f"{action} {deleted_count} temporary files "
            f"(total size: {total_size / 1024:.2f} KB) from {temp_dir}"
        )
        
        return deleted_count
        
    except Exception as e:
        error_msg = f"Failed to cleanup temp files in {temp_dir}: {str(e)}"
        logger.error(error_msg)
        raise FileOperationError(
            message=error_msg,
            file_path=str(temp_dir),
            operation="cleanup",
            details={"error": str(e)}
        )


def ensure_directory(
    dir_path: Union[str, Path],
    create_if_missing: bool = True
) -> Path:
    """
    Ensure a directory exists, optionally creating it if missing.
    
    Args:
        dir_path: Path to the directory
        create_if_missing: Whether to create the directory if it doesn't exist
    
    Returns:
        Path object for the directory
    
    Raises:
        FileOperationError: If directory cannot be created or accessed
    
    Example:
        >>> output_dir = ensure_directory("outputs/reports")
    """
    dir_path = Path(dir_path)
    
    try:
        if not dir_path.exists():
            if create_if_missing:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {dir_path}")
            else:
                raise FileOperationError(
                    message=f"Directory does not exist: {dir_path}",
                    file_path=str(dir_path),
                    operation="ensure_directory"
                )
        
        if not dir_path.is_dir():
            raise FileOperationError(
                message=f"Path exists but is not a directory: {dir_path}",
                file_path=str(dir_path),
                operation="ensure_directory"
            )
        
        return dir_path
        
    except Exception as e:
        if isinstance(e, FileOperationError):
            raise
        error_msg = f"Failed to ensure directory {dir_path}: {str(e)}"
        logger.error(error_msg)
        raise FileOperationError(
            message=error_msg,
            file_path=str(dir_path),
            operation="ensure_directory",
            details={"error": str(e)}
        )


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
    
    Returns:
        File size in bytes
    
    Raises:
        FileOperationError: If file size cannot be determined
    """
    file_path = Path(file_path)
    
    try:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return file_path.stat().st_size
        
    except Exception as e:
        error_msg = f"Failed to get file size for {file_path}: {str(e)}"
        logger.error(error_msg)
        raise FileOperationError(
            message=error_msg,
            file_path=str(file_path),
            operation="get_size",
            details={"error": str(e)}
        )


def list_files(
    directory: Union[str, Path],
    pattern: str = "*",
    recursive: bool = False
) -> List[Path]:
    """
    List files in a directory matching a pattern.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern for files (default: all files)
        recursive: Whether to search recursively
    
    Returns:
        List of Path objects for matching files
    
    Raises:
        FileOperationError: If directory cannot be accessed
    
    Example:
        >>> pdf_files = list_files("outputs/reports", pattern="*.pdf")
    """
    directory = Path(directory)
    
    try:
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not directory.is_dir():
            raise FileOperationError(
                message=f"Path is not a directory: {directory}",
                file_path=str(directory),
                operation="list_files"
            )
        
        if recursive:
            files = [f for f in directory.rglob(pattern) if f.is_file()]
        else:
            files = [f for f in directory.glob(pattern) if f.is_file()]
        
        logger.debug(f"Found {len(files)} files in {directory} matching '{pattern}'")
        return files
        
    except Exception as e:
        if isinstance(e, FileOperationError):
            raise
        error_msg = f"Failed to list files in {directory}: {str(e)}"
        logger.error(error_msg)
        raise FileOperationError(
            message=error_msg,
            file_path=str(directory),
            operation="list_files",
            details={"error": str(e)}
        )
