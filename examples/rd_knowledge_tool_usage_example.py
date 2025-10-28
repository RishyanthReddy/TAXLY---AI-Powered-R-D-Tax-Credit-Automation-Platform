"""
Usage example for RD_Knowledge_Tool.

This example demonstrates how to use the RD_Knowledge_Tool to query
the IRS document knowledge base for R&D tax credit qualification guidance.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.rd_knowledge_tool import RD_Knowledge_Tool


def main():
    """Demonstrate RD_Knowledge_Tool usage."""
    
    print("=" * 80)
    print("RD_Knowledge_Tool Usage Example")
    print("=" * 80)
    print()
    
    # Initialize the tool
    print("1. Initializing RD_Knowledge_Tool...")
    tool = RD_Knowledge_Tool(
        knowledge_base_path="./knowledge_base/indexed",
        default_top_k=3
    )
    print(f"   ✓ Tool initialized successfully")
    print()
    
    # Get knowledge base info
    print("2. Getting knowledge base information...")
    info = tool.get_knowledge_base_info()
    print(f"   Path: {info['path']}")
    print(f"   Total chunks: {info['total_chunks']}")
    print(f"   Collection: {info['collection_name']}")
    print(f"   Embedding model: {info['embedding_model']}")
    print()
    
    # Example 1: Query about the four-part test
    print("3. Querying: 'What is the four-part test for qualified research?'")
    context1 = tool.query(
        "What is the four-part test for qualified research?",
        top_k=3
    )
    print(f"   ✓ Retrieved {context1.chunk_count} chunks")
    print(f"   ✓ Average relevance: {context1.average_relevance:.2f}")
    print()
    print("   Top result:")
    if context1.chunks:
        top_chunk = context1.chunks[0]
        print(f"   Source: {top_chunk['source']}, Page {top_chunk['page']}")
        print(f"   Relevance: {top_chunk['relevance_score']:.2f}")
        print(f"   Text: {top_chunk['text'][:200]}...")
    print()
    
    # Example 2: Query about qualified research expenses
    print("4. Querying: 'What are qualified research expenses?'")
    context2 = tool.query(
        "What are qualified research expenses?",
        top_k=2
    )
    print(f"   ✓ Retrieved {context2.chunk_count} chunks")
    print(f"   ✓ Average relevance: {context2.average_relevance:.2f}")
    print()
    
    # Example 3: Format context for LLM prompt
    print("5. Formatting context for LLM prompt...")
    formatted = context2.format_for_llm_prompt(max_chunks=2)
    print("   Formatted output (first 500 chars):")
    print("   " + "-" * 76)
    print("   " + formatted[:500].replace("\n", "\n   "))
    print("   ...")
    print("   " + "-" * 76)
    print()
    
    # Example 4: Extract citations
    print("6. Extracting citations...")
    citations = context2.extract_citations()
    print(f"   ✓ Found {len(citations)} unique citations:")
    for i, citation in enumerate(citations, 1):
        print(f"      {i}. {citation}")
    print()
    
    # Example 5: Query with metadata filter
    print("7. Querying with metadata filter (Form 6765 only)...")
    context3 = tool.query(
        "qualified research wages",
        top_k=5,
        metadata_filter={"source": "Form 6765 Instructions"}
    )
    print(f"   ✓ Retrieved {context3.chunk_count} chunks from Form 6765")
    print()
    
    # Example 6: Multiple queries
    print("8. Running multiple queries...")
    queries = [
        "process of experimentation",
        "software development R&D",
        "business component"
    ]
    
    for query in queries:
        context = tool.query(query, top_k=1)
        print(f"   Query: '{query}'")
        print(f"   → {context.chunk_count} chunk(s), avg relevance: {context.average_relevance:.2f}")
    print()
    
    print("=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
