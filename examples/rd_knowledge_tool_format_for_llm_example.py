"""
Example usage of RD_Knowledge_Tool.format_for_llm() method.

This example demonstrates how to format RAG context for LLM consumption
with various options including relevance scores, metadata, custom templates,
and chunk limiting.
"""

from tools.rd_knowledge_tool import RD_Knowledge_Tool
from models.tax_models import RAGContext
from datetime import datetime


def example_basic_formatting():
    """Example 1: Basic formatting with all default options"""
    print("=" * 80)
    print("Example 1: Basic Formatting")
    print("=" * 80)
    
    # Initialize the tool
    tool = RD_Knowledge_Tool(
        knowledge_base_path="./knowledge_base/indexed",
        default_top_k=3
    )
    
    # Query the knowledge base
    context = tool.query("What is the four-part test for qualified research?", top_k=3)
    
    # Format for LLM with default options
    formatted = tool.format_for_llm(context)
    
    print(formatted)
    print("\n")


def example_without_relevance_scores():
    """Example 2: Formatting without relevance scores"""
    print("=" * 80)
    print("Example 2: Formatting Without Relevance Scores")
    print("=" * 80)
    
    tool = RD_Knowledge_Tool(knowledge_base_path="./knowledge_base/indexed")
    context = tool.query("What are qualified research expenses?", top_k=2)
    
    # Format without relevance scores
    formatted = tool.format_for_llm(
        context,
        include_relevance_scores=False
    )
    
    print(formatted)
    print("\n")


def example_without_metadata():
    """Example 3: Formatting without retrieval metadata"""
    print("=" * 80)
    print("Example 3: Formatting Without Metadata")
    print("=" * 80)
    
    tool = RD_Knowledge_Tool(knowledge_base_path="./knowledge_base/indexed")
    context = tool.query("process of experimentation", top_k=2)
    
    # Format without metadata
    formatted = tool.format_for_llm(
        context,
        include_metadata=False
    )
    
    print(formatted)
    print("\n")


def example_with_max_chunks():
    """Example 4: Limiting the number of chunks in output"""
    print("=" * 80)
    print("Example 4: Limiting Chunks")
    print("=" * 80)
    
    tool = RD_Knowledge_Tool(knowledge_base_path="./knowledge_base/indexed")
    context = tool.query("R&D tax credit requirements", top_k=5)
    
    # Format with max 2 chunks
    formatted = tool.format_for_llm(
        context,
        max_chunks=2
    )
    
    print(f"Original context had {context.chunk_count} chunks")
    print(f"Formatted output limited to 2 chunks\n")
    print(formatted)
    print("\n")


def example_custom_template():
    """Example 5: Using a custom prompt template"""
    print("=" * 80)
    print("Example 5: Custom Prompt Template")
    print("=" * 80)
    
    tool = RD_Knowledge_Tool(knowledge_base_path="./knowledge_base/indexed")
    context = tool.query("software development R&D qualification", top_k=3)
    
    # Define custom template
    custom_template = """
You are an R&D tax credit expert. Based on the following IRS guidance:

{context}

Please analyze whether the following project qualifies for R&D tax credit:

Project: Software Development - Authentication System
Description: Developing a new multi-factor authentication system with 
biometric integration and advanced encryption algorithms.

Query: {query}
Number of relevant IRS excerpts: {chunk_count}

Provide your analysis with:
1. Qualification percentage (0-100%)
2. Confidence score (0-1)
3. Reasoning based on the four-part test
4. Supporting citations

Sources consulted:
{citations}
"""
    
    # Format with custom template
    formatted = tool.format_for_llm(
        context,
        prompt_template=custom_template
    )
    
    print(formatted)
    print("\n")


def example_minimal_formatting():
    """Example 6: Minimal formatting (no scores, no metadata)"""
    print("=" * 80)
    print("Example 6: Minimal Formatting")
    print("=" * 80)
    
    tool = RD_Knowledge_Tool(knowledge_base_path="./knowledge_base/indexed")
    context = tool.query("wage limitations", top_k=2)
    
    # Minimal formatting
    formatted = tool.format_for_llm(
        context,
        include_relevance_scores=False,
        include_metadata=False
    )
    
    print(formatted)
    print("\n")


def example_comprehensive_formatting():
    """Example 7: Comprehensive formatting with all options"""
    print("=" * 80)
    print("Example 7: Comprehensive Formatting")
    print("=" * 80)
    
    tool = RD_Knowledge_Tool(knowledge_base_path="./knowledge_base/indexed")
    
    # Query with all optimizations
    context = tool.query(
        "What is QRE?",
        top_k=5,
        enable_query_expansion=True,
        enable_query_rewriting=True,
        enable_reranking=True,
        source_preference="Form 6765"
    )
    
    # Format with all options
    formatted = tool.format_for_llm(
        context,
        include_relevance_scores=True,
        include_metadata=True,
        max_chunks=3
    )
    
    print(formatted)
    print("\n")


def example_empty_context():
    """Example 8: Handling empty context"""
    print("=" * 80)
    print("Example 8: Empty Context Handling")
    print("=" * 80)
    
    tool = RD_Knowledge_Tool(knowledge_base_path="./knowledge_base/indexed")
    
    # Create an empty context (simulating no results)
    empty_context = RAGContext(
        query="nonexistent topic xyz123",
        chunks=[],
        retrieval_timestamp=datetime.now(),
        total_chunks_available=150,
        retrieval_method="semantic_search"
    )
    
    # Format empty context
    formatted = tool.format_for_llm(empty_context)
    
    print(formatted)
    print("\n")


def example_for_agent_prompt():
    """Example 9: Real-world usage in agent prompt"""
    print("=" * 80)
    print("Example 9: Real-World Agent Prompt")
    print("=" * 80)
    
    tool = RD_Knowledge_Tool(knowledge_base_path="./knowledge_base/indexed")
    
    # Query for specific project
    context = tool.query(
        "software development qualified research four-part test",
        top_k=3
    )
    
    # Create agent prompt with formatted context
    agent_prompt_template = """
You are the R&D Tax Credit Qualification Agent. Your task is to determine 
whether the following project qualifies for R&D tax credit under IRC Section 41.

PROJECT INFORMATION:
- Name: Alpha Development - User Authentication System
- Hours: 145.5 hours
- Cost: $10,457.40
- Description: Development of a new multi-factor authentication system with 
  biometric integration, advanced encryption algorithms, and real-time threat 
  detection capabilities.

RELEVANT IRS GUIDANCE:
{context}

INSTRUCTIONS:
1. Evaluate the project against the four-part test
2. Determine qualification percentage (0-100%)
3. Assign confidence score (0-1)
4. Provide detailed reasoning
5. Include IRS citations from the context above

OUTPUT FORMAT:
{{
  "qualification_percentage": <0-100>,
  "confidence_score": <0-1>,
  "reasoning": "<detailed explanation>",
  "irs_citations": ["<citation 1>", "<citation 2>", ...],
  "flagged_for_review": <true/false>
}}
"""
    
    # Format the prompt
    final_prompt = agent_prompt_template.format(
        context=tool.format_for_llm(
            context,
            include_relevance_scores=True,
            include_metadata=False,
            max_chunks=3
        )
    )
    
    print(final_prompt)
    print("\n")


def main():
    """Run all examples"""
    print("\n")
    print("*" * 80)
    print("RD_Knowledge_Tool.format_for_llm() Examples")
    print("*" * 80)
    print("\n")
    
    try:
        # Run examples
        example_basic_formatting()
        example_without_relevance_scores()
        example_without_metadata()
        example_with_max_chunks()
        example_custom_template()
        example_minimal_formatting()
        example_comprehensive_formatting()
        example_empty_context()
        example_for_agent_prompt()
        
        print("*" * 80)
        print("All examples completed successfully!")
        print("*" * 80)
        
    except Exception as e:
        print(f"\nError running examples: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
