"""
PDF Report Verification Script

This script helps verify that generated PDF reports contain all required
information and meet audit-ready standards.

Usage:
    python verify_pdf_reports.py [report_path]
    
    If no report_path provided, verifies all reports in outputs/reports/
"""

import sys
from pathlib import Path
from datetime import datetime
import json

# Try to import PyPDF2 for PDF reading
try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    print("Warning: PyPDF2 not installed. Install with: pip install PyPDF2")
    print("Verification will be limited without PDF reading capability.\n")


def verify_pdf_structure(pdf_path: Path) -> dict:
    """
    Verify the structure and content of a PDF report.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary with verification results
    """
    results = {
        'file_path': str(pdf_path),
        'file_name': pdf_path.name,
        'file_exists': pdf_path.exists(),
        'file_size': 0,
        'page_count': 0,
        'has_metadata': False,
        'metadata': {},
        'checks': {},
        'issues': [],
        'warnings': []
    }
    
    if not pdf_path.exists():
        results['issues'].append(f"File not found: {pdf_path}")
        return results
    
    # Get file size
    results['file_size'] = pdf_path.stat().st_size
    results['file_size_kb'] = round(results['file_size'] / 1024, 2)
    
    # Check file size is reasonable
    if results['file_size'] < 1000:
        results['warnings'].append("File size is very small (< 1 KB)")
    elif results['file_size'] > 10_000_000:
        results['warnings'].append("File size is very large (> 10 MB)")
    
    if not HAS_PYPDF2:
        results['warnings'].append("PyPDF2 not available - limited verification")
        return results
    
    try:
        # Read PDF
        reader = PdfReader(str(pdf_path))
        results['page_count'] = len(reader.pages)
        
        # Check page count
        if results['page_count'] < 3:
            results['issues'].append(f"Too few pages: {results['page_count']} (expected at least 3)")
        
        # Get metadata
        if reader.metadata:
            results['has_metadata'] = True
            results['metadata'] = {
                'title': reader.metadata.get('/Title', 'N/A'),
                'author': reader.metadata.get('/Author', 'N/A'),
                'subject': reader.metadata.get('/Subject', 'N/A'),
                'creator': reader.metadata.get('/Creator', 'N/A'),
                'producer': reader.metadata.get('/Producer', 'N/A'),
                'creation_date': reader.metadata.get('/CreationDate', 'N/A')
            }
        
        # Extract text from first few pages for verification
        page_texts = []
        for i in range(min(5, results['page_count'])):
            try:
                text = reader.pages[i].extract_text()
                page_texts.append(text)
            except Exception as e:
                results['warnings'].append(f"Could not extract text from page {i+1}: {e}")
        
        # Verify cover page (page 1)
        if page_texts:
            cover_text = page_texts[0].lower()
            results['checks']['has_title'] = 'r&d tax credit' in cover_text or 'audit report' in cover_text
            results['checks']['has_tax_year'] = 'tax year' in cover_text
            results['checks']['has_report_id'] = 'report id' in cover_text or 'rpt-' in cover_text
            
            if not results['checks']['has_title']:
                results['issues'].append("Cover page missing report title")
            if not results['checks']['has_tax_year']:
                results['warnings'].append("Cover page may be missing tax year")
        
        # Verify TOC (page 2)
        if len(page_texts) > 1:
            toc_text = page_texts[1].lower()
            results['checks']['has_toc'] = 'table of contents' in toc_text or 'contents' in toc_text
            
            if not results['checks']['has_toc']:
                results['warnings'].append("Page 2 may not be table of contents")
        
        # Verify Executive Summary (page 3)
        if len(page_texts) > 2:
            exec_text = page_texts[2].lower()
            results['checks']['has_executive_summary'] = 'executive summary' in exec_text
            results['checks']['has_qualified_cost'] = 'qualified cost' in exec_text
            results['checks']['has_estimated_credit'] = 'estimated credit' in exec_text or 'estimated r&d' in exec_text
            
            if not results['checks']['has_executive_summary']:
                results['warnings'].append("Page 3 may not be executive summary")
            if not results['checks']['has_qualified_cost']:
                results['warnings'].append("Executive summary may be missing qualified cost")
            if not results['checks']['has_estimated_credit']:
                results['warnings'].append("Executive summary may be missing estimated credit")
        
        # Check for project sections
        all_text = ' '.join(page_texts).lower()
        results['checks']['has_project_sections'] = 'project' in all_text and 'qualified hours' in all_text
        results['checks']['has_irs_citation'] = 'irs' in all_text or 'cfr' in all_text
        results['checks']['has_reasoning'] = 'reasoning' in all_text or 'qualification' in all_text
        
        if not results['checks']['has_project_sections']:
            results['issues'].append("No project sections found")
        if not results['checks']['has_irs_citation']:
            results['warnings'].append("No IRS citations found")
        if not results['checks']['has_reasoning']:
            results['warnings'].append("No qualification reasoning found")
        
    except Exception as e:
        results['issues'].append(f"Error reading PDF: {str(e)}")
    
    return results


def print_verification_results(results: dict):
    """Print verification results in a readable format."""
    print(f"\n{'='*80}")
    print(f"PDF VERIFICATION REPORT")
    print(f"{'='*80}")
    print(f"\nFile: {results['file_name']}")
    print(f"Path: {results['file_path']}")
    print(f"Size: {results['file_size_kb']} KB")
    print(f"Pages: {results['page_count']}")
    
    if results['has_metadata']:
        print(f"\nMetadata:")
        for key, value in results['metadata'].items():
            print(f"  {key}: {value}")
    
    if results['checks']:
        print(f"\nStructure Checks:")
        for check, passed in results['checks'].items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check.replace('_', ' ').title()}")
    
    if results['issues']:
        print(f"\n❌ ISSUES FOUND ({len(results['issues'])}):")
        for issue in results['issues']:
            print(f"  - {issue}")
    
    if results['warnings']:
        print(f"\n⚠️  WARNINGS ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"  - {warning}")
    
    if not results['issues'] and not results['warnings']:
        print(f"\n✅ All checks passed!")
    
    print(f"\n{'='*80}\n")


def verify_all_reports(reports_dir: Path):
    """Verify all PDF reports in a directory."""
    pdf_files = list(reports_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {reports_dir}")
        return
    
    print(f"\nFound {len(pdf_files)} PDF report(s) to verify\n")
    
    all_results = []
    for pdf_file in pdf_files:
        results = verify_pdf_structure(pdf_file)
        all_results.append(results)
        print_verification_results(results)
    
    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total reports verified: {len(all_results)}")
    
    reports_with_issues = sum(1 for r in all_results if r['issues'])
    reports_with_warnings = sum(1 for r in all_results if r['warnings'])
    reports_clean = len(all_results) - reports_with_issues - reports_with_warnings
    
    print(f"Reports with issues: {reports_with_issues}")
    print(f"Reports with warnings: {reports_with_warnings}")
    print(f"Reports clean: {reports_clean}")
    
    if reports_with_issues == 0:
        print(f"\n✅ All reports passed verification!")
    else:
        print(f"\n❌ {reports_with_issues} report(s) have issues that need attention")
    
    print(f"{'='*80}\n")
    
    # Save results to JSON
    results_file = reports_dir / "verification_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            'verification_date': datetime.now().isoformat(),
            'total_reports': len(all_results),
            'reports_with_issues': reports_with_issues,
            'reports_with_warnings': reports_with_warnings,
            'reports_clean': reports_clean,
            'results': all_results
        }, f, indent=2)
    
    print(f"Detailed results saved to: {results_file}\n")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Verify specific file
        pdf_path = Path(sys.argv[1])
        results = verify_pdf_structure(pdf_path)
        print_verification_results(results)
    else:
        # Verify all reports in outputs/reports/
        reports_dir = Path("outputs/reports")
        if not reports_dir.exists():
            print(f"Reports directory not found: {reports_dir}")
            print("Please run from the rd_tax_agent directory")
            sys.exit(1)
        
        verify_all_reports(reports_dir)


if __name__ == "__main__":
    main()
