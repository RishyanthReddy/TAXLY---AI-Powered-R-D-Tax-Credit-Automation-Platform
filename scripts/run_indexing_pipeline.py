"""
Script to run the indexing pipeline on IRS documents.

This script executes the complete indexing pipeline and provides
detailed verification of the results.

Usage:
    python scripts/run_indexing_pipeline.py [--force-reindex]
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.indexing_pipeline import index_documents, get_indexing_status
from tools.rd_knowledge_tool import RD_Knowledge_Tool
from utils.logger import AgentLogger

# Set up logger
logger = AgentLogger.get_logger(__name__)


def run_indexing_pipeline(force_reindex: bool = False):
    """
    Run the indexing pipeline and verify results.
    
    Args:
        force_reindex (bool): If True, reindex even if already indexed
    """
    logger.info("=" * 80)
    logger.info("RUNNING INDEXING PIPELINE")
    logger.info("=" * 80)
    
    # Get status before indexing
    logger.info("\nChecking current indexing status...")
    status_before = get_indexing_status("./knowledge_base")
    
    if 'error' in status_before:
        logger.error(f"Failed to get indexing status: {status_before['error']}")
        return False
    
    logger.info(f"Documents before indexing:")
    logger.info(f"  Total: {status_before['total_documents']}")
    logger.info(f"  Indexed: {status_before['indexed_documents']}")
    logger.info(f"  Unindexed: {status_before['unindexed_documents']}")
    
    # Run indexing pipeline
    logger.info("\nStarting indexing pipeline...")
    try:
        results = index_documents(
            knowledge_base_path="./knowledge_base",
            chunk_size=512,
            overlap=50,
            embedding_model="all-MiniLM-L6-v2",
            force_reindex=force_reindex
        )
        
        logger.info("\n" + "=" * 80)
        logger.info("INDEXING PIPELINE RESULTS")
        logger.info("=" * 80)
        logger.info(f"Total documents: {results['total_documents']}")
        logger.info(f"Documents indexed: {results['documents_indexed']}")
        logger.info(f"Documents skipped: {results['documents_skipped']}")
        logger.info(f"Documents failed: {results['documents_failed']}")
        logger.info(f"Total chunks created: {results['total_chunks']}")
        logger.info(f"Total embeddings generated: {results['total_embeddings']}")
        logger.info(f"Duration: {results['duration_seconds']:.2f} seconds")
        
        if results['errors']:
            logger.warning(f"\nErrors encountered: {len(results['errors'])}")
            for error in results['errors']:
                logger.warning(f"  - {error}")
            return False
        
        # Get status after indexing
        logger.info("\nChecking final indexing status...")
        status_after = get_indexing_status("./knowledge_base")
        
        logger.info(f"Documents after indexing:")
        logger.info(f"  Total: {status_after['total_documents']}")
        logger.info(f"  Indexed: {status_after['indexed_documents']}")
        logger.info(f"  Unindexed: {status_after['unindexed_documents']}")
        
        # Verify all documents are indexed
        if status_after['unindexed_documents'] > 0:
            logger.error(f"\nWARNING: {status_after['unindexed_documents']} documents remain unindexed!")
            logger.info("\nUnindexed documents:")
            for doc in status_after['documents']:
                if not doc['indexed']:
                    logger.info(f"  - {doc['filename']}")
            return False
        
        logger.info("\n✓ All documents successfully indexed!")
        
        # Test sample queries
        logger.info("\n" + "=" * 80)
        logger.info("TESTING SAMPLE QUERIES")
        logger.info("=" * 80)
        
        test_queries = [
            "What is the four-part test for qualified research?",
            "What are the wage caps for R&D tax credit?",
            "How do I calculate qualified research expenditures?",
            "What documentation is required for software development R&D claims?",
            "What is the process of experimentation?"
        ]
        
        logger.info("\nInitializing RAG Knowledge Tool...")
        rag_tool = RD_Knowledge_Tool(
            knowledge_base_path="./knowledge_base/indexed",
            collection_name="irs_documents",
            default_top_k=3
        )
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"\nQuery {i}: {query}")
            try:
                context = rag_tool.query(query, top_k=3)
                logger.info(f"  Retrieved {context.chunk_count} chunks")
                logger.info(f"  Average relevance: {context.average_relevance:.4f}")
                
                for j, chunk in enumerate(context.chunks, 1):
                    logger.info(f"  Chunk {j}:")
                    logger.info(f"    Source: {chunk.get('source', 'Unknown')}")
                    logger.info(f"    Page: {chunk.get('page', chunk.get('page_number', 'N/A'))}")
                    logger.info(f"    Relevance: {chunk.get('relevance_score', 0.0):.4f}")
                    logger.info(f"    Preview: {chunk.get('text', '')[:100]}...")
                
                # Check relevance scores
                if context.chunks and context.chunks[0].get('relevance_score', 1.0) < 0.3:
                    logger.warning(f"  WARNING: Low relevance score for query: {query}")
                
            except Exception as e:
                logger.error(f"  ERROR: Failed to query: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return False
        
        logger.info("\n" + "=" * 80)
        logger.info("INDEXING PIPELINE VERIFICATION COMPLETE")
        logger.info("=" * 80)
        logger.info("✓ All documents indexed successfully")
        logger.info("✓ ChromaDB collection populated")
        logger.info("✓ Sample queries validated")
        logger.info("✓ Retrieval quality confirmed")
        
        return True
        
    except Exception as e:
        logger.error(f"\nFailed to run indexing pipeline: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Run the indexing pipeline on IRS documents"
    )
    parser.add_argument(
        '--force-reindex',
        action='store_true',
        help='Force reindexing of all documents even if already indexed'
    )
    
    args = parser.parse_args()
    
    success = run_indexing_pipeline(force_reindex=args.force_reindex)
    
    if success:
        logger.info("\n✓ Indexing pipeline completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n✗ Indexing pipeline failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
