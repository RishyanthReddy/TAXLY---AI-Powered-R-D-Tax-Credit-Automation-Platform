#!/usr/bin/env python3
"""
Script to update knowledge base metadata with page counts from PDF files.
This script reads PDF files and extracts page count information to complete
the metadata.json file.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    print("Warning: pypdf not available. Install with: pip install pypdf")


def get_pdf_page_count(pdf_path: Path) -> int:
    """
    Extract page count from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Number of pages in the PDF
        
    Raises:
        Exception: If PDF cannot be read
    """
    if not PYPDF_AVAILABLE:
        raise ImportError("pypdf is required to read PDF files")
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            return len(pdf_reader.pages)
    except Exception as e:
        raise Exception(f"Failed to read PDF {pdf_path}: {str(e)}")


def update_metadata_with_page_counts(
    metadata_path: Path,
    tax_docs_dir: Path
) -> Dict[str, Any]:
    """
    Update metadata.json with page counts from PDF files.
    
    Args:
        metadata_path: Path to metadata.json
        tax_docs_dir: Path to directory containing PDF files
        
    Returns:
        Updated metadata dictionary
    """
    # Load existing metadata
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Update page counts for each document
    for doc in metadata['documents']:
        filename = doc['filename']
        pdf_path = tax_docs_dir / filename
        
        if pdf_path.exists():
            try:
                page_count = get_pdf_page_count(pdf_path)
                doc['page_count'] = page_count
                print(f"✓ {filename}: {page_count} pages")
            except Exception as e:
                print(f"✗ {filename}: Error - {str(e)}")
                doc['page_count'] = None
        else:
            print(f"✗ {filename}: File not found")
            doc['page_count'] = None
    
    # Update last_updated timestamp
    from datetime import datetime
    metadata['last_updated'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    return metadata


def main():
    """Main execution function."""
    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    metadata_path = project_root / 'knowledge_base' / 'metadata.json'
    tax_docs_dir = project_root / 'knowledge_base' / 'tax_docs'
    
    print("Updating knowledge base metadata...")
    print(f"Metadata file: {metadata_path}")
    print(f"Tax docs directory: {tax_docs_dir}")
    print()
    
    # Check if files exist
    if not metadata_path.exists():
        print(f"Error: metadata.json not found at {metadata_path}")
        return 1
    
    if not tax_docs_dir.exists():
        print(f"Error: tax_docs directory not found at {tax_docs_dir}")
        return 1
    
    # Update metadata
    try:
        updated_metadata = update_metadata_with_page_counts(
            metadata_path,
            tax_docs_dir
        )
        
        # Write updated metadata back to file
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(updated_metadata, f, indent=2, ensure_ascii=False)
        
        print()
        print("✓ Metadata updated successfully!")
        print(f"Updated file: {metadata_path}")
        
        return 0
        
    except Exception as e:
        print(f"Error updating metadata: {str(e)}")
        return 1


if __name__ == '__main__':
    exit(main())
