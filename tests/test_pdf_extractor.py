"""
Unit tests for PDF text extraction tool.

Tests cover:
- Basic PDF text extraction
- Multi-page PDF handling
- Page tracking and metadata
- Formatting preservation
- Error handling for corrupted PDFs
- Batch extraction from multiple PDFs
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from pypdf.errors import PdfReadError

from tools.pdf_extractor import (
    extract_text_from_pdf,
    extract_text_from_multiple_pdfs,
    PDFExtractionError,
    _preserve_formatting,
    _is_list_item
)


class TestExtractTextFromPDF:
    """Tests for extract_text_from_pdf function."""
    
    def test_extract_from_real_pdf(self):
        """Test extraction from an actual IRS PDF document."""
        # Use one of the actual IRS PDFs in the knowledge base
        pdf_path = Path("rd_tax_agent/knowledge_base/CFR-2012-title26-vol1-sec1-41-4.pdf")
        
        if not pdf_path.exists():
            pytest.skip("IRS PDF not found in knowledge base")
        
        result = extract_text_from_pdf(str(pdf_path))
        
        # Verify result structure
        assert 'text' in result
        assert 'pages' in result
        assert 'total_pages' in result
        assert 'total_chars' in result
        assert 'file_path' in result
        assert 'metadata' in result
        
        # Verify content
        assert result['total_pages'] > 0
        assert result['total_chars'] > 0
        assert len(result['pages']) == result['total_pages']
        assert len(result['text']) > 0
        
        # Verify each page has required fields
        for page in result['pages']:
            assert 'page_number' in page
            assert 'text' in page
            assert 'char_count' in page
            assert page['page_number'] > 0
    
    def test_file_not_found(self):
        """Test error handling when PDF file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            extract_text_from_pdf("nonexistent_file.pdf")
    
    @patch('tools.pdf_extractor.PdfReader')
    def test_corrupted_pdf_handling(self, mock_reader):
        """Test error handling for corrupted PDF files."""
        # Mock PdfReader to raise PdfReadError
        mock_reader.side_effect = PdfReadError("Corrupted PDF")
        
        # Create a temporary file to pass the existence check
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            with pytest.raises(PDFExtractionError) as exc_info:
                extract_text_from_pdf(tmp_path)
            
            assert "Corrupted or invalid PDF" in str(exc_info.value)
        finally:
            Path(tmp_path).unlink()
    
    @patch('tools.pdf_extractor.PdfReader')
    def test_extract_with_metadata(self, mock_reader):
        """Test extraction with metadata included."""
        # Create mock PDF reader
        mock_pdf = MagicMock()
        mock_reader.return_value = mock_pdf
        
        # Mock metadata
        mock_metadata = {
            '/Title': 'Test Document',
            '/Author': 'IRS',
            '/Subject': 'Tax Regulations',
            '/Creator': 'Adobe',
            '/Producer': 'PDF Generator',
            '/CreationDate': 'D:20240101120000'
        }
        mock_pdf.metadata = mock_metadata
        
        # Mock pages
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Test content"
        mock_pdf.pages = [mock_page]
        
        # Create a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            result = extract_text_from_pdf(tmp_path, include_metadata=True)
            
            assert 'metadata' in result
            assert result['metadata']['title'] == 'Test Document'
            assert result['metadata']['author'] == 'IRS'
        finally:
            Path(tmp_path).unlink()
    
    @patch('tools.pdf_extractor.PdfReader')
    def test_extract_without_metadata(self, mock_reader):
        """Test extraction without metadata."""
        # Create mock PDF reader
        mock_pdf = MagicMock()
        mock_reader.return_value = mock_pdf
        
        # Mock pages
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Test content"
        mock_pdf.pages = [mock_page]
        
        # Create a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            result = extract_text_from_pdf(tmp_path, include_metadata=False)
            
            assert 'metadata' not in result
        finally:
            Path(tmp_path).unlink()
    
    @patch('tools.pdf_extractor.PdfReader')
    def test_multipage_extraction(self, mock_reader):
        """Test extraction from multi-page PDF."""
        # Create mock PDF reader
        mock_pdf = MagicMock()
        mock_reader.return_value = mock_pdf
        
        # Mock multiple pages
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"
        
        mock_page3 = MagicMock()
        mock_page3.extract_text.return_value = "Page 3 content"
        
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdf.metadata = None
        
        # Create a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            result = extract_text_from_pdf(tmp_path)
            
            assert result['total_pages'] == 3
            assert len(result['pages']) == 3
            
            # Verify page numbers are correct
            assert result['pages'][0]['page_number'] == 1
            assert result['pages'][1]['page_number'] == 2
            assert result['pages'][2]['page_number'] == 3
            
            # Verify text content
            assert "Page 1 content" in result['pages'][0]['text']
            assert "Page 2 content" in result['pages'][1]['text']
            assert "Page 3 content" in result['pages'][2]['text']
            
            # Verify full text contains all pages
            assert "Page 1 content" in result['text']
            assert "Page 2 content" in result['text']
            assert "Page 3 content" in result['text']
        finally:
            Path(tmp_path).unlink()
    
    @patch('tools.pdf_extractor.PdfReader')
    def test_empty_page_handling(self, mock_reader):
        """Test handling of pages with no extractable text."""
        # Create mock PDF reader
        mock_pdf = MagicMock()
        mock_reader.return_value = mock_pdf
        
        # Mock pages with one empty page
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = ""  # Empty page
        
        mock_page3 = MagicMock()
        mock_page3.extract_text.return_value = "Page 3 content"
        
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdf.metadata = None
        
        # Create a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            result = extract_text_from_pdf(tmp_path)
            
            assert result['total_pages'] == 3
            assert result['pages'][1]['text'] == ''
            assert result['pages'][1]['char_count'] == 0
        finally:
            Path(tmp_path).unlink()


class TestPreserveFormatting:
    """Tests for _preserve_formatting function."""
    
    def test_preserve_headings(self):
        """Test preservation of heading formatting."""
        text = "SECTION 1\nThis is regular text.\nSUBSECTION A\nMore text."
        result = _preserve_formatting(text)
        
        # Headings should have extra spacing
        assert "SECTION 1" in result
        assert "SUBSECTION A" in result
    
    def test_preserve_list_items(self):
        """Test preservation of list item formatting."""
        text = "• Item 1\n• Item 2\n1. Numbered item\na. Lettered item"
        result = _preserve_formatting(text)
        
        assert "• Item 1" in result
        assert "• Item 2" in result
        assert "1. Numbered item" in result
        assert "a. Lettered item" in result
    
    def test_empty_text(self):
        """Test handling of empty text."""
        result = _preserve_formatting("")
        assert result == ""
    
    def test_preserve_paragraph_breaks(self):
        """Test preservation of paragraph breaks."""
        text = "Paragraph 1\n\nParagraph 2\n\nParagraph 3"
        result = _preserve_formatting(text)
        
        # Should maintain empty lines
        assert "\n\n" in result


class TestIsListItem:
    """Tests for _is_list_item function."""
    
    def test_bullet_points(self):
        """Test detection of bullet point list items."""
        assert _is_list_item("• Item with bullet")
        assert _is_list_item("◦ Item with hollow bullet")
        assert _is_list_item("▪ Item with square bullet")
        assert _is_list_item("– Item with dash")
    
    def test_numbered_lists(self):
        """Test detection of numbered list items."""
        assert _is_list_item("1. First item")
        assert _is_list_item("2) Second item")
        assert _is_list_item("3: Third item")
        assert _is_list_item("10. Tenth item")
    
    def test_lettered_lists(self):
        """Test detection of lettered list items."""
        assert _is_list_item("a. First item")
        assert _is_list_item("b) Second item")
        assert _is_list_item("c: Third item")
    
    def test_parenthesized_items(self):
        """Test detection of parenthesized list items."""
        assert _is_list_item("(1) First item")
        assert _is_list_item("(a) Lettered item")
    
    def test_non_list_items(self):
        """Test that regular text is not detected as list items."""
        assert not _is_list_item("Regular text")
        assert not _is_list_item("This is a sentence.")
        assert not _is_list_item("")


class TestExtractTextFromMultiplePDFs:
    """Tests for extract_text_from_multiple_pdfs function."""
    
    def test_extract_multiple_real_pdfs(self):
        """Test extraction from multiple actual IRS PDFs."""
        # Get all text-based PDFs from knowledge base (3 of 4 are text-based)
        # Note: IRS Audit Guidelines for Software.pdf is scanned/image-based
        kb_path = Path("rd_tax_agent/knowledge_base")
        pdf_files = [
            kb_path / "CFR-2012-title26-vol1-sec1-41-4.pdf",
            kb_path / "Instructions for Form 6765.pdf",
            kb_path / "IRS Publication 542 (Corporations).pdf"
        ]
        
        # Filter to only existing files
        existing_files = [str(f) for f in pdf_files if f.exists()]
        
        if len(existing_files) < 2:
            pytest.skip("Not enough IRS PDFs found in knowledge base")
        
        result = extract_text_from_multiple_pdfs(existing_files)
        
        assert 'documents' in result
        assert 'successful' in result
        assert 'failed' in result
        assert 'errors' in result
        
        assert result['successful'] == len(existing_files)
        assert result['failed'] == 0
        assert len(result['documents']) == len(existing_files)
    
    @patch('tools.pdf_extractor.extract_text_from_pdf')
    def test_continue_on_error(self, mock_extract):
        """Test that processing continues when one PDF fails."""
        # Mock to succeed on first call, fail on second, succeed on third
        mock_extract.side_effect = [
            {'text': 'Doc 1', 'pages': [], 'total_pages': 1, 'total_chars': 5},
            PDFExtractionError("Corrupted PDF"),
            {'text': 'Doc 3', 'pages': [], 'total_pages': 1, 'total_chars': 5}
        ]
        
        pdf_files = ['doc1.pdf', 'doc2.pdf', 'doc3.pdf']
        result = extract_text_from_multiple_pdfs(pdf_files, continue_on_error=True)
        
        assert result['successful'] == 2
        assert result['failed'] == 1
        assert len(result['documents']) == 2
        assert len(result['errors']) == 1
        assert result['errors'][0]['file'] == 'doc2.pdf'
    
    @patch('tools.pdf_extractor.extract_text_from_pdf')
    def test_stop_on_error(self, mock_extract):
        """Test that processing stops when continue_on_error=False."""
        # Mock to succeed on first call, fail on second
        mock_extract.side_effect = [
            {'text': 'Doc 1', 'pages': [], 'total_pages': 1, 'total_chars': 5},
            PDFExtractionError("Corrupted PDF")
        ]
        
        pdf_files = ['doc1.pdf', 'doc2.pdf', 'doc3.pdf']
        
        with pytest.raises(PDFExtractionError):
            extract_text_from_multiple_pdfs(pdf_files, continue_on_error=False)
    
    def test_empty_list(self):
        """Test handling of empty PDF list."""
        result = extract_text_from_multiple_pdfs([])
        
        assert result['successful'] == 0
        assert result['failed'] == 0
        assert len(result['documents']) == 0
        assert len(result['errors']) == 0


class TestPDFExtractionIntegration:
    """Integration tests using actual IRS PDF documents."""
    
    def test_scanned_pdf_handling(self):
        """Test handling of scanned/image-based PDF (4th IRS document)."""
        pdf_path = Path("../knowledge_base/IRS Audit Guidelines for Software.pdf")
        
        if not pdf_path.exists():
            pytest.skip("IRS Audit Guidelines PDF not found")
        
        # This PDF is scanned/image-based, so we expect minimal or no text extraction
        result = extract_text_from_pdf(str(pdf_path))
        
        # The extraction should complete without errors
        assert 'text' in result
        assert 'pages' in result
        assert 'total_pages' in result
        
        # But we expect very little extractable text (it's a scanned PDF)
        # This is a documented limitation - OCR not included
        print(f"\nScanned PDF extracted {result['total_chars']} characters from {result['total_pages']} pages")
        print("Note: Low character count expected for scanned/image-based PDFs")
    
    def test_extract_cfr_document(self):
        """Test extraction from CFR Title 26 document."""
        pdf_path = Path("rd_tax_agent/knowledge_base/CFR-2012-title26-vol1-sec1-41-4.pdf")
        
        if not pdf_path.exists():
            pytest.skip("CFR PDF not found")
        
        result = extract_text_from_pdf(str(pdf_path))
        
        # Verify we got substantial content
        assert result['total_chars'] > 1000
        
        # Verify expected content (CFR documents should contain regulation text)
        text_lower = result['text'].lower()
        assert any(keyword in text_lower for keyword in ['research', 'qualified', 'section'])
    
    def test_extract_form_6765_instructions(self):
        """Test extraction from Form 6765 Instructions."""
        pdf_path = Path("rd_tax_agent/knowledge_base/Instructions for Form 6765.pdf")
        
        if not pdf_path.exists():
            pytest.skip("Form 6765 Instructions PDF not found")
        
        result = extract_text_from_pdf(str(pdf_path))
        
        # Verify we got substantial content
        assert result['total_chars'] > 1000
        
        # Verify expected content
        text_lower = result['text'].lower()
        assert any(keyword in text_lower for keyword in ['credit', 'research', 'form'])
    
    def test_page_tracking_accuracy(self):
        """Test that page tracking is accurate."""
        pdf_path = Path("rd_tax_agent/knowledge_base/CFR-2012-title26-vol1-sec1-41-4.pdf")
        
        if not pdf_path.exists():
            pytest.skip("CFR PDF not found")
        
        result = extract_text_from_pdf(str(pdf_path))
        
        # Verify page numbers are sequential
        for i, page in enumerate(result['pages'], start=1):
            assert page['page_number'] == i
        
        # Verify total character count matches sum of page counts
        total_from_pages = sum(p['char_count'] for p in result['pages'])
        assert result['total_chars'] == total_from_pages
