"""
Indexing Pipeline Usage Examples

This script demonstrates how to use the document indexing pipeline to index
IRS tax documents for the RAG system.

Run this script from the rd_tax_agent directory:
    python examples/indexing_pipeline_usage_example.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.indexing_pipeline import index_documents, get_indexing_status
from tools.vector_db import VectorDB
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_1_index_all_documents():
    """
    Example 1: Index all documents in the knowledge base.
    
    This will:
    - Extract text from all PDFs in knowledge_base/tax_docs/
    - Chunk the text with 512 token chunks and 50 token overlap
    - Generate embeddings using all-MiniLM-L6-v2
    - Store in ChromaDB
    - Update metadata.json
    """
    print("\n" + "=" * 80)
    print("Example 1: Index All Documents")
    print("=" * 80)
    
    results = index_documents(
        knowledge_base_path="./knowledge_base",
        chunk_size=512,
        overlap=50,
        embedding_model="all-MiniLM-L6-v2",
        force_reindex=False  # Skip already indexed documents
    )
    
    print("\nIndexing Results:")
    print(f"  Total documents: {results['total_documents']}")
    print(f"  Documents indexed: {results['documents_indexed']}")
    print(f"  Documents skipped: {results['documents_skipped']}")
    print(f"  Documents failed: {results['documents_failed']}")
    print(f"  Total chunks: {results['total_chunks']}")
    print(f"  Total embeddings: {results['total_embeddings']}")
    print(f"  Duration: {results['duration_seconds']:.2f} seconds")
    
    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")


def example_2_force_reindex():
    """
    Example 2: Force reindex all documents (even if already indexed).
    
    This is useful when:
    - You want to change chunk size or overlap
    - You want to use a different embedding model
    - You suspect the index is corrupted
    """
    print("\n" + "=" * 80)
    print("Example 2: Force Reindex All Documents")
    print("=" * 80)
    
    results = index_documents(
        knowledge_base_path="./knowledge_base",
        chunk_size=512,
        overlap=50,
        embedding_model="all-MiniLM-L6-v2",
        force_reindex=True  # Reindex even if already indexed
    )
    
    print("\nReindexing Results:")
    print(f"  Documents indexed: {results['documents_indexed']}")
    print(f"  Total chunks: {results['total_chunks']}")
    print(f"  Duration: {results['duration_seconds']:.2f} seconds")


def example_3_check_indexing_status():
    """
    Example 3: Check the current indexing status.
    
    This shows which documents are indexed and which are not.
    """
    print("\n" + "=" * 80)
    print("Example 3: Check Indexing Status")
    print("=" * 80)
    
    status = get_indexing_status(knowledge_base_path="./knowledge_base")
    
    print("\nIndexing Status:")
    print(f"  Total documents: {status['total_documents']}")
    print(f"  Indexed: {status['indexed_documents']}")
    print(f"  Unindexed: {status['unindexed_documents']}")
    
    print("\nDocument Details:")
    for doc in status['documents']:
        status_str = "✓ Indexed" if doc['indexed'] else "✗ Not indexed"
        chunk_info = f"({doc['chunk_count']} chunks)" if doc['chunk_count'] > 0 else ""
        print(f"  {status_str}: {doc['filename']} {chunk_info}")
        if doc['index_date']:
            print(f"    Indexed on: {doc['index_date']}")


def example_4_query_indexed_documents():
    """
    Example 4: Query the indexed documents to verify indexing worked.
    
    This demonstrates that the indexed documents can be retrieved.
    """
    print("\n" + "=" * 80)
    print("Example 4: Query Indexed Documents")
    print("=" * 80)
    
    # Initialize vector database
    vector_db = VectorDB(
        persist_directory="./knowledge_base/indexed",
        collection_name="irs_documents"
    )
    
    # Get collection info
    info = vector_db.get_collection_info()
    print(f"\nCollection: {info['name']}")
    print(f"Total documents: {info['count']}")
    print(f"Embedding model: {info['embedding_model']}")
    
    # Test query
    query = "What is the four-part test for qualified research?"
    print(f"\nTest Query: '{query}'")
    
    results = vector_db.query(query, top_k=3)
    
    print(f"\nTop {len(results['documents'][0])} Results:")
    for i, (doc, metadata, distance) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    ), 1):
        print(f"\n  Result {i}:")
        print(f"    Source: {metadata['source']}")
        print(f"    Page: {metadata['page_number']}")
        print(f"    Distance: {distance:.4f}")
        print(f"    Text preview: {doc[:150]}...")


def example_5_custom_chunk_size():
    """
    Example 5: Index with custom chunk size and overlap.
    
    This shows how to adjust chunking parameters for different use cases.
    """
    print("\n" + "=" * 80)
    print("Example 5: Index with Custom Chunk Size")
    print("=" * 80)
    
    # Use larger chunks for more context
    results = index_documents(
        knowledge_base_path="./knowledge_base",
        chunk_size=1024,  # Larger chunks
        overlap=100,      # More overlap
        embedding_model="all-MiniLM-L6-v2",
        force_reindex=True
    )
    
    print("\nIndexing with Custom Parameters:")
    print(f"  Chunk size: 1024 tokens")
    print(f"  Overlap: 100 tokens")
    print(f"  Total chunks: {results['total_chunks']}")
    print(f"  Duration: {results['duration_seconds']:.2f} seconds")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("INDEXING PIPELINE USAGE EXAMPLES")
    print("=" * 80)
    
    try:
        # Example 1: Index all documents
        example_1_index_all_documents()
        
        # Example 2: Check status
        example_3_check_indexing_status()
        
        # Example 3: Query indexed documents
        example_4_query_indexed_documents()
        
        # Uncomment to run other examples:
        # example_2_force_reindex()
        # example_5_custom_chunk_size()
        
        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
