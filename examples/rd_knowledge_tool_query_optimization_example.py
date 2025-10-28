"""
Example demonstrating query optimization features in RD_Knowledge_Tool.

This example shows how to use the new query optimization features:
- Query expansion with technical term synonyms
- Query rewriting for better retrieval
- Re-ranking based on metadata and source preference
- Document source filtering
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.rd_knowledge_tool import RD_Knowledge_Tool


def main():
    """Demonstrate query optimization features"""
    
    # Initialize the tool (assumes knowledge base is already indexed)
    tool = RD_Knowledge_Tool(
        knowledge_base_path="./knowledge_base/indexed",
        default_top_k=3
    )
    
    print("=" * 80)
    print("RD Knowledge Tool - Query Optimization Examples")
    print("=" * 80)
    
    # Example 1: Query with all optimizations enabled (default)
    print("\n1. Query with ALL optimizations enabled (default):")
    print("-" * 80)
    query = "What is QRE?"
    print(f"Query: {query}")
    
    context = tool.query(
        query,
        top_k=3,
        enable_query_expansion=True,
        enable_query_rewriting=True,
        enable_reranking=True
    )
    
    print(f"Retrieval method: {context.retrieval_method}")
    print(f"Retrieved {context.chunk_count} chunks")
    print(f"Average relevance: {context.average_relevance:.2f}")
    print("\nTop result:")
    if context.chunks:
        print(f"  Source: {context.chunks[0]['source']}")
        print(f"  Relevance: {context.chunks[0]['relevance_score']}")
        print(f"  Text: {context.chunks[0]['text'][:150]}...")
    
    # Example 2: Query without optimizations for comparison
    print("\n\n2. Same query WITHOUT optimizations:")
    print("-" * 80)
    
    context_basic = tool.query(
        query,
        top_k=3,
        enable_query_expansion=False,
        enable_query_rewriting=False,
        enable_reranking=False
    )
    
    print(f"Retrieval method: {context_basic.retrieval_method}")
    print(f"Retrieved {context_basic.chunk_count} chunks")
    print(f"Average relevance: {context_basic.average_relevance:.2f}")
    print("\nTop result:")
    if context_basic.chunks:
        print(f"  Source: {context_basic.chunks[0]['source']}")
        print(f"  Relevance: {context_basic.chunks[0]['relevance_score']}")
        print(f"  Text: {context_basic.chunks[0]['text'][:150]}...")
    
    # Example 3: Query with source preference
    print("\n\n3. Query with source preference (Form 6765):")
    print("-" * 80)
    query = "wage limitations"
    print(f"Query: {query}")
    
    context = tool.query(
        query,
        top_k=3,
        enable_reranking=True,
        source_preference="Form 6765"
    )
    
    print(f"Retrieved {context.chunk_count} chunks")
    print("\nResults (note Form 6765 sources are boosted):")
    for i, chunk in enumerate(context.chunks, 1):
        print(f"\n  {i}. Source: {chunk['source']}")
        print(f"     Relevance: {chunk['relevance_score']}")
        if 'boost_factors' in chunk:
            print(f"     Boost factors: {', '.join(chunk['boost_factors'])}")
    
    # Example 4: Query with metadata filtering
    print("\n\n4. Query with metadata filtering (only CFR documents):")
    print("-" * 80)
    query = "four-part test"
    print(f"Query: {query}")
    
    context = tool.query(
        query,
        top_k=5,
        metadata_filter={"source": "CFR Title 26 § 1.41-4(a)(1)"}
    )
    
    print(f"Retrieved {context.chunk_count} chunks")
    print("\nAll results are from CFR:")
    for i, chunk in enumerate(context.chunks, 1):
        print(f"  {i}. {chunk['source']} - Relevance: {chunk['relevance_score']}")
    
    # Example 5: Testing individual optimization methods
    print("\n\n5. Testing individual optimization methods:")
    print("-" * 80)
    
    # Test query expansion
    expansions = tool._expand_query("What is QRE?")
    print(f"\nQuery expansion for 'What is QRE?':")
    print(f"  Generated {len(expansions)} variations:")
    for exp in expansions[:3]:  # Show first 3
        print(f"    - {exp}")
    
    # Test query rewriting
    original = "What is the four-part test?"
    rewritten = tool._rewrite_query(original)
    print(f"\nQuery rewriting:")
    print(f"  Original: {original}")
    print(f"  Rewritten: {rewritten}")
    
    # Test re-ranking
    sample_chunks = [
        {
            'text': 'Short text',
            'source': 'Publication 542',
            'page': 1,
            'relevance_score': 0.8
        },
        {
            'text': 'This is a longer text with more substantial content that provides detailed information.',
            'source': 'Form 6765 Instructions',
            'page': 2,
            'relevance_score': 0.75
        }
    ]
    
    reranked = tool._rerank_results(sample_chunks, "test", source_preference="Form 6765")
    print(f"\nRe-ranking with Form 6765 preference:")
    for chunk in reranked:
        print(f"  {chunk['source']}: {chunk['original_score']:.2f} -> {chunk['relevance_score']:.2f}")
        if 'boost_factors' in chunk:
            print(f"    Boost factors: {', '.join(chunk['boost_factors'])}")
    
    print("\n" + "=" * 80)
    print("Query optimization examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
