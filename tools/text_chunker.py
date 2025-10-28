"""
Text Chunking Tool

This module provides functionality to chunk text into token-sized segments with overlap
for use in RAG (Retrieval-Augmented Generation) systems. It uses tiktoken for accurate
token counting and preserves sentence boundaries to maintain context.

Requirements: 2.1
"""

import logging
import re
from typing import Dict, List, Optional
import tiktoken

# Configure logger
logger = logging.getLogger(__name__)


class TextChunkingError(Exception):
    """Custom exception for text chunking errors"""
    pass


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50,
    source_document: Optional[str] = None,
    page_number: Optional[int] = None,
    encoding_name: str = "cl100k_base"
) -> List[Dict[str, any]]:
    """
    Chunk text into token-sized segments with overlap, preserving sentence boundaries.
    
    This function splits text into chunks of approximately chunk_size tokens, with
    overlap tokens between consecutive chunks to preserve context. It attempts to
    split at sentence boundaries to avoid breaking sentences mid-way.
    
    Args:
        text: The text to chunk
        chunk_size: Target size of each chunk in tokens (default: 512)
        overlap: Number of tokens to overlap between chunks (default: 50)
        source_document: Name of the source document (for metadata)
        page_number: Page number in the source document (for metadata)
        encoding_name: Tiktoken encoding to use (default: "cl100k_base" for GPT-4)
    
    Returns:
        List of dictionaries, each containing:
            - 'text': The chunk text
            - 'token_count': Number of tokens in the chunk
            - 'char_count': Number of characters in the chunk
            - 'chunk_index': Index of this chunk (0-based)
            - 'source_document': Source document name (if provided)
            - 'page_number': Page number (if provided)
            - 'start_char': Starting character position in original text
            - 'end_char': Ending character position in original text
    
    Raises:
        TextChunkingError: If chunking fails
        ValueError: If chunk_size or overlap are invalid
    
    Example:
        >>> text = "This is a long document. It has many sentences. We need to chunk it."
        >>> chunks = chunk_text(text, chunk_size=20, overlap=5, source_document="doc.pdf")
        >>> print(f"Created {len(chunks)} chunks")
        >>> print(f"First chunk: {chunks[0]['text']}")
    """
    # Validate parameters
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    
    if overlap < 0:
        raise ValueError("overlap cannot be negative")
    
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size")
    
    if not text or not text.strip():
        logger.warning("Empty text provided for chunking")
        return []
    
    logger.info(
        f"Starting text chunking: {len(text)} chars, "
        f"chunk_size={chunk_size}, overlap={overlap}"
    )
    
    try:
        # Initialize tiktoken encoder
        encoding = tiktoken.get_encoding(encoding_name)
        
        # Split text into sentences
        sentences = _split_into_sentences(text)
        
        if not sentences:
            logger.warning("No sentences found in text")
            return []
        
        logger.debug(f"Split text into {len(sentences)} sentences")
        
        # Build chunks
        chunks = []
        current_chunk_sentences = []
        current_chunk_tokens = 0
        chunk_index = 0
        char_position = 0
        
        for sentence in sentences:
            # Count tokens in this sentence
            sentence_tokens = len(encoding.encode(sentence))
            
            # Check if adding this sentence would exceed chunk_size
            if current_chunk_tokens + sentence_tokens > chunk_size and current_chunk_sentences:
                # Create chunk from accumulated sentences
                chunk_text = ' '.join(current_chunk_sentences)
                chunk_start = char_position - len(chunk_text)
                
                chunk_data = _create_chunk_metadata(
                    text=chunk_text,
                    encoding=encoding,
                    chunk_index=chunk_index,
                    source_document=source_document,
                    page_number=page_number,
                    start_char=chunk_start,
                    end_char=char_position
                )
                
                chunks.append(chunk_data)
                chunk_index += 1
                
                # Start new chunk with overlap
                # Keep sentences that fit within overlap token count
                overlap_sentences = []
                overlap_tokens = 0
                
                for sent in reversed(current_chunk_sentences):
                    sent_tokens = len(encoding.encode(sent))
                    if overlap_tokens + sent_tokens <= overlap:
                        overlap_sentences.insert(0, sent)
                        overlap_tokens += sent_tokens
                    else:
                        break
                
                current_chunk_sentences = overlap_sentences
                current_chunk_tokens = overlap_tokens
                
                logger.debug(
                    f"Created chunk {chunk_index - 1}: "
                    f"{chunk_data['token_count']} tokens, "
                    f"{chunk_data['char_count']} chars"
                )
            
            # Add sentence to current chunk
            current_chunk_sentences.append(sentence)
            current_chunk_tokens += sentence_tokens
            char_position += len(sentence) + 1  # +1 for space
        
        # Add final chunk if there are remaining sentences
        if current_chunk_sentences:
            chunk_text = ' '.join(current_chunk_sentences)
            chunk_start = char_position - len(chunk_text)
            
            chunk_data = _create_chunk_metadata(
                text=chunk_text,
                encoding=encoding,
                chunk_index=chunk_index,
                source_document=source_document,
                page_number=page_number,
                start_char=chunk_start,
                end_char=char_position
            )
            
            chunks.append(chunk_data)
            
            logger.debug(
                f"Created final chunk {chunk_index}: "
                f"{chunk_data['token_count']} tokens, "
                f"{chunk_data['char_count']} chars"
            )
        
        logger.info(f"Successfully created {len(chunks)} chunks from text")
        
        return chunks
    
    except Exception as e:
        error_msg = f"Error chunking text: {e}"
        logger.error(error_msg)
        raise TextChunkingError(error_msg) from e


def _split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences, attempting to preserve sentence boundaries.
    
    This function uses regex patterns to identify sentence boundaries based on
    common punctuation marks (., !, ?) followed by whitespace and capital letters.
    
    Args:
        text: Text to split into sentences
    
    Returns:
        List of sentences
    """
    if not text:
        return []
    
    # Clean up the text
    text = text.strip()
    
    # Pattern to split on sentence boundaries
    # Matches: period/exclamation/question followed by space and capital letter
    # Also handles common abbreviations (Dr., Mr., Mrs., etc.)
    sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+(?=[A-Z])'
    
    # Split text into sentences
    sentences = re.split(sentence_pattern, text)
    
    # Clean up sentences
    cleaned_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:
            cleaned_sentences.append(sentence)
    
    # If no sentences were found (no proper punctuation), split by newlines
    if not cleaned_sentences:
        lines = text.split('\n')
        cleaned_sentences = [line.strip() for line in lines if line.strip()]
    
    # If still no sentences, return the whole text as one sentence
    if not cleaned_sentences:
        cleaned_sentences = [text]
    
    return cleaned_sentences


def _create_chunk_metadata(
    text: str,
    encoding: tiktoken.Encoding,
    chunk_index: int,
    source_document: Optional[str],
    page_number: Optional[int],
    start_char: int,
    end_char: int
) -> Dict[str, any]:
    """
    Create metadata dictionary for a text chunk.
    
    Args:
        text: The chunk text
        encoding: Tiktoken encoding instance
        chunk_index: Index of this chunk
        source_document: Source document name
        page_number: Page number
        start_char: Starting character position
        end_char: Ending character position
    
    Returns:
        Dictionary with chunk text and metadata
    """
    token_count = len(encoding.encode(text))
    
    metadata = {
        'text': text,
        'token_count': token_count,
        'char_count': len(text),
        'chunk_index': chunk_index,
        'start_char': start_char,
        'end_char': end_char
    }
    
    if source_document is not None:
        metadata['source_document'] = source_document
    
    if page_number is not None:
        metadata['page_number'] = page_number
    
    return metadata


def chunk_document(
    document: Dict[str, any],
    chunk_size: int = 512,
    overlap: int = 50,
    encoding_name: str = "cl100k_base"
) -> List[Dict[str, any]]:
    """
    Chunk a document extracted by pdf_extractor.py.
    
    This function takes the output from extract_text_from_pdf() and chunks it
    page by page, preserving page metadata in each chunk.
    
    Args:
        document: Document dictionary from extract_text_from_pdf()
        chunk_size: Target size of each chunk in tokens (default: 512)
        overlap: Number of tokens to overlap between chunks (default: 50)
        encoding_name: Tiktoken encoding to use (default: "cl100k_base")
    
    Returns:
        List of chunk dictionaries with metadata
    
    Raises:
        TextChunkingError: If chunking fails
        ValueError: If document format is invalid
    
    Example:
        >>> from tools.pdf_extractor import extract_text_from_pdf
        >>> document = extract_text_from_pdf('knowledge_base/tax_docs/form_6765.pdf')
        >>> chunks = chunk_document(document, chunk_size=512, overlap=50)
        >>> print(f"Created {len(chunks)} chunks from {document['total_pages']} pages")
    """
    # Validate document structure
    if not isinstance(document, dict):
        raise ValueError("document must be a dictionary")
    
    if 'pages' not in document:
        raise ValueError("document must contain 'pages' key")
    
    if 'file_path' not in document:
        raise ValueError("document must contain 'file_path' key")
    
    source_document = document['file_path']
    pages = document['pages']
    
    logger.info(
        f"Chunking document: {source_document}, "
        f"{len(pages)} pages"
    )
    
    all_chunks = []
    
    # Process each page
    for page_data in pages:
        page_number = page_data.get('page_number')
        page_text = page_data.get('text', '')
        
        if not page_text or not page_text.strip():
            logger.debug(f"Skipping empty page {page_number}")
            continue
        
        # Chunk this page's text
        page_chunks = chunk_text(
            text=page_text,
            chunk_size=chunk_size,
            overlap=overlap,
            source_document=source_document,
            page_number=page_number,
            encoding_name=encoding_name
        )
        
        all_chunks.extend(page_chunks)
        
        logger.debug(
            f"Page {page_number}: created {len(page_chunks)} chunks"
        )
    
    logger.info(
        f"Successfully chunked document: {len(all_chunks)} total chunks"
    )
    
    return all_chunks


def chunk_multiple_documents(
    documents: List[Dict[str, any]],
    chunk_size: int = 512,
    overlap: int = 50,
    encoding_name: str = "cl100k_base",
    continue_on_error: bool = True
) -> Dict[str, any]:
    """
    Chunk multiple documents extracted by pdf_extractor.py.
    
    Args:
        documents: List of document dictionaries from extract_text_from_pdf()
        chunk_size: Target size of each chunk in tokens (default: 512)
        overlap: Number of tokens to overlap between chunks (default: 50)
        encoding_name: Tiktoken encoding to use (default: "cl100k_base")
        continue_on_error: If True, continues processing even if some documents fail
    
    Returns:
        Dictionary containing:
            - 'chunks': List of all chunks from all documents
            - 'total_chunks': Total number of chunks created
            - 'documents_processed': Number of successfully processed documents
            - 'documents_failed': Number of failed documents
            - 'errors': List of error messages for failed documents
    
    Example:
        >>> from tools.pdf_extractor import extract_text_from_multiple_pdfs
        >>> pdf_files = ['doc1.pdf', 'doc2.pdf']
        >>> extraction_result = extract_text_from_multiple_pdfs(pdf_files)
        >>> chunking_result = chunk_multiple_documents(extraction_result['documents'])
        >>> print(f"Created {chunking_result['total_chunks']} chunks")
    """
    all_chunks = []
    errors = []
    documents_processed = 0
    documents_failed = 0
    
    for document in documents:
        try:
            chunks = chunk_document(
                document=document,
                chunk_size=chunk_size,
                overlap=overlap,
                encoding_name=encoding_name
            )
            
            all_chunks.extend(chunks)
            documents_processed += 1
        
        except Exception as e:
            documents_failed += 1
            source = document.get('file_path', 'unknown')
            error_info = {
                'document': source,
                'error': str(e)
            }
            errors.append(error_info)
            logger.error(f"Failed to chunk document {source}: {e}")
            
            if not continue_on_error:
                raise
    
    return {
        'chunks': all_chunks,
        'total_chunks': len(all_chunks),
        'documents_processed': documents_processed,
        'documents_failed': documents_failed,
        'errors': errors
    }
