"""Tool modules for external integrations and utilities."""

from .pdf_extractor import (
    extract_text_from_pdf,
    extract_text_from_multiple_pdfs,
    PDFExtractionError
)

__all__ = [
    'extract_text_from_pdf',
    'extract_text_from_multiple_pdfs',
    'PDFExtractionError'
]
