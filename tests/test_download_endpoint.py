"""
Unit tests for report download endpoint.

Tests the GET /api/download/report/{report_id} endpoint functionality including:
- Valid report download
- Invalid report_id handling
- File not found scenarios
- Path traversal security checks
- File streaming response

Requirements: 4.5, Testing
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import shutil

from main import app
from utils.config import get_config


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def temp_reports_dir():
    """
    Create a temporary reports directory with sample PDF files.
    
    Yields:
        Path: Path to temporary reports directory
    """
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    reports_dir = Path(temp_dir) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample PDF files
    sample_pdf_1 = reports_dir / "report_20240115_123456.pdf"
    sample_pdf_1.write_text("%PDF-1.4\nSample PDF content for testing")
    
    sample_pdf_2 = reports_dir / "rd_tax_credit_report_RPT-2024-001_20240115.pdf"
    sample_pdf_2.write_text("%PDF-1.4\nAnother sample PDF")
    
    # Create subdirectory with report
    subdir = reports_dir / "2024"
    subdir.mkdir(exist_ok=True)
    sample_pdf_3 = subdir / "report_20240201_654321.pdf"
    sample_pdf_3.write_text("%PDF-1.4\nSubdirectory PDF")
    
    yield reports_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


def test_download_valid_report(client, temp_reports_dir, monkeypatch):
    """
    Test downloading a valid report file.
    
    Verifies:
    - 200 OK status code
    - Correct Content-Type header
    - Correct Content-Disposition header
    - File content is returned
    """
    # Mock the config to use temp directory
    def mock_get_config():
        config = get_config()
        config.output_dir = temp_reports_dir.parent
        return config
    
    monkeypatch.setattr("main.get_config", mock_get_config)
    
    # Test download with exact filename
    response = client.get("/api/download/report/report_20240115_123456.pdf")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert "report_20240115_123456.pdf" in response.headers["content-disposition"]
    assert b"%PDF" in response.content


def test_download_report_without_extension(client, temp_reports_dir, monkeypatch):
    """
    Test downloading a report using ID without .pdf extension.
    
    Verifies:
    - Endpoint automatically adds .pdf extension
    - File is found and returned correctly
    """
    # Mock the config to use temp directory
    def mock_get_config():
        config = get_config()
        config.output_dir = temp_reports_dir.parent
        return config
    
    monkeypatch.setattr("main.get_config", mock_get_config)
    
    # Test download without extension
    response = client.get("/api/download/report/report_20240115_123456")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_download_report_with_pattern_match(client, temp_reports_dir, monkeypatch):
    """
    Test downloading a report using partial ID that matches a pattern.
    
    Verifies:
    - Endpoint can find files with complex naming patterns
    - Pattern matching works correctly
    """
    # Mock the config to use temp directory
    def mock_get_config():
        config = get_config()
        config.output_dir = temp_reports_dir.parent
        return config
    
    monkeypatch.setattr("main.get_config", mock_get_config)
    
    # Test download with partial ID
    response = client.get("/api/download/report/RPT-2024-001")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_download_report_from_subdirectory(client, temp_reports_dir, monkeypatch):
    """
    Test downloading a report from a subdirectory.
    
    Verifies:
    - Recursive search finds files in subdirectories
    - File is returned correctly
    """
    # Mock the config to use temp directory
    def mock_get_config():
        config = get_config()
        config.output_dir = temp_reports_dir.parent
        return config
    
    monkeypatch.setattr("main.get_config", mock_get_config)
    
    # Test download from subdirectory
    response = client.get("/api/download/report/report_20240201_654321")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_download_nonexistent_report(client, temp_reports_dir, monkeypatch):
    """
    Test downloading a report that doesn't exist.
    
    Verifies:
    - 404 Not Found status code
    - Appropriate error message
    """
    # Mock the config to use temp directory
    def mock_get_config():
        config = get_config()
        config.output_dir = temp_reports_dir.parent
        return config
    
    monkeypatch.setattr("main.get_config", mock_get_config)
    
    # Test download of nonexistent report
    response = client.get("/api/download/report/nonexistent_report_12345")
    
    assert response.status_code == 404
    response_json = response.json()
    # HTTPException handler returns 'message' field
    assert "message" in response_json, f"Expected 'message' field in response: {response_json}"
    assert "not found" in response_json["message"].lower()


def test_download_empty_report_id(client):
    """
    Test downloading with empty report_id.
    
    Verifies:
    - 400 Bad Request status code
    - Appropriate error message
    """
    # Test with empty report_id
    response = client.get("/api/download/report/   ")
    
    assert response.status_code == 400
    response_json = response.json()
    # HTTPException handler returns 'message' field
    assert "message" in response_json, f"Expected 'message' field in response: {response_json}"
    assert "cannot be empty" in response_json["message"].lower()


def test_download_path_traversal_attempt(client, temp_reports_dir, monkeypatch):
    """
    Test security against path traversal attacks.
    
    Verifies:
    - Path traversal attempts are sanitized
    - Files outside reports directory cannot be accessed
    """
    # Mock the config to use temp directory
    def mock_get_config():
        config = get_config()
        config.output_dir = temp_reports_dir.parent
        return config
    
    monkeypatch.setattr("main.get_config", mock_get_config)
    
    # Test path traversal attempts
    malicious_ids = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "../../sensitive_file.txt",
    ]
    
    for malicious_id in malicious_ids:
        response = client.get(f"/api/download/report/{malicious_id}")
        
        # Should either return 404 (file not found after sanitization)
        # or 403 (access denied)
        assert response.status_code in [404, 403]


def test_download_response_headers(client, temp_reports_dir, monkeypatch):
    """
    Test that response headers are set correctly.
    
    Verifies:
    - Content-Type is application/pdf
    - Content-Disposition includes attachment and filename
    - Cache-Control headers prevent caching
    """
    # Mock the config to use temp directory
    def mock_get_config():
        config = get_config()
        config.output_dir = temp_reports_dir.parent
        return config
    
    monkeypatch.setattr("main.get_config", mock_get_config)
    
    response = client.get("/api/download/report/report_20240115_123456")
    
    assert response.status_code == 200
    
    # Check Content-Type
    assert response.headers["content-type"] == "application/pdf"
    
    # Check Content-Disposition
    content_disposition = response.headers["content-disposition"]
    assert "attachment" in content_disposition
    assert "filename=" in content_disposition
    
    # Check Cache-Control headers
    assert "cache-control" in response.headers
    assert "no-cache" in response.headers["cache-control"].lower()


def test_download_file_content_integrity(client, temp_reports_dir, monkeypatch):
    """
    Test that downloaded file content matches original file.
    
    Verifies:
    - File content is not corrupted during download
    - Complete file is returned
    """
    # Mock the config to use temp directory
    def mock_get_config():
        config = get_config()
        config.output_dir = temp_reports_dir.parent
        return config
    
    monkeypatch.setattr("main.get_config", mock_get_config)
    
    # Read original file content
    original_file = temp_reports_dir / "report_20240115_123456.pdf"
    original_content = original_file.read_bytes()
    
    # Download file
    response = client.get("/api/download/report/report_20240115_123456")
    
    assert response.status_code == 200
    assert response.content == original_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
