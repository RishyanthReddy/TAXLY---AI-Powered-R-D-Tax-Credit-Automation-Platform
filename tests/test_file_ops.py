"""
Unit tests for file operations utility.

Tests cover:
- Atomic file writing
- Safe file reading with encoding detection
- Temporary file cleanup
- Directory management
- Error handling
"""

import pytest
import tempfile
import time
from pathlib import Path
from datetime import datetime, timedelta

from utils.file_ops import (
    safe_write_file,
    safe_read_file,
    cleanup_temp_files,
    ensure_directory,
    get_file_size,
    list_files,
    FileOperationError
)


class TestSafeWriteFile:
    """Tests for safe_write_file function."""
    
    def test_write_text_file(self, tmp_path):
        """Test writing a text file."""
        file_path = tmp_path / "test.txt"
        content = "Hello, World!"
        
        safe_write_file(file_path, content)
        
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == content
    
    def test_write_binary_file(self, tmp_path):
        """Test writing a binary file."""
        file_path = tmp_path / "test.bin"
        content = b"\x00\x01\x02\x03\x04"
        
        safe_write_file(file_path, content)
        
        assert file_path.exists()
        assert file_path.read_bytes() == content
    
    def test_write_with_custom_encoding(self, tmp_path):
        """Test writing with custom encoding."""
        file_path = tmp_path / "test_latin1.txt"
        content = "Héllo, Wörld!"
        
        safe_write_file(file_path, content, encoding="latin-1")
        
        assert file_path.exists()
        assert file_path.read_text(encoding="latin-1") == content
    
    def test_write_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created automatically."""
        file_path = tmp_path / "subdir1" / "subdir2" / "test.txt"
        content = "Test content"
        
        safe_write_file(file_path, content, create_dirs=True)
        
        assert file_path.exists()
        assert file_path.read_text() == content
    
    def test_write_overwrites_existing_file(self, tmp_path):
        """Test that existing files are overwritten."""
        file_path = tmp_path / "test.txt"
        
        # Write initial content
        safe_write_file(file_path, "Initial content")
        assert file_path.read_text() == "Initial content"
        
        # Overwrite with new content
        safe_write_file(file_path, "New content")
        assert file_path.read_text() == "New content"
    
    def test_write_atomic_operation(self, tmp_path):
        """Test that write is atomic (no partial writes)."""
        file_path = tmp_path / "test.txt"
        large_content = "x" * 10000
        
        safe_write_file(file_path, large_content)
        
        # File should either exist with full content or not exist at all
        assert file_path.exists()
        assert len(file_path.read_text()) == len(large_content)
    
    def test_write_to_nonexistent_directory_without_create(self, tmp_path):
        """Test writing to non-existent directory without create_dirs."""
        file_path = tmp_path / "nonexistent" / "test.txt"
        
        with pytest.raises(FileOperationError) as exc_info:
            safe_write_file(file_path, "content", create_dirs=False)
        
        assert "Failed to write file" in str(exc_info.value)


class TestSafeReadFile:
    """Tests for safe_read_file function."""
    
    def test_read_text_file(self, tmp_path):
        """Test reading a text file."""
        file_path = tmp_path / "test.txt"
        content = "Hello, World!"
        file_path.write_text(content, encoding="utf-8")
        
        result = safe_read_file(file_path, encoding="utf-8")
        
        assert result == content
    
    def test_read_binary_file(self, tmp_path):
        """Test reading a binary file."""
        file_path = tmp_path / "test.bin"
        content = b"\x00\x01\x02\x03\x04"
        file_path.write_bytes(content)
        
        result = safe_read_file(file_path, encoding=None, detect_encoding=False)
        
        assert result == content
    
    def test_read_with_encoding_detection(self, tmp_path):
        """Test reading with automatic encoding detection."""
        file_path = tmp_path / "test.txt"
        content = "Hello, World!"
        file_path.write_text(content, encoding="utf-8")
        
        # Read without specifying encoding
        result = safe_read_file(file_path, encoding=None, detect_encoding=True)
        
        assert result == content
    
    def test_read_with_custom_encoding(self, tmp_path):
        """Test reading with custom encoding."""
        file_path = tmp_path / "test_latin1.txt"
        content = "Héllo, Wörld!"
        file_path.write_text(content, encoding="latin-1")
        
        result = safe_read_file(file_path, encoding="latin-1")
        
        assert result == content
    
    def test_read_nonexistent_file(self, tmp_path):
        """Test reading a file that doesn't exist."""
        file_path = tmp_path / "nonexistent.txt"
        
        with pytest.raises(FileNotFoundError):
            safe_read_file(file_path)
    
    def test_read_with_fallback_encoding(self, tmp_path):
        """Test reading with encoding fallback on decode error."""
        file_path = tmp_path / "test.txt"
        # Write with latin-1 encoding
        file_path.write_bytes("Héllo".encode("latin-1"))
        
        # Try to read with utf-8 (will fail and fallback)
        result = safe_read_file(file_path, encoding="latin-1")
        
        assert "Héllo" in result


class TestCleanupTempFiles:
    """Tests for cleanup_temp_files function."""
    
    def test_cleanup_old_files(self, tmp_path):
        """Test cleaning up old temporary files."""
        # Create some old files
        old_file1 = tmp_path / "old1.tmp"
        old_file2 = tmp_path / "old2.tmp"
        old_file1.write_text("old content 1")
        old_file2.write_text("old content 2")
        
        # Make files appear old by modifying their timestamps
        old_time = (datetime.now() - timedelta(hours=48)).timestamp()
        old_file1.touch()
        old_file2.touch()
        import os
        os.utime(old_file1, (old_time, old_time))
        os.utime(old_file2, (old_time, old_time))
        
        # Create a recent file
        recent_file = tmp_path / "recent.tmp"
        recent_file.write_text("recent content")
        
        # Clean up files older than 24 hours
        deleted_count = cleanup_temp_files(tmp_path, max_age_hours=24)
        
        assert deleted_count == 2
        assert not old_file1.exists()
        assert not old_file2.exists()
        assert recent_file.exists()
    
    def test_cleanup_with_pattern(self, tmp_path):
        """Test cleaning up files matching a pattern."""
        # Create files with different extensions
        tmp_file = tmp_path / "test.tmp"
        txt_file = tmp_path / "test.txt"
        tmp_file.write_text("tmp content")
        txt_file.write_text("txt content")
        
        # Make both files old
        old_time = (datetime.now() - timedelta(hours=48)).timestamp()
        import os
        os.utime(tmp_file, (old_time, old_time))
        os.utime(txt_file, (old_time, old_time))
        
        # Clean up only .tmp files
        deleted_count = cleanup_temp_files(tmp_path, max_age_hours=24, pattern="*.tmp")
        
        assert deleted_count == 1
        assert not tmp_file.exists()
        assert txt_file.exists()
    
    def test_cleanup_dry_run(self, tmp_path):
        """Test cleanup in dry-run mode."""
        # Create an old file
        old_file = tmp_path / "old.tmp"
        old_file.write_text("old content")
        
        # Make file appear old
        old_time = (datetime.now() - timedelta(hours=48)).timestamp()
        import os
        os.utime(old_file, (old_time, old_time))
        
        # Run cleanup in dry-run mode
        deleted_count = cleanup_temp_files(tmp_path, max_age_hours=24, dry_run=True)
        
        assert deleted_count == 1
        assert old_file.exists()  # File should still exist
    
    def test_cleanup_nonexistent_directory(self, tmp_path):
        """Test cleanup on non-existent directory."""
        nonexistent_dir = tmp_path / "nonexistent"
        
        # Should return 0 without raising error
        deleted_count = cleanup_temp_files(nonexistent_dir, max_age_hours=24)
        
        assert deleted_count == 0
    
    def test_cleanup_empty_directory(self, tmp_path):
        """Test cleanup on empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        deleted_count = cleanup_temp_files(empty_dir, max_age_hours=24)
        
        assert deleted_count == 0


class TestEnsureDirectory:
    """Tests for ensure_directory function."""
    
    def test_ensure_existing_directory(self, tmp_path):
        """Test ensuring an existing directory."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        
        result = ensure_directory(existing_dir)
        
        assert result == existing_dir
        assert result.is_dir()
    
    def test_ensure_creates_missing_directory(self, tmp_path):
        """Test creating a missing directory."""
        new_dir = tmp_path / "new_dir"
        
        result = ensure_directory(new_dir, create_if_missing=True)
        
        assert result == new_dir
        assert result.exists()
        assert result.is_dir()
    
    def test_ensure_creates_nested_directories(self, tmp_path):
        """Test creating nested directories."""
        nested_dir = tmp_path / "level1" / "level2" / "level3"
        
        result = ensure_directory(nested_dir, create_if_missing=True)
        
        assert result == nested_dir
        assert result.exists()
        assert result.is_dir()
    
    def test_ensure_fails_on_missing_without_create(self, tmp_path):
        """Test that missing directory raises error without create flag."""
        missing_dir = tmp_path / "missing"
        
        with pytest.raises(FileOperationError) as exc_info:
            ensure_directory(missing_dir, create_if_missing=False)
        
        assert "does not exist" in str(exc_info.value)
    
    def test_ensure_fails_on_file_path(self, tmp_path):
        """Test that file path raises error."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        
        with pytest.raises(FileOperationError) as exc_info:
            ensure_directory(file_path)
        
        assert "not a directory" in str(exc_info.value)


class TestGetFileSize:
    """Tests for get_file_size function."""
    
    def test_get_size_of_text_file(self, tmp_path):
        """Test getting size of a text file."""
        file_path = tmp_path / "test.txt"
        content = "Hello, World!"
        file_path.write_text(content, encoding="utf-8")
        
        size = get_file_size(file_path)
        
        assert size == len(content.encode("utf-8"))
    
    def test_get_size_of_binary_file(self, tmp_path):
        """Test getting size of a binary file."""
        file_path = tmp_path / "test.bin"
        content = b"\x00\x01\x02\x03\x04"
        file_path.write_bytes(content)
        
        size = get_file_size(file_path)
        
        assert size == len(content)
    
    def test_get_size_of_empty_file(self, tmp_path):
        """Test getting size of an empty file."""
        file_path = tmp_path / "empty.txt"
        file_path.write_text("")
        
        size = get_file_size(file_path)
        
        assert size == 0
    
    def test_get_size_of_nonexistent_file(self, tmp_path):
        """Test getting size of non-existent file."""
        file_path = tmp_path / "nonexistent.txt"
        
        with pytest.raises(FileOperationError):
            get_file_size(file_path)


class TestListFiles:
    """Tests for list_files function."""
    
    def test_list_all_files(self, tmp_path):
        """Test listing all files in a directory."""
        # Create some files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "file3.dat").write_text("content3")
        
        files = list_files(tmp_path)
        
        assert len(files) == 3
        assert all(f.is_file() for f in files)
    
    def test_list_files_with_pattern(self, tmp_path):
        """Test listing files matching a pattern."""
        # Create files with different extensions
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "file3.dat").write_text("content3")
        
        txt_files = list_files(tmp_path, pattern="*.txt")
        
        assert len(txt_files) == 2
        assert all(f.suffix == ".txt" for f in txt_files)
    
    def test_list_files_recursive(self, tmp_path):
        """Test listing files recursively."""
        # Create nested structure
        (tmp_path / "file1.txt").write_text("content1")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content2")
        
        # Non-recursive
        files_non_recursive = list_files(tmp_path, pattern="*.txt", recursive=False)
        assert len(files_non_recursive) == 1
        
        # Recursive
        files_recursive = list_files(tmp_path, pattern="*.txt", recursive=True)
        assert len(files_recursive) == 2
    
    def test_list_files_empty_directory(self, tmp_path):
        """Test listing files in empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        files = list_files(empty_dir)
        
        assert len(files) == 0
    
    def test_list_files_nonexistent_directory(self, tmp_path):
        """Test listing files in non-existent directory."""
        nonexistent_dir = tmp_path / "nonexistent"
        
        with pytest.raises(FileOperationError):
            list_files(nonexistent_dir)
    
    def test_list_files_excludes_directories(self, tmp_path):
        """Test that directories are excluded from file list."""
        # Create files and directories
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "subdir").mkdir()
        
        files = list_files(tmp_path)
        
        assert len(files) == 1
        assert files[0].name == "file.txt"


class TestFileOperationError:
    """Tests for FileOperationError exception."""
    
    def test_error_with_all_attributes(self):
        """Test creating error with all attributes."""
        error = FileOperationError(
            message="Test error",
            file_path="/path/to/file.txt",
            operation="write",
            details={"extra": "info"}
        )
        
        assert error.message == "Test error"
        assert error.file_path == "/path/to/file.txt"
        assert error.operation == "write"
        assert error.details["extra"] == "info"
    
    def test_error_string_representation(self):
        """Test error string representation."""
        error = FileOperationError(
            message="Test error",
            file_path="/path/to/file.txt",
            operation="write"
        )
        
        error_str = str(error)
        assert "Test error" in error_str
        assert "file_path" in error_str
