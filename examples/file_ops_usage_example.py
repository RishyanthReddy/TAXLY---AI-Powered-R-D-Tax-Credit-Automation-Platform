"""
Example usage of file operations utility.

This script demonstrates how to use the safe file operations utilities
for reading, writing, and managing files in the R&D Tax Credit Automation Agent.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.file_ops import (
    safe_write_file,
    safe_read_file,
    cleanup_temp_files,
    ensure_directory,
    get_file_size,
    list_files,
    FileOperationError
)


def example_safe_write():
    """Demonstrate safe atomic file writing."""
    print("\n=== Example: Safe Write File ===")
    
    # Write a text file
    output_path = Path("outputs/temp/example_output.txt")
    content = "This is a test file with important data.\nLine 2\nLine 3"
    
    try:
        safe_write_file(output_path, content, create_dirs=True)
        print(f"✓ Successfully wrote file: {output_path}")
        print(f"  Content: {len(content)} characters")
    except FileOperationError as e:
        print(f"✗ Failed to write file: {e}")
    
    # Write a binary file
    binary_path = Path("outputs/temp/example_binary.dat")
    binary_content = b"\x00\x01\x02\x03\x04\x05"
    
    try:
        safe_write_file(binary_path, binary_content, create_dirs=True)
        print(f"✓ Successfully wrote binary file: {binary_path}")
        print(f"  Content: {len(binary_content)} bytes")
    except FileOperationError as e:
        print(f"✗ Failed to write binary file: {e}")


def example_safe_read():
    """Demonstrate safe file reading with encoding detection."""
    print("\n=== Example: Safe Read File ===")
    
    # Read a text file with automatic encoding detection
    file_path = Path("outputs/temp/example_output.txt")
    
    try:
        content = safe_read_file(file_path, detect_encoding=True)
        print(f"✓ Successfully read file: {file_path}")
        print(f"  Content preview: {content[:50]}...")
        print(f"  Total length: {len(content)} characters")
    except FileOperationError as e:
        print(f"✗ Failed to read file: {e}")
    except FileNotFoundError:
        print(f"✗ File not found: {file_path}")
    
    # Read a binary file
    binary_path = Path("outputs/temp/example_binary.dat")
    
    try:
        binary_content = safe_read_file(binary_path, encoding=None, detect_encoding=False)
        print(f"✓ Successfully read binary file: {binary_path}")
        print(f"  Content: {binary_content.hex()}")
    except FileOperationError as e:
        print(f"✗ Failed to read binary file: {e}")


def example_cleanup_temp_files():
    """Demonstrate temporary file cleanup."""
    print("\n=== Example: Cleanup Temp Files ===")
    
    temp_dir = Path("outputs/temp")
    
    # First, show what would be deleted (dry run)
    print("\nDry run (preview):")
    try:
        count = cleanup_temp_files(
            temp_dir,
            max_age_hours=24,
            pattern="*.txt",
            dry_run=True
        )
        print(f"  Would delete {count} files")
    except FileOperationError as e:
        print(f"✗ Cleanup failed: {e}")
    
    # Actually clean up old files
    print("\nActual cleanup:")
    try:
        count = cleanup_temp_files(
            temp_dir,
            max_age_hours=24,
            pattern="*.txt",
            dry_run=False
        )
        print(f"✓ Deleted {count} temporary files")
    except FileOperationError as e:
        print(f"✗ Cleanup failed: {e}")


def example_directory_management():
    """Demonstrate directory management utilities."""
    print("\n=== Example: Directory Management ===")
    
    # Ensure a directory exists
    output_dir = Path("outputs/reports/2024")
    
    try:
        result = ensure_directory(output_dir, create_if_missing=True)
        print(f"✓ Directory ensured: {result}")
    except FileOperationError as e:
        print(f"✗ Failed to ensure directory: {e}")
    
    # List files in a directory
    try:
        files = list_files("outputs", pattern="*.txt", recursive=True)
        print(f"✓ Found {len(files)} .txt files in outputs/")
        for file in files[:5]:  # Show first 5
            print(f"  - {file}")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")
    except FileOperationError as e:
        print(f"✗ Failed to list files: {e}")


def example_file_info():
    """Demonstrate getting file information."""
    print("\n=== Example: File Information ===")
    
    file_path = Path("outputs/temp/example_output.txt")
    
    try:
        size = get_file_size(file_path)
        print(f"✓ File size: {size} bytes ({size / 1024:.2f} KB)")
    except FileOperationError as e:
        print(f"✗ Failed to get file size: {e}")


def example_error_handling():
    """Demonstrate error handling."""
    print("\n=== Example: Error Handling ===")
    
    # Try to read a non-existent file
    try:
        content = safe_read_file("nonexistent_file.txt")
        print(f"Content: {content}")
    except FileNotFoundError as e:
        print(f"✓ Caught FileNotFoundError: {e}")
    except FileOperationError as e:
        print(f"✓ Caught FileOperationError: {e}")
        print(f"  Operation: {e.operation}")
        print(f"  File path: {e.file_path}")
    
    # Try to write to an invalid location (if permissions are restricted)
    try:
        safe_write_file("/root/protected.txt", "content", create_dirs=False)
    except FileOperationError as e:
        print(f"✓ Caught FileOperationError: {e.message}")


def main():
    """Run all examples."""
    print("=" * 60)
    print("File Operations Utility - Usage Examples")
    print("=" * 60)
    
    # Run examples
    example_safe_write()
    example_safe_read()
    example_directory_management()
    example_file_info()
    example_cleanup_temp_files()
    example_error_handling()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
