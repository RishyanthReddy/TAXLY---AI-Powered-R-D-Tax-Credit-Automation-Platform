"""
PDF Extractor Usage Examples

This module demonstrates how to use the PDF text extraction tool
for processing IRS tax documents.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.pdf_extractor import (
    extract_text_from_pdf,
    extract_text_from_multiple_pdfs,
    PDFExtractionError
)


def example_basic_extraction():
    """Example 1: Basic PDF text extraction."""
    print("Example 1: Basic PDF Text Extraction")
    print("=" * 60)
    
    # Extract text from a single PDF
    pdf_path = "../knowledge_base/CFR-2012-title26-vol1-sec1-41-4.pdf"
    
    try:
        result = extract_text_from_pdf(pdf_path)
        
        print(f"Successfully extracted text from: {Path(pdf_path).name}")
        print(f"Total pages: {result['total_pages']}")
        print(f"Total characters: {result['total_chars']:,}")
        print(f"\nFirst 200 characters:")
        print(result['text'][:200])
        
    except FileNotFoundError:
        print(f"Error: PDF file not found at {pdf_path}")
    except PDFExtractionError as e:
        print(f"Error extracting PDF: {e}")


def example_with_metadata():
    """Example 2: Extract text with metadata."""
    print("\n\nExample 2: Extract Text with Metadata")
    print("=" * 60)
    
    pdf_path = "../knowledge_base/Instructions for Form 6765.pdf"
    
    try:
        result = extract_text_from_pdf(
            pdf_path,
            preserve_formatting=True,
            include_metadata=True
        )
        
        print(f"Document: {Path(pdf_path).name}")
        
        if 'metadata' in result:
            print("\nMetadata:")
            for key, value in result['metadata'].items():
                if value:
                    print(f"  {key}: {value}")
        
        print(f"\nContent Statistics:")
        print(f"  Pages: {result['total_pages']}")
        print(f"  Characters: {result['total_chars']:,}")
        
    except Exception as e:
        print(f"Error: {e}")


def example_page_by_page():
    """Example 3: Process PDF page by page."""
    print("\n\nExample 3: Process PDF Page by Page")
    print("=" * 60)
    
    pdf_path = "../knowledge_base/CFR-2012-title26-vol1-sec1-41-4.pdf"
    
    try:
        result = extract_text_from_pdf(pdf_path)
        
        print(f"Processing {result['total_pages']} pages...\n")
        
        # Process each page individually
        for page in result['pages'][:3]:  # Show first 3 pages
            print(f"Page {page['page_number']}:")
            print(f"  Characters: {page['char_count']:,}")
            print(f"  Preview: {page['text'][:100]}...")
            print()
        
        if len(result['pages']) > 3:
            print(f"... and {len(result['pages']) - 3} more pages")
        
    except Exception as e:
        print(f"Error: {e}")


def example_batch_extraction():
    """Example 4: Extract from multiple PDFs."""
    print("\n\nExample 4: Batch PDF Extraction")
    print("=" * 60)
    
    # List of PDF files to process
    pdf_files = [
        "../knowledge_base/CFR-2012-title26-vol1-sec1-41-4.pdf",
        "../knowledge_base/Instructions for Form 6765.pdf",
        "../knowledge_base/IRS Publication 542 (Corporations).pdf"
    ]
    
    try:
        result = extract_text_from_multiple_pdfs(
            pdf_files,
            preserve_formatting=True,
            continue_on_error=True
        )
        
        print(f"Batch Extraction Results:")
        print(f"  Successful: {result['successful']}")
        print(f"  Failed: {result['failed']}")
        
        if result['errors']:
            print("\nErrors:")
            for error in result['errors']:
                print(f"  - {error['file']}: {error['error']}")
        
        print("\nExtracted Documents:")
        for doc in result['documents']:
            filename = Path(doc['file_path']).name
            print(f"  - {filename}: {doc['total_pages']} pages, "
                  f"{doc['total_chars']:,} characters")
        
    except Exception as e:
        print(f"Error: {e}")


def example_search_in_extracted_text():
    """Example 5: Search for specific content in extracted text."""
    print("\n\nExample 5: Search in Extracted Text")
    print("=" * 60)
    
    pdf_path = "../knowledge_base/CFR-2012-title26-vol1-sec1-41-4.pdf"
    
    try:
        result = extract_text_from_pdf(pdf_path)
        
        # Search for specific terms
        search_terms = ['qualified research', 'four-part test', 'technological']
        
        print(f"Searching in {Path(pdf_path).name}...\n")
        
        for term in search_terms:
            count = result['text'].lower().count(term.lower())
            print(f"'{term}': found {count} times")
            
            if count > 0:
                # Find first occurrence
                text_lower = result['text'].lower()
                pos = text_lower.find(term.lower())
                context_start = max(0, pos - 50)
                context_end = min(len(result['text']), pos + len(term) + 50)
                context = result['text'][context_start:context_end]
                print(f"  Context: ...{context}...")
            print()
        
    except Exception as e:
        print(f"Error: {e}")


def example_error_handling():
    """Example 6: Proper error handling."""
    print("\n\nExample 6: Error Handling")
    print("=" * 60)
    
    # Try to extract from non-existent file
    print("Attempting to extract from non-existent file...")
    try:
        result = extract_text_from_pdf("nonexistent.pdf")
    except FileNotFoundError as e:
        print(f"[OK] Caught FileNotFoundError: {e}")
    
    # Try to extract from corrupted file (simulated)
    print("\nAttempting to extract from invalid file...")
    try:
        # This would fail if we had a corrupted PDF
        result = extract_text_from_pdf("invalid.pdf")
    except FileNotFoundError:
        print("[OK] File doesn't exist (expected)")
    except PDFExtractionError as e:
        print(f"[OK] Caught PDFExtractionError: {e}")


def example_rag_preparation():
    """Example 7: Prepare text for RAG system."""
    print("\n\nExample 7: Prepare Text for RAG System")
    print("=" * 60)
    
    pdf_path = "../knowledge_base/CFR-2012-title26-vol1-sec1-41-4.pdf"
    
    try:
        result = extract_text_from_pdf(pdf_path, preserve_formatting=True)
        
        print(f"Preparing {Path(pdf_path).name} for RAG indexing...\n")
        
        # Prepare chunks for RAG system
        chunks = []
        for page in result['pages']:
            if page['text']:
                chunk = {
                    'text': page['text'],
                    'source': Path(pdf_path).name,
                    'page': page['page_number'],
                    'char_count': page['char_count']
                }
                chunks.append(chunk)
        
        print(f"Created {len(chunks)} chunks for RAG indexing")
        print(f"Average chunk size: {sum(c['char_count'] for c in chunks) // len(chunks):,} characters")
        
        # Show first chunk
        print(f"\nFirst chunk preview:")
        print(f"  Source: {chunks[0]['source']}")
        print(f"  Page: {chunks[0]['page']}")
        print(f"  Text: {chunks[0]['text'][:150]}...")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PDF EXTRACTOR USAGE EXAMPLES")
    print("=" * 60)
    
    # Run all examples
    example_basic_extraction()
    example_with_metadata()
    example_page_by_page()
    example_batch_extraction()
    example_search_in_extracted_text()
    example_error_handling()
    example_rag_preparation()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
