"""
Document Indexing Pipeline

This module orchestrates the full document indexing pipeline for IRS tax documents.
It extracts text from PDFs, chunks the text with overlap, generates embeddings,
and stores them in ChromaDB for RAG (Retrieval-Augmented Generation) retrieval.

Functions:
    index_documents: Main function to orchestrate the full indexing pipeline
    index_single_document: Index a single document
    update_metadata: Update metadata.json with indexing status

Requirements: 2.1
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from tools.pdf_extractor import extract_text_from_pdf, PDFExtractionError
from tools.text_chunker import chunk_document, TextChunkingError
from tools.embedder import Embedder
from tools.vector_db import VectorDB
from utils.exceptions import RAGRetrievalError

# Configure logger
logger = logging.getLogger(__name__)


class IndexingPipelineError(Exception):
    """Custom exception for indexing pipeline errors"""
    pass


def index_documents(
    knowledge_base_path: str = "./knowledge_base",
    chunk_size: int = 512,
    overlap: int = 50,
    embedding_model: str = "all-MiniLM-L6-v2",
    force_reindex: bool = False
) -> Dict[str, Any]:
    """
    Index all PDF documents in the knowledge base directory.
    
    This function orchestrates the complete indexing pipeline:
    1. Reads metadata.json to find documents to index
    2. Extracts text from PDFs in knowledge_base/tax_docs/
    3. Chunks extracted text with overlap
    4. Generates embeddings for all chunks
    5. Stores embeddings and metadata in ChromaDB
    6. Updates metadata.json with indexing status
    7. Logs progress and statistics
    
    Args:
        knowledge_base_path (str): Path to knowledge base directory.
                                   Default is "./knowledge_base"
        chunk_size (int): Target size of each chunk in tokens. Default is 512.
        overlap (int): Number of tokens to overlap between chunks. Default is 50.
        embedding_model (str): SentenceTransformer model name.
                              Default is "all-MiniLM-L6-v2"
        force_reindex (bool): If True, reindex even if already indexed.
                             Default is False.
    
    Returns:
        Dict[str, Any]: Indexing results containing:
            - total_documents: Total number of documents found
            - documents_indexed: Number of documents successfully indexed
            - documents_skipped: Number of documents skipped (already indexed)
            - documents_failed: Number of documents that failed
            - total_chunks: Total number of chunks created
            - total_embeddings: Total number of embeddings generated
            - errors: List of error messages for failed documents
            - duration_seconds: Total time taken for indexing
    
    Raises:
        IndexingPipelineError: If pipeline initialization fails
        FileNotFoundError: If knowledge base path doesn't exist
    
    Example:
        >>> from tools.indexing_pipeline import index_documents
        >>> results = index_documents()
        >>> print(f"Indexed {results['documents_indexed']} documents")
        >>> print(f"Created {results['total_chunks']} chunks")
    """
    start_time = datetime.now()
    
    # Validate knowledge base path
    kb_path = Path(knowledge_base_path)
    if not kb_path.exists():
        raise FileNotFoundError(f"Knowledge base path not found: {knowledge_base_path}")
    
    tax_docs_path = kb_path / "tax_docs"
    indexed_path = kb_path / "indexed"
    metadata_path = kb_path / "metadata.json"
    
    if not tax_docs_path.exists():
        raise FileNotFoundError(f"Tax documents directory not found: {tax_docs_path}")
    
    logger.info("=" * 80)
    logger.info("Starting Document Indexing Pipeline")
    logger.info("=" * 80)
    logger.info(f"Knowledge base path: {knowledge_base_path}")
    logger.info(f"Chunk size: {chunk_size} tokens")
    logger.info(f"Overlap: {overlap} tokens")
    logger.info(f"Embedding model: {embedding_model}")
    logger.info(f"Force reindex: {force_reindex}")
    
    # Load metadata
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        logger.info(f"Loaded metadata for {len(metadata['documents'])} documents")
    except Exception as e:
        raise IndexingPipelineError(f"Failed to load metadata.json: {e}")
    
    # Initialize components
    try:
        logger.info("Initializing indexing components...")
        embedder = Embedder(model_name=embedding_model)
        vector_db = VectorDB(
            persist_directory=str(indexed_path),
            collection_name="irs_documents",
            embedding_model=embedding_model
        )
        logger.info("Components initialized successfully")
    except Exception as e:
        raise IndexingPipelineError(f"Failed to initialize components: {e}")
    
    # Track statistics
    stats = {
        'total_documents': len(metadata['documents']),
        'documents_indexed': 0,
        'documents_skipped': 0,
        'documents_failed': 0,
        'total_chunks': 0,
        'total_embeddings': 0,
        'errors': []
    }
    
    # Process each document
    for doc_metadata in metadata['documents']:
        doc_id = doc_metadata['id']
        filename = doc_metadata['filename']
        
        # Check if already indexed
        if doc_metadata.get('indexed', False) and not force_reindex:
            logger.info(f"Skipping {filename} (already indexed)")
            stats['documents_skipped'] += 1
            continue
        
        logger.info("-" * 80)
        logger.info(f"Processing document: {filename}")
        
        try:
            # Index the document
            result = index_single_document(
                doc_metadata=doc_metadata,
                tax_docs_path=tax_docs_path,
                vector_db=vector_db,
                embedder=embedder,
                chunk_size=chunk_size,
                overlap=overlap
            )
            
            # Update statistics
            stats['documents_indexed'] += 1
            stats['total_chunks'] += result['chunk_count']
            stats['total_embeddings'] += result['embedding_count']
            
            # Update metadata
            doc_metadata['indexed'] = True
            doc_metadata['index_date'] = datetime.now().isoformat()
            doc_metadata['chunk_count'] = result['chunk_count']
            
            logger.info(
                f"Successfully indexed {filename}: "
                f"{result['chunk_count']} chunks, "
                f"{result['embedding_count']} embeddings"
            )
            
        except Exception as e:
            stats['documents_failed'] += 1
            error_msg = f"Failed to index {filename}: {str(e)}"
            stats['err