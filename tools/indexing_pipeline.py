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
            stats['errors'].append(error_msg)
            logger.error(error_msg)
            
            # Mark as not indexed
            doc_metadata['indexed'] = False
            doc_metadata['index_date'] = None
    
    # Save updated metadata
    try:
        metadata['last_updated'] = datetime.now().isoformat()
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info("Updated metadata.json with indexing status")
    except Exception as e:
        logger.error(f"Failed to update metadata.json: {e}")
    
    # Calculate duration
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    stats['duration_seconds'] = duration
    
    # Log final statistics
    logger.info("=" * 80)
    logger.info("Indexing Pipeline Complete")
    logger.info("=" * 80)
    logger.info(f"Total documents: {stats['total_documents']}")
    logger.info(f"Documents indexed: {stats['documents_indexed']}")
    logger.info(f"Documents skipped: {stats['documents_skipped']}")
    logger.info(f"Documents failed: {stats['documents_failed']}")
    logger.info(f"Total chunks created: {stats['total_chunks']}")
    logger.info(f"Total embeddings generated: {stats['total_embeddings']}")
    logger.info(f"Duration: {duration:.2f} seconds")
    
    if stats['errors']:
        logger.warning(f"Errors encountered: {len(stats['errors'])}")
        for error in stats['errors']:
            logger.warning(f"  - {error}")
    
    # Get final collection info
    collection_info = vector_db.get_collection_info()
    logger.info(f"Vector DB collection: {collection_info['name']}")
    logger.info(f"Total documents in collection: {collection_info['count']}")
    logger.info("=" * 80)
    
    return stats


def index_single_document(
    doc_metadata: Dict[str, Any],
    tax_docs_path: Path,
    vector_db: VectorDB,
    embedder: Embedder,
    chunk_size: int = 512,
    overlap: int = 50
) -> Dict[str, Any]:
    """
    Index a single document through the complete pipeline.
    
    Args:
        doc_metadata (Dict[str, Any]): Document metadata from metadata.json
        tax_docs_path (Path): Path to tax_docs directory
        vector_db (VectorDB): Initialized VectorDB instance
        embedder (Embedder): Initialized Embedder instance
        chunk_size (int): Target chunk size in tokens
        overlap (int): Overlap between chunks in tokens
    
    Returns:
        Dict[str, Any]: Indexing results for this document:
            - chunk_count: Number of chunks created
            - embedding_count: Number of embeddings generated
            - document_id: Document ID
    
    Raises:
        PDFExtractionError: If PDF extraction fails
        TextChunkingError: If text chunking fails
        RAGRetrievalError: If vector DB operations fail
    """
    doc_id = doc_metadata['id']
    filename = doc_metadata['filename']
    file_path = tax_docs_path / filename
    
    # Step 1: Extract text from PDF or read text file
    logger.info(f"Step 1/4: Extracting text from {filename}")
    
    # Check if it's a text file
    if filename.endswith('.txt'):
        # Read text file directly
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            # Create a document structure similar to PDF extraction
            extracted_doc = {
                'text': text_content,
                'pages': [{
                    'page_number': 1,
                    'text': text_content,
                    'char_count': len(text_content)
                }],
                'total_pages': 1,
                'total_chars': len(text_content),
                'file_path': str(file_path)
            }
            logger.info(f"Read text file: {len(text_content)} characters")
        except Exception as e:
            raise PDFExtractionError(f"Failed to read text file {filename}: {e}")
    else:
        # Extract from PDF
        extracted_doc = extract_text_from_pdf(
            pdf_path=str(file_path),
            preserve_formatting=True,
            include_metadata=True
        )
        logger.info(
            f"Extracted {extracted_doc['total_chars']} characters "
            f"from {extracted_doc['total_pages']} pages"
        )
    
    # Step 2: Chunk the text
    logger.info(f"Step 2/4: Chunking text (chunk_size={chunk_size}, overlap={overlap})")
    chunks = chunk_document(
        document=extracted_doc,
        chunk_size=chunk_size,
        overlap=overlap
    )
    logger.info(f"Created {len(chunks)} chunks")
    
    # Step 3: Generate embeddings
    logger.info(f"Step 3/4: Generating embeddings for {len(chunks)} chunks")
    chunk_texts = [chunk['text'] for chunk in chunks]
    embeddings = embedder.encode_batch(
        texts=chunk_texts,
        use_cache=True,
        batch_size=32,
        show_progress_bar=False
    )
    logger.info(f"Generated {len(embeddings)} embeddings")
    
    # Step 4: Store in vector database
    logger.info(f"Step 4/4: Storing {len(chunks)} chunks in vector database")
    
    # Prepare data for vector DB
    chunk_ids = []
    chunk_metadatas = []
    
    for i, chunk in enumerate(chunks):
        # Create unique ID for this chunk
        chunk_id = f"{doc_id}_chunk_{i}"
        chunk_ids.append(chunk_id)
        
        # Prepare metadata
        chunk_metadata = {
            'document_id': doc_id,
            'source': doc_metadata.get('title', filename),
            'filename': filename,
            'chunk_index': chunk.get('chunk_index', i),
            'page_number': chunk.get('page_number', 1),
            'token_count': chunk.get('token_count', 0),
            'char_count': chunk.get('char_count', 0)
        }
        
        # Add optional metadata fields
        if 'key_topics' in doc_metadata:
            chunk_metadata['key_topics'] = ', '.join(doc_metadata['key_topics'])
        
        chunk_metadatas.append(chunk_metadata)
    
    # Add to vector database
    vector_db.add_documents(
        texts=chunk_texts,
        metadatas=chunk_metadatas,
        ids=chunk_ids
    )
    
    logger.info(f"Successfully stored {len(chunks)} chunks in vector database")
    
    return {
        'chunk_count': len(chunks),
        'embedding_count': len(embeddings),
        'document_id': doc_id
    }


def get_indexing_status(knowledge_base_path: str = "./knowledge_base") -> Dict[str, Any]:
    """
    Get the current indexing status from metadata.json.
    
    Args:
        knowledge_base_path (str): Path to knowledge base directory
    
    Returns:
        Dict[str, Any]: Indexing status containing:
            - total_documents: Total number of documents
            - indexed_documents: Number of indexed documents
            - unindexed_documents: Number of unindexed documents
            - documents: List of document statuses
    
    Example:
        >>> from tools.indexing_pipeline import get_indexing_status
        >>> status = get_indexing_status()
        >>> print(f"Indexed: {status['indexed_documents']}/{status['total_documents']}")
    """
    metadata_path = Path(knowledge_base_path) / "metadata.json"
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        indexed_count = sum(1 for doc in metadata['documents'] if doc.get('indexed', False))
        
        return {
            'total_documents': len(metadata['documents']),
            'indexed_documents': indexed_count,
            'unindexed_documents': len(metadata['documents']) - indexed_count,
            'documents': [
                {
                    'id': doc['id'],
                    'filename': doc['filename'],
                    'indexed': doc.get('indexed', False),
                    'index_date': doc.get('index_date'),
                    'chunk_count': doc.get('chunk_count', 0)
                }
                for doc in metadata['documents']
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get indexing status: {e}")
        return {
            'error': str(e)
        }
