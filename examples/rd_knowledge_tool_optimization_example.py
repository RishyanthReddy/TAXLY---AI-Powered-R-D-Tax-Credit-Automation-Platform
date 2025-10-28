"""
RD Knowledge Tool Optimization Features Example

This example demonstrates the optimization features added to the RD_Knowledge_Tool:
1. Query caching for repeated questions
2. Batch query support for multiple projects
3. Cache management and statistics

Requirements: 2.2 (Task 51)
"""

import sys
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.rd_knowledge_tool import RD_Knowledge_Tool


def example_query_caching():
    """
    Example 1: Query Caching
    
    Demonstrates how query caching improves performance for repeated questions.
    """
    print("=" * 70)
    print("EXAMPLE 1: Query Caching")
    print("=" * 70)
    print()
    
    # Initialize tool with caching enabled (default)
    tool = RD_Knowledge_Tool(
        knowledge_base_path="./knowledge_base/indexed",
        enable_cache=True,
        cache_ttl=3600  # 1 hour TTL
    )
    
    question = "What is the four-part test for qualified research?"
    
    # First query - will hit the database
    print(f"Query 1: '{question}'")
    start_time = time.time()
    context1 = tool.query(question, top_k=3)
    elapsed1 = time.time() - start_time
    print(f"  Retrieved {context1.chunk_count} chunks in {elapsed1:.3f} seconds")
    print()
    
    # Second query - should hit the cache
    print(f"Query 2 (same question): '{question}'")
    start_time = time.time()
    context2 = tool.query(question, top_k=3)
    elapsed2 = time.time() - start_time
    print(f"  Retrieved {context2.chunk_count} chunks in {elapsed2:.3f} seconds")
    print(f"  Speedup: {elapsed1/elapsed2:.1f}x faster")
    print()
    
    # Get cache statistics
    cache_stats = tool.get_cache_stats()
    print("Cache Statistics:")
    print(f"  Enabled: {cache_stats['enabled']}")
    print(f"  Size: {cache_stats['size']} entries")
    print(f"  TTL: {cache_stats['ttl_seconds']} seconds")
    if cache_stats['newest_entry_age_seconds'] is not None:
        print(f"  Newest entry age: {cache_stats['newest_entry_age_seconds']:.1f} seconds")
    print()


def example_batch_query():
    """
    Example 2: Batch Query Support
    
    Demonstrates how to query multiple questions efficiently in batch.
    """
    print("=" * 70)
    print("EXAMPLE 2: Batch Query Support")
    print("=" * 70)
    print()
    
    # Initialize tool
    tool = RD_Knowledge_Tool(
        knowledge_base_path="./knowledge_base/indexed",
        enable_cache=True
    )
    
    # Define multiple questions (simulating multiple R&D projects)
    questions = [
        "What is the four-part test for qualified research?",
        "What are qualified research expenses?",
        "What is a process of experimentation?",
        "What are the wage limitations for R&D credit?",
        "Can software development qualify for R&D credit?"
    ]
    
    print(f"Processing {len(questions)} questions in batch...")
    print()
    
    # Execute batch query
    start_time = time.time()
    batch_result = tool.batch_query(
        questions=questions,
        top_k=3,
        enable_query_expansion=True,
        enable_query_rewriting=True,
        enable_reranking=True
    )
    elapsed = time.time() - start_time
    
    # Display results
    print("Batch Query Results:")
    print(f"  Total queries: {batch_result['total_queries']}")
    print(f"  Successful: {batch_result['successful_queries']}")
    print(f"  Failed: {batch_result['failed_queries']}")
    print(f"  Cache hits: {batch_result['cache_hits']}")
    print(f"  Cache hit rate: {batch_result['cache_hit_rate']:.1f}%")
    print(f"  Total time: {elapsed:.3f} seconds")
    print(f"  Average time per query: {elapsed/len(questions):.3f} seconds")
    print()
    
    # Display individual results
    print("Individual Query Results:")
    for i, (question, context) in enumerate(zip(questions, batch_result['results']), 1):
        if context is not None:
            print(f"  {i}. {question[:50]}...")
            print(f"     Chunks: {context.chunk_count}, Avg Relevance: {context.average_relevance:.2f}")
        else:
            print(f"  {i}. {question[:50]}...")
            print(f"     FAILED")
    print()


def example_batch_query_with_cache():
    """
    Example 3: Batch Query with Cache Benefits
    
    Demonstrates how caching improves performance when processing
    multiple batches with overlapping questions.
    """
    print("=" * 70)
    print("EXAMPLE 3: Batch Query with Cache Benefits")
    print("=" * 70)
    print()
    
    # Initialize tool
    tool = RD_Knowledge_Tool(
        knowledge_base_path="./knowledge_base/indexed",
        enable_cache=True
    )
    
    # First batch of questions
    batch1_questions = [
        "What is the four-part test?",
        "What are qualified research expenses?",
        "What is technological uncertainty?"
    ]
    
    # Second batch with some overlapping questions
    batch2_questions = [
        "What is the four-part test?",  # Duplicate from batch 1
        "What is a process of experimentation?",
        "What are qualified research expenses?",  # Duplicate from batch 1
        "Can software development qualify?"
    ]
    
    # Process first batch
    print("Processing Batch 1 (3 questions)...")
    start_time = time.time()
    result1 = tool.batch_query(batch1_questions, top_k=3)
    elapsed1 = time.time() - start_time
    print(f"  Time: {elapsed1:.3f} seconds")
    print(f"  Cache hits: {result1['cache_hits']}/{result1['total_queries']}")
    print()
    
    # Process second batch (should benefit from cache)
    print("Processing Batch 2 (4 questions, 2 duplicates from Batch 1)...")
    start_time = time.time()
    result2 = tool.batch_query(batch2_questions, top_k=3)
    elapsed2 = time.time() - start_time
    print(f"  Time: {elapsed2:.3f} seconds")
    print(f"  Cache hits: {result2['cache_hits']}/{result2['total_queries']}")
    print(f"  Cache hit rate: {result2['cache_hit_rate']:.1f}%")
    print()
    
    # Show cache statistics
    cache_stats = tool.get_cache_stats()
    print("Final Cache Statistics:")
    print(f"  Total entries: {cache_stats['size']}")
    print(f"  Average age: {cache_stats.get('average_age_seconds', 0):.1f} seconds")
    print()


def example_cache_management():
    """
    Example 4: Cache Management
    
    Demonstrates cache management operations.
    """
    print("=" * 70)
    print("EXAMPLE 4: Cache Management")
    print("=" * 70)
    print()
    
    # Initialize tool
    tool = RD_Knowledge_Tool(
        knowledge_base_path="./knowledge_base/indexed",
        enable_cache=True,
        cache_ttl=3600
    )
    
    # Execute some queries to populate cache
    questions = [
        "What is the four-part test?",
        "What are QRE?",
        "What is technological uncertainty?"
    ]
    
    print("Populating cache with 3 queries...")
    for question in questions:
        tool.query(question, top_k=3)
    print()
    
    # Check cache stats
    stats = tool.get_cache_stats()
    print(f"Cache size: {stats['size']} entries")
    print()
    
    # Clear cache
    print("Clearing cache...")
    cleared_count = tool.clear_cache()
    print(f"Cleared {cleared_count} entries")
    print()
    
    # Check cache stats again
    stats = tool.get_cache_stats()
    print(f"Cache size after clear: {stats['size']} entries")
    print()


def example_configurable_parameters():
    """
    Example 5: Configurable Parameters
    
    Demonstrates how to configure chunk retrieval parameters.
    """
    print("=" * 70)
    print("EXAMPLE 5: Configurable Parameters")
    print("=" * 70)
    print()
    
    # Initialize tool with custom default top_k
    tool = RD_Knowledge_Tool(
        knowledge_base_path="./knowledge_base/indexed",
        default_top_k=5,  # Retrieve 5 chunks by default
        enable_cache=True
    )
    
    question = "What are qualified research expenses?"
    
    # Query with default top_k (5)
    print(f"Query with default top_k (5):")
    context1 = tool.query(question)
    print(f"  Retrieved {context1.chunk_count} chunks")
    print()
    
    # Query with custom top_k (3)
    print(f"Query with custom top_k (3):")
    context2 = tool.query(question, top_k=3)
    print(f"  Retrieved {context2.chunk_count} chunks")
    print()
    
    # Query with optimizations disabled (for comparison)
    print(f"Query with optimizations disabled:")
    context3 = tool.query(
        question,
        top_k=3,
        enable_query_expansion=False,
        enable_query_rewriting=False,
        enable_reranking=False
    )
    print(f"  Retrieved {context3.chunk_count} chunks")
    print(f"  Retrieval method: {context3.retrieval_method}")
    print()


def main():
    """Run all examples"""
    print("\n")
    print("=" * 70)
    print("RD KNOWLEDGE TOOL OPTIMIZATION FEATURES")
    print("=" * 70)
    print("\n")
    
    try:
        # Example 1: Query Caching
        example_query_caching()
        
        # Example 2: Batch Query Support
        example_batch_query()
        
        # Example 3: Batch Query with Cache Benefits
        example_batch_query_with_cache()
        
        # Example 4: Cache Management
        example_cache_management()
        
        # Example 5: Configurable Parameters
        example_configurable_parameters()
        
        print("=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)
        print()
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
