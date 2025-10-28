"""
PDF Text Extraction Tool

This module provides functionality to extract text from PDF documents with page tracking
and formatting preservation. It is designed to work with IRS tax documents for the
R&D Tax Credit Automation Agent.

Requirements: 2.1
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from pypdf import PdfReader
from pypdf.errors import PdfReadError

# Configure logger
logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    """Custom exception for PDF extraction errors"""
    pass


def extract_text_from_pdf(
    pdf_path: str,
    preserve_formatting: bool = True,
    include_metadata: bool = True
) -> Dict[str, any]:
    """
    Extract text from a PDF file with page tracking and optional formatting preservation.
    
    This function reads a PDF file and extracts all text content, maintaining page
    boundaries and optionally preserving formatting elements like headings and lists.
    
    Args:
        pdf_path: Path to the PDF file (absolute or relative)
        preserve_formatting: If True, attempts to preserve headings and list structures
        include_metadata: If True, includes PDF metadata in the result
    
    Returns:
        Dictionary containing:
            - 'text': Full extracted text as a single string
            - 'pages': List of dictionaries, each containing:
                - 'page_number': Page number (1-indexed)
                - 'text': Text content of the page
                - 'char_count': Number of characters on the page
            - 'metadata': PDF metadata (if include_metadata=True)
            - 'total_pages': Total number of pages
            - 'total_chars': Total character count
            - 'file_path': Original file path
    
    Raises:
        PDFExtractionError: If the PDF cannot be read or is corrupted
        FileNotFoundError: If the PDF file does not exist
    
    Example:
        >>> result = extract_text_from_pdf('knowledge_base/tax_docs/form_6765.pdf')
        >>> print(f"Extracted {result['total_pages']} pages")
        >>> print(f"First page text: {result['pages'][0]['text'][:100]}")
    """
    # Validate file path
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if not pdf_file.is_file():
        raise PDFExtractionError(f"Path is not a file: {pdf_path}")
    
    logger.info(f"Starting PDF extraction from: {pdf_path}")
    
    try:
        # Open and read the PDF
        reader = PdfReader(str(pdf_file))
        
        # Extract metadata if requested
        metadata = {}
        if include_metadata:
            try:
                pdf_metadata = reader.metadata
                if pdf_metadata:
                    metadata = {
                        'title': pdf_metadata.get('/Title', ''),
                        'author': pdf_metadata.get('/Author', ''),
                        'subject': pdf_metadata.get('/Subject', ''),
                        'creator': pdf_metadata.get('/Creator', ''),
                        'producer': pdf_metadata.get('/Producer', ''),
                        'creation_date': str(pdf_metadata.get('/CreationDate', '')),
                    }
            except Exception as e:
                logger.warning(f"Could not extract metadata: {e}")
                metadata = {}
        
        # Extract text from each page
        pages = []
        full_text_parts = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                # Extract text from the page
                page_text = page.extract_text()
                
                if page_text:
                    # Apply formatting preservation if requested
                    if preserve_formatting:
                        page_text = _preserve_formatting(page_text)
                    
                    # Store page information
                    pages.append({
                        'page_number': page_num,
                        'text': page_text,
                        'char_count': len(page_text)
                    })
                    
                    full_text_parts.append(page_text)
                    
                    logger.debug(f"Extracted {len(page_text)} characters from page {page_num}")
                else:
                    logger.warning(f"No text extracted from page {page_num}")
                    pages.append({
                        'page_number': page_num,
                        'text': '',
                        'char_count': 0
                    })
            
            except Exception as e:
                logger.error(f"Error extracting text from page {page_num}: {e}")
                pages.append({
                    'page_number': page_num,
                    'text': '',
                    'char_count': 0,
                    'error': str(e)
                })
        
        # Combine all text
        full_text = '\n\n'.join(full_text_parts)
        total_chars = sum(p['char_count'] for p in pages)
        
        result = {
            'text': full_text,
            'pages': pages,
            'total_pages': len(reader.pages),
            'total_chars': total_chars,
            'file_path': str(pdf_file.absolute())
        }
        
        if include_metadata:
            result['metadata'] = metadata
        
        logger.info(
            f"Successfully extracted {total_chars} characters from "
            f"{len(reader.pages)} pages in {pdf_path}"
        )
        
        return result
    
    except PdfReadError as e:
        error_msg = f"Corrupted or invalid PDF file: {pdf_path}. Error: {e}"
        logger.error(error_msg)
        raise PDFExtractionError(error_msg) from e
    
    except Exception as e:
        error_msg = f"Unexpected error extracting PDF {pdf_path}: {e}"
        logger.error(error_msg)
        raise PDFExtractionError(error_msg) from e


def _preserve_formatting(text: str) -> str:
    """
    Apply basic formatting preservation to extracted text.
    
    This function attempts to preserve common formatting elements like:
    - Headings (lines in ALL CAPS or with specific patterns)
    - List items (lines starting with bullets, numbers, or letters)
    - Section breaks (multiple newlines)
    
    Args:
        text: Raw extracted text
    
    Returns:
        Text with improved formatting
    """
    if not text:
        return text
    
    lines = text.split('\n')
    formatted_lines = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if not stripped:
            # Preserve empty lines as paragraph breaks
            formatted_lines.append('')
            continue
        
        # Detect potential headings (all caps, short lines)
        if stripped.isupper() and len(stripped) < 100:
            # Add extra spacing before headings (except first line)
            if i > 0 and formatted_lines and formatted_lines[-1]:
                formatted_lines.append('')
            formatted_lines.append(stripped)
            formatted_lines.append('')
            continue
        
        # Detect list items
        if _is_list_item(stripped):
            formatted_lines.append(stripped)
            continue
        
        # Regular text
        formatted_lines.append(stripped)
    
    return '\n'.join(formatted_lines)


def _is_list_item(line: str) -> bool:
    """
    Check if a line appears to be a list item.
    
    Args:
        line: Text line to check
    
    Returns:
        True if the line appears to be a list item
    """
    if not line:
        return False
    
    # Check for common list markers
    list_markers = [
        '•', '◦', '▪', '▫', '–', '—',  # Bullet points
        '○', '●', '□', '■',  # Other bullets
    ]
    
    # Check if starts with bullet
    if any(line.startswith(marker) for marker in list_markers):
        return True
    
    # Check for numbered lists (1., 2., 10., etc.)
    # Find the first non-digit character
    first_non_digit = 0
    for i, char in enumerate(line):
        if not char.isdigit():
            first_non_digit = i
            break
    
    if first_non_digit > 0 and first_non_digit < len(line):
        if line[first_non_digit] in '.):':
            return True
    
    # Check for lettered lists (a., b., etc.)
    if len(line) > 2 and line[0].isalpha() and line[1] in '.):':
        return True
    
    # Check for parenthesized numbers/letters
    if line.startswith('(') and len(line) > 3:
        if line[1].isdigit() or line[1].isalpha():
            if line[2] == ')':
                return True
    
    return False


def extract_text_from_multiple_pdfs(
    pdf_paths: List[str],
    preserve_formatting: bool = True,
    include_metadata: bool = True,
    continue_on_error: bool = True
) -> Dict[str, any]:
    """
    Extract text from multiple PDF files.
    
    Args:
        pdf_paths: List of paths to PDF files
        preserve_formatting: If True, attempts to preserve formatting
        include_metadata: If True, includes PDF metadata
        continue_on_error: If True, continues processing even if some PDFs fail
    
    Returns:
        Dictionary containing:
            - 'documents': List of extraction results (one per PDF)
            - 'successful': Number of successfully processed PDFs
            - 'failed': Number of failed PDFs
            - 'errors': List of error messages for failed PDFs
    
    Example:
        >>> pdf_files = ['doc1.pdf', 'doc2.pdf', 'doc3.pdf']
        >>> results = extract_text_from_multiple_pdfs(pdf_files)
        >>> print(f"Processed {results['successful']} of {len(pdf_files)} files")
    """
    documents = []
    errors = []
    successful = 0
    failed = 0
    
    for pdf_path in pdf_paths:
        try:
            result = extract_text_from_pdf(
                pdf_path,
                preserve_formatting=preserve_formatting,
                include_metadata=include_metadata
            )
            documents.append(result)
            successful += 1
        
        except Exception as e:
            failed += 1
            error_info = {
                'file': pdf_path,
                'error': str(e)
            }
            errors.append(error_info)
            logger.error(f"Failed to extract {pdf_path}: {e}")
            
            if not continue_on_error:
                raise
    
    return {
        'documents': documents,
        'successful': successful,
        'failed': failed,
        'errors': errors
    }
