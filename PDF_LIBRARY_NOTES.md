# PDF Generation Library Notes

## WeasyPrint Replacement

### Issue
WeasyPrint had compatibility issues on Windows due to missing GTK libraries (libgobject-2.0-0). This is a known limitation of WeasyPrint on Windows systems.

### Solution
Replaced WeasyPrint with **xhtml2pdf** (version 0.2.17), which is:
- Pure Python with no external system dependencies
- Fully compatible with Windows, macOS, and Linux
- Capable of HTML-to-PDF conversion like WeasyPrint
- Well-maintained and actively developed

### Installed Libraries

1. **ReportLab 4.4.4** (upgraded from 4.2.5)
   - Primary PDF generation library
   - Low-level programmatic PDF creation
   - Excellent for structured reports with precise layout control

2. **xhtml2pdf 0.2.17** (replaced WeasyPrint 63.1)
   - HTML-to-PDF conversion
   - Supports CSS styling
   - Great for template-based PDF generation
   - No external dependencies required

3. **Pillow 11.0.0**
   - Image handling and manipulation
   - Required for embedding images in PDFs
   - Supports multiple image formats

### Usage Recommendations

**Use ReportLab when:**
- You need precise control over PDF layout
- Creating structured reports with tables and charts
- Building PDFs programmatically from data

**Use xhtml2pdf when:**
- Converting HTML templates to PDF
- Leveraging CSS for styling
- Working with web-based content

### Testing
All libraries have been tested and verified working correctly. See `test_pdf_libs.py` for validation tests.

### Updated Files
- `requirements.txt` - Updated dependencies
- `.kiro/specs/rd-tax-credit-automation/design.md` - Updated design documentation
- `.kiro/specs/rd-tax-credit-automation/tasks.md` - Updated task documentation
