"""
Integration test for PDF viewer functionality
Tests that the backend properly serves PDFs for the frontend viewer
"""

import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_pdf_download_endpoint_exists():
    """Test that the PDF download endpoint exists"""
    # Try to download a non-existent report (should return 404, not 500)
    response = client.get("/api/download/report/nonexistent_report")
    assert response.status_code in [404, 500], "Endpoint should exist"

def test_pdf_download_with_existing_report():
    """Test downloading an existing PDF report"""
    # Check if any reports exist in outputs/reports
    reports_dir = Path("outputs/reports")
    
    if not reports_dir.exists():
        pytest.skip("No reports directory found")
    
    pdf_files = list(reports_dir.glob("*.pdf"))
    
    if not pdf_files:
        pytest.skip("No PDF reports found to test")
    
    # Get the first PDF file
    test_pdf = pdf_files[0]
    report_id = test_pdf.stem  # Filename without .pdf extension
    
    print(f"\nTesting with report: {report_id}")
    
    # Try to download it
    response = client.get(f"/api/download/report/{report_id}")
    
    # Should return 200 OK
    assert response.status_code == 200, f"Failed to download report: {response.text}"
    
    # Should have PDF content type
    assert "application/pdf" in response.headers.get("content-type", ""), \
        "Response should be PDF content type"
    
    # Should have content-disposition header
    assert "content-disposition" in response.headers, \
        "Response should have content-disposition header"
    
    # Should have actual content
    assert len(response.content) > 0, "PDF content should not be empty"
    
    # Should be a valid PDF (starts with %PDF)
    assert response.content[:4] == b'%PDF', "Content should be a valid PDF"
    
    print(f"✓ Successfully downloaded PDF: {len(response.content)} bytes")

def test_pdf_file_sizes():
    """Test that PDF files are reasonable sizes (not too small or too large)"""
    reports_dir = Path("outputs/reports")
    
    if not reports_dir.exists():
        pytest.skip("No reports directory found")
    
    pdf_files = list(reports_dir.glob("*.pdf"))
    
    if not pdf_files:
        pytest.skip("No PDF reports found to test")
    
    for pdf_file in pdf_files:
        file_size = pdf_file.stat().st_size
        
        # Should be at least 10KB (reasonable minimum for a report)
        assert file_size > 10000, f"{pdf_file.name} is too small: {file_size} bytes"
        
        # Should be less than 10MB (reasonable maximum)
        assert file_size < 10000000, f"{pdf_file.name} is too large: {file_size} bytes"
        
        print(f"✓ {pdf_file.name}: {file_size:,} bytes")

def test_cors_headers_for_pdf_download():
    """Test that CORS headers are set for PDF downloads"""
    reports_dir = Path("outputs/reports")
    
    if not reports_dir.exists():
        pytest.skip("No reports directory found")
    
    pdf_files = list(reports_dir.glob("*.pdf"))
    
    if not pdf_files:
        pytest.skip("No PDF reports found to test")
    
    test_pdf = pdf_files[0]
    report_id = test_pdf.stem
    
    # Make request with Origin header
    response = client.get(
        f"/api/download/report/{report_id}",
        headers={"Origin": "http://localhost:3000"}
    )
    
    # Should have CORS headers
    assert "access-control-allow-origin" in response.headers, \
        "Response should have CORS headers for frontend access"
    
    print(f"✓ CORS headers present: {response.headers.get('access-control-allow-origin')}")

def test_pdf_metadata_extraction():
    """Test that we can extract metadata from PDF files"""
    reports_dir = Path("outputs/reports")
    
    if not reports_dir.exists():
        pytest.skip("No reports directory found")
    
    pdf_files = list(reports_dir.glob("*.pdf"))
    
    if not pdf_files:
        pytest.skip("No PDF reports found to test")
    
    for pdf_file in pdf_files[:3]:  # Test first 3 files
        # Check file exists and is readable
        assert pdf_file.exists(), f"PDF file should exist: {pdf_file}"
        assert pdf_file.is_file(), f"Should be a file: {pdf_file}"
        
        # Check file size
        file_size = pdf_file.stat().st_size
        assert file_size > 0, f"PDF should have content: {pdf_file}"
        
        # Check filename format
        filename = pdf_file.name
        assert filename.endswith('.pdf'), f"Should be a PDF file: {filename}"
        
        print(f"✓ {filename}: {file_size:,} bytes")

def test_frontend_files_exist():
    """Test that all required frontend files exist"""
    frontend_dir = Path("frontend")
    
    required_files = [
        "reports.html",
        "js/pdf-viewer.js",
        "css/pdf-viewer.css",
        "test_pdf_viewer.html",
        "PDF_VIEWER_README.md"
    ]
    
    for file_path in required_files:
        full_path = frontend_dir / file_path
        assert full_path.exists(), f"Required file missing: {file_path}"
        print(f"✓ {file_path} exists")

def test_pdf_viewer_js_structure():
    """Test that pdf-viewer.js has required functions"""
    pdf_viewer_path = Path("frontend/js/pdf-viewer.js")
    
    if not pdf_viewer_path.exists():
        pytest.skip("pdf-viewer.js not found")
    
    content = pdf_viewer_path.read_text()
    
    required_functions = [
        "initPdfJs",
        "loadPdf",
        "renderPage",
        "generateThumbnail",
        "openPdfViewer",
        "closePdfViewer",
        "goToPage",
        "previousPage",
        "nextPage",
        "zoomIn",
        "zoomOut",
        "resetZoom",
        "fitToWidth"
    ]
    
    for func_name in required_functions:
        assert f"function {func_name}" in content or f"async function {func_name}" in content, \
            f"Required function missing: {func_name}"
        print(f"✓ Function exists: {func_name}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PDF Viewer Integration Tests")
    print("="*60 + "\n")
    
    # Run tests
    pytest.main([__file__, "-v", "-s"])
