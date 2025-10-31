"""
Test script to verify dashboard backend data loading
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import get_config
from utils.logger import AgentLogger

logger = AgentLogger.get_logger(__name__)

def test_reports_directory():
    """Test that reports directory exists and contains PDFs"""
    print("\n=== Testing Reports Directory ===")
    
    config = get_config()
    reports_dir = config.output_dir / "reports"
    
    # Also check absolute path
    abs_reports_dir = Path(__file__).parent / "outputs" / "reports"
    
    print(f"Reports directory (config): {reports_dir}")
    print(f"Reports directory (absolute): {abs_reports_dir}")
    print(f"Config dir exists: {reports_dir.exists()}")
    print(f"Absolute dir exists: {abs_reports_dir.exists()}")
    
    # Use whichever exists
    if abs_reports_dir.exists():
        reports_dir = abs_reports_dir
    
    if reports_dir.exists():
        pdf_files = list(reports_dir.glob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files")
        
        for pdf in pdf_files[:5]:  # Show first 5
            stats = pdf.stat()
            print(f"  - {pdf.name} ({stats.st_size} bytes)")
    
    return reports_dir.exists()

def test_sample_qualified_projects():
    """Test loading sample qualified projects"""
    print("\n=== Testing Sample Qualified Projects ===")
    
    fixtures_path = Path(__file__).parent / "tests" / "fixtures" / "sample_qualified_projects.json"
    print(f"Fixtures path: {fixtures_path}")
    print(f"Exists: {fixtures_path.exists()}")
    
    if fixtures_path.exists():
        with open(fixtures_path, 'r') as f:
            projects = json.load(f)
        
        print(f"Loaded {len(projects)} projects")
        
        # Calculate metrics
        total_hours = sum(p.get('qualified_hours', 0) for p in projects)
        total_cost = sum(p.get('qualified_cost', 0) for p in projects)
        estimated_credit = total_cost * 0.20
        avg_confidence = sum(p.get('confidence_score', 0) for p in projects) / len(projects) if projects else 0
        
        print(f"\nMetrics:")
        print(f"  Total Projects: {len(projects)}")
        print(f"  Total Qualified Hours: {total_hours:.2f}")
        print(f"  Total Qualified Cost: ${total_cost:.2f}")
        print(f"  Estimated Credit: ${estimated_credit:.2f}")
        print(f"  Average Confidence: {avg_confidence * 100:.1f}%")
        
        return True
    
    return False

def test_list_reports_logic():
    """Test the logic from /api/reports/list endpoint"""
    print("\n=== Testing List Reports Logic ===")
    
    config = get_config()
    reports_dir = config.output_dir / "reports"
    
    # Also check absolute path
    abs_reports_dir = Path(__file__).parent / "outputs" / "reports"
    
    if abs_reports_dir.exists():
        reports_dir = abs_reports_dir
    
    if not reports_dir.exists():
        print(f"Reports directory does not exist: {reports_dir}")
        return False
    
    reports = []
    
    for pdf_path in reports_dir.rglob("*.pdf"):
        if not pdf_path.is_file():
            continue
        
        try:
            # Get file stats
            file_stats = pdf_path.stat()
            file_size = file_stats.st_size
            
            # Parse filename
            filename = pdf_path.name
            report_id = filename.replace('.pdf', '')
            
            # Try to parse standard format
            import re
            from datetime import datetime
            
            match = re.match(r'rd_tax_credit_report_(\d{4})_(\d{8})_(\d{6})\.pdf', filename)
            if match:
                tax_year = int(match.group(1))
                date_str = match.group(2)
                time_str = match.group(3)
                
                year = date_str[0:4]
                month = date_str[4:6]
                day = date_str[6:8]
                hour = time_str[0:2]
                minute = time_str[2:4]
                second = time_str[4:6]
                
                generation_date = f"{year}-{month}-{day}T{hour}:{minute}:{second}"
                report_id = f"{tax_year}_{date_str}_{time_str}"
            else:
                generation_date = datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                tax_year = datetime.now().year
            
            reports.append({
                "id": report_id,
                "filename": filename,
                "fileSize": file_size,
                "generationDate": generation_date,
                "taxYear": tax_year,
                "companyName": "Acme Corporation",
                "status": "complete"
            })
            
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            continue
    
    # Sort by generation date (newest first)
    reports.sort(key=lambda r: r["generationDate"], reverse=True)
    
    print(f"Found {len(reports)} reports")
    
    if reports:
        print("\nFirst 3 reports:")
        for report in reports[:3]:
            print(f"  - {report['filename']}")
            print(f"    ID: {report['id']}")
            print(f"    Size: {report['fileSize']} bytes")
            print(f"    Date: {report['generationDate']}")
    
    return len(reports) > 0

def main():
    """Run all tests"""
    print("=" * 60)
    print("Dashboard Backend Data Loading Tests")
    print("=" * 60)
    
    results = {
        "reports_directory": test_reports_directory(),
        "sample_projects": test_sample_qualified_projects(),
        "list_reports_logic": test_list_reports_logic()
    }
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    print("\n" + ("=" * 60))
    print(f"Overall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
