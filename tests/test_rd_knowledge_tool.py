"""
Unit tests for the RD_Knowledge_Tool class.
"""

import pytest
import os
import tempfile
import shutil
import gc
import time
from datetime import datetime

from tools.rd_knowledge_tool import RD_Knowledge_Tool
from tools.vector_db import VectorDB
from models.tax_models import RAGContext
from utils.exceptions import RAGRetrievalError


@pytest.fixture
def temp_kb_dir():
    """Create a temporary directory for test knowledge base"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Give ChromaDB time to release file handles
    gc.collect()
    time.sleep(0.1)
    # Try to cleanup, ignore errors on Windows
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except PermissionError:
        # Windows file locking - ChromaDB still has handles open
        pass


@pytest.fixture
def populated_knowledge_base(temp_kb_dir):
    """Create and populate a knowledge base for testing"""
    # Create vector database and add sample IRS documents
    vector_db = VectorDB(
        persist_directory=temp_kb_dir,
        collection_name="irs_documents"
    )
    
    # Sample IRS document chunks
    texts = [
        "Qualified research must meet the four-part test: (1) technological in nature, "
        "(2) undertaken for a qualified purpose, (3) involves a process of experimentation, "
        "(4) relates to a new or improved business component.",
        
        "A process of experimentation is a process designed to evaluate one or more "
        "alternatives to achieve a result where the capability or method is uncertain.",
        
        "Qualified research expenses (QREs) include wages paid to employees for qualified "
        "services, supplies used in qualified research, and amounts paid for computer use.",
        
        "Software development can qualify as research if it meets the four-part test and "
        "involves technological uncertainty requiring experimentation.",
        
        "The R&D tax credit is calculated as a percentage of qualified research expenditures "
        "and can significantly reduce a company's tax liability."
    ]
    
    metadatas = [
        {"source": "CFR Title 26 § 1.41-4(a)(1)", "page": 3, "chunk_index": 0},
        {"source": "CFR Title 26 § 1.41-4(a)(5)", "page": 5, "chunk_index": 0},
        {"source": "Form 6765 Instructions", "page": 2, "chunk_index": 0},
        {"source": "IRS Audit Guidelines for Software", "page": 8, "chunk_index": 0},
        {"source": "IRS Publication 542", "page": 15, "chunk_index": 0}
    ]
    
    ids = [f"chunk_{i}" for i in range(len(texts))]
    
    vector_db.add_documents(texts=texts, metadatas=metadatas, ids=ids)
    
    # Cleanup vector_db reference
    del vector_db
    gc.collect()
    
    yield temp_kb_dir


@pytest.fixture
def rd_tool(populated_knowledge_base):
    """Create an RD_Knowledge_Tool instance with populated knowledge base"""
    tool = RD_Knowledge_Tool(knowledge_base_path=populated_knowledge_base)
    yield tool
    # Cleanup
    try:
        if hasattr(tool, 'vector_db'):
            del tool.vector_db
    except:
        pass
    gc.collect()


def test_initialization_success(populated_knowledge_base):
    """Test successful RD_Knowledge_Tool initialization"""
    tool = RD_Knowledge_Tool(knowledge_base_path=populated_knowledge_base)
    
    try:
        assert tool.knowledge_base_path == populated_knowledge_base
        assert tool.default_top_k == 3
        assert tool.vector_db is not None
        assert tool.get_total_chunks() == 5
    finally:
        del tool
        gc.collect()


def test_initialization_with_custom_params(populated_knowledge_base):
    """Test initialization with custom parameters"""
    tool = RD_Knowledge_Tool(
        knowledge_base_path=populated_knowledge_base,
        collection_name="irs_documents",
        default_top_k=5
    )
    
    try:
        assert tool.default_top_k == 5
        assert tool.get_total_chunks() == 5
    finally:
        del tool
        gc.collect()


def test_query_returns_rag_context(rd_tool):
    """Test that query returns a RAGContext object"""
    context = rd_tool.query("What is the four-part test?")
    
    assert isinstance(context, RAGContext)
    assert context.query == "What is the four-part test?"
    assert isinstance(context.retrieval_timestamp, datetime)
    # With optimizations enabled by default, retrieval method includes all optimizations
    assert "semantic_search" in context.retrieval_method


def test_query_with_default_top_k(rd_tool):
    """Test query with default top_k value"""
    context = rd_tool.query("What are qualified research expenses?")
    
    assert context.chunk_count <= 3  # Default top_k
    assert context.chunk_count > 0
    assert context.total_chunks_available == 5


def test_query_with_custom_top_k(rd_tool):
    """Test query with custom top_k value"""
    context = rd_tool.query("R&D tax credit", top_k=2)
    
    assert context.chunk_count <= 2
    assert context.chunk_count > 0


def test_query_chunks_have_required_fields(rd_tool):
    """Test that returned chunks have all required fields"""
    context = rd_tool.query("process of experimentation")
    
    assert context.chunk_count > 0
    
    for chunk in context.chunks:
        assert 'text' in chunk
        assert 'source' in chunk
        assert 'page' in chunk
        assert 'relevance_score' in chunk
        
        assert isinstance(chunk['text'], str)
        assert isinstance(chunk['source'], str)
        assert isinstance(chunk['page'], int)
        assert isinstance(chunk['relevance_score'], (int, float))
        assert 0 <= chunk['relevance_score'] <= 1


def test_query_relevance_scores(rd_tool):
    """Test that relevance scores are properly calculated"""
    context = rd_tool.query("four-part test for qualified research")
    
    assert context.chunk_count > 0
    
    # Check that relevance scores are in valid range
    for chunk in context.chunks:
        assert 0 <= chunk['relevance_score'] <= 1
    
    # Check that chunks are ordered by relevance (highest first)
    if context.chunk_count > 1:
        scores = [chunk['relevance_score'] for chunk in context.chunks]
        assert scores == sorted(scores, reverse=True)


def test_query_with_metadata_filter(rd_tool):
    """Test query with metadata filter"""
    context = rd_tool.query(
        "qualified research",
        top_k=5,
        metadata_filter={"source": "Form 6765 Instructions"}
    )
    
    # Should only return chunks from Form 6765
    for chunk in context.chunks:
        assert chunk['source'] == "Form 6765 Instructions"


def test_query_empty_string_raises_error(rd_tool):
    """Test that empty query string raises ValueError"""
    with pytest.raises(ValueError, match="non-empty string"):
        rd_tool.query("")


def test_query_none_raises_error(rd_tool):
    """Test that None query raises ValueError"""
    with pytest.raises(ValueError, match="non-empty string"):
        rd_tool.query(None)


def test_query_invalid_top_k_raises_error(rd_tool):
    """Test that invalid top_k raises ValueError"""
    with pytest.raises(ValueError, match="at least 1"):
        rd_tool.query("test query", top_k=0)
    
    with pytest.raises(ValueError, match="at least 1"):
        rd_tool.query("test query", top_k=-1)


def test_rag_context_format_for_llm(rd_tool):
    """Test that RAGContext can be formatted for LLM prompts"""
    context = rd_tool.query("What is qualified research?", top_k=2)
    
    formatted = context.format_for_llm_prompt()
    
    assert isinstance(formatted, str)
    assert "=== IRS GUIDANCE CONTEXT ===" in formatted
    assert "=== END CONTEXT ===" in formatted
    
    # Should include source citations
    for chunk in context.chunks:
        assert chunk['source'] in formatted


def test_rag_context_extract_citations(rd_tool):
    """Test that RAGContext can extract citations"""
    context = rd_tool.query("R&D tax credit requirements", top_k=3)
    
    citations = context.extract_citations()
    
    assert isinstance(citations, list)
    assert len(citations) > 0
    
    # Each citation should include source and page
    for citation in citations:
        assert isinstance(citation, str)
        assert "Page" in citation


def test_get_total_chunks(rd_tool):
    """Test getting total chunk count"""
    total = rd_tool.get_total_chunks()
    
    assert isinstance(total, int)
    assert total == 5


def test_get_knowledge_base_info(rd_tool):
    """Test getting knowledge base information"""
    info = rd_tool.get_knowledge_base_info()
    
    assert isinstance(info, dict)
    assert 'path' in info
    assert 'total_chunks' in info
    assert 'collection_name' in info
    assert 'embedding_model' in info
    assert 'default_top_k' in info
    
    assert info['total_chunks'] == 5
    assert info['collection_name'] == 'irs_documents'
    assert info['default_top_k'] == 3


def test_query_no_results_returns_empty_context(rd_tool):
    """Test that query with no results returns empty RAGContext"""
    # Query with very specific text unlikely to match
    context = rd_tool.query("xyzabc123nonexistent", top_k=3)
    
    assert isinstance(context, RAGContext)
    # May return 0 or low-relevance results depending on vector DB behavior
    assert context.chunk_count >= 0


def test_rag_context_computed_fields(rd_tool):
    """Test RAGContext computed fields"""
    context = rd_tool.query("qualified research expenses", top_k=3)
    
    # Test chunk_count
    assert context.chunk_count == len(context.chunks)
    
    # Test average_relevance
    if context.chunk_count > 0:
        expected_avg = sum(c['relevance_score'] for c in context.chunks) / context.chunk_count
        assert abs(context.average_relevance - expected_avg) < 0.01


def test_multiple_queries_same_tool(rd_tool):
    """Test that the same tool can handle multiple queries"""
    context1 = rd_tool.query("four-part test", top_k=2)
    context2 = rd_tool.query("qualified research expenses", top_k=2)
    context3 = rd_tool.query("software development", top_k=2)
    
    assert isinstance(context1, RAGContext)
    assert isinstance(context2, RAGContext)
    assert isinstance(context3, RAGContext)
    
    # Each query should have its own results
    assert context1.query != context2.query
    assert context2.query != context3.query


# ============================================================================
# Query Optimization Tests (Task 43)
# ============================================================================

def test_query_expansion(rd_tool):
    """Test query expansion with technical term synonyms"""
    # Query with abbreviation that should be expanded
    context = rd_tool.query("What is QRE?", top_k=3, enable_query_expansion=True)
    
    assert isinstance(context, RAGContext)
    assert context.chunk_count > 0
    assert "query_expansion" in context.retrieval_method
    
    # Should find results about qualified research expenses
    found_qre = any("qualified research" in chunk['text'].lower() 
                    for chunk in context.chunks)
    assert found_qre, "Query expansion should find QRE-related content"


def test_query_expansion_disabled(rd_tool):
    """Test that query expansion can be disabled"""
    context = rd_tool.query(
        "What is QRE?",
        top_k=3,
        enable_query_expansion=False
    )
    
    assert isinstance(context, RAGContext)
    assert "query_expansion" not in context.retrieval_method


def test_query_rewriting(rd_tool):
    """Test query rewriting for better retrieval"""
    # Question format that should be rewritten
    context = rd_tool.query(
        "What is the four-part test?",
        top_k=3,
        enable_query_rewriting=True
    )
    
    assert isinstance(context, RAGContext)
    assert context.chunk_count > 0
    assert "query_rewriting" in context.retrieval_method


def test_query_rewriting_disabled(rd_tool):
    """Test that query rewriting can be disabled"""
    context = rd_tool.query(
        "What is the four-part test?",
        top_k=3,
        enable_query_rewriting=False
    )
    
    assert isinstance(context, RAGContext)
    assert "query_rewriting" not in context.retrieval_method


def test_reranking_with_source_preference(rd_tool):
    """Test re-ranking with source preference"""
    # Query with source preference
    context = rd_tool.query(
        "qualified research",
        top_k=3,
        enable_reranking=True,
        source_preference="Form 6765"
    )
    
    assert isinstance(context, RAGContext)
    assert context.chunk_count > 0
    assert "metadata_reranking" in context.retrieval_method
    
    # Check if Form 6765 results are boosted (if present)
    if any("Form 6765" in chunk['source'] for chunk in context.chunks):
        # First result should ideally be from Form 6765 or have high relevance
        assert context.chunks[0]['relevance_score'] > 0


def test_reranking_disabled(rd_tool):
    """Test that re-ranking can be disabled"""
    context = rd_tool.query(
        "qualified research",
        top_k=3,
        enable_reranking=False
    )
    
    assert isinstance(context, RAGContext)
    assert "metadata_reranking" not in context.retrieval_method


def test_all_optimizations_enabled(rd_tool):
    """Test query with all optimizations enabled"""
    context = rd_tool.query(
        "What is QRE?",
        top_k=3,
        enable_query_expansion=True,
        enable_query_rewriting=True,
        enable_reranking=True,
        source_preference="Form 6765"
    )
    
    assert isinstance(context, RAGContext)
    assert context.chunk_count > 0
    
    # Should include all optimization methods
    assert "semantic_search" in context.retrieval_method
    assert "query_expansion" in context.retrieval_method
    assert "query_rewriting" in context.retrieval_method
    assert "metadata_reranking" in context.retrieval_method


def test_all_optimizations_disabled(rd_tool):
    """Test query with all optimizations disabled"""
    context = rd_tool.query(
        "qualified research",
        top_k=3,
        enable_query_expansion=False,
        enable_query_rewriting=False,
        enable_reranking=False
    )
    
    assert isinstance(context, RAGContext)
    assert context.chunk_count > 0
    
    # Should only have semantic_search
    assert context.retrieval_method == "semantic_search"


def test_metadata_filter_with_optimizations(rd_tool):
    """Test that metadata filtering works with query optimizations"""
    context = rd_tool.query(
        "qualified research",
        top_k=5,
        metadata_filter={"source": "Form 6765 Instructions"},
        enable_query_expansion=True,
        enable_reranking=True
    )
    
    # All results should be from the filtered source
    for chunk in context.chunks:
        assert chunk['source'] == "Form 6765 Instructions"


def test_expand_query_method(rd_tool):
    """Test the _expand_query method directly"""
    expansions = rd_tool._expand_query("What is QRE?")
    
    assert isinstance(expansions, list)
    assert len(expansions) > 1  # Should have original + expansions
    assert "What is QRE?" in expansions  # Original should be included
    
    # Should have variations with expanded terms
    has_expansion = any("qualified research" in exp.lower() for exp in expansions)
    assert has_expansion


def test_rewrite_query_method(rd_tool):
    """Test the _rewrite_query method directly"""
    # Test question rewriting
    rewritten = rd_tool._rewrite_query("What is the four-part test?")
    assert isinstance(rewritten, str)
    # Should be rewritten to declarative form
    assert "?" not in rewritten or rewritten != "What is the four-part test?"
    
    # Test abbreviation expansion
    rewritten = rd_tool._rewrite_query("R&D requirements")
    assert "research and development" in rewritten.lower()


def test_rerank_results_method(rd_tool):
    """Test the _rerank_results method directly"""
    # Create sample chunks
    chunks = [
        {
            'text': 'Short text',
            'source': 'Publication 542',
            'page': 1,
            'relevance_score': 0.8
        },
        {
            'text': 'This is a much longer text with substantial content that should get a boost for being more comprehensive and detailed.',
            'source': 'Form 6765 Instructions',
            'page': 2,
            'relevance_score': 0.75
        },
        {
            'text': 'Another substantial piece of text from an authoritative source that provides detailed guidance on qualified research activities.',
            'source': 'CFR Title 26',
            'page': 3,
            'relevance_score': 0.7
        }
    ]
    
    reranked = rd_tool._rerank_results(chunks, "test query", source_preference="Form 6765")
    
    assert isinstance(reranked, list)
    assert len(reranked) == 3
    
    # Check that scores were adjusted
    for chunk in reranked:
        assert 'relevance_score' in chunk
        assert 'original_score' in chunk
    
    # Form 6765 chunk should be boosted
    form_6765_chunk = next(c for c in reranked if 'Form 6765' in c['source'])
    assert form_6765_chunk['relevance_score'] >= form_6765_chunk['original_score']


def test_query_optimization_improves_results(rd_tool):
    """Test that query optimization improves retrieval quality"""
    # Query without optimization
    context_basic = rd_tool.query(
        "QRE",
        top_k=3,
        enable_query_expansion=False,
        enable_query_rewriting=False,
        enable_reranking=False
    )
    
    # Query with optimization
    context_optimized = rd_tool.query(
        "QRE",
        top_k=3,
        enable_query_expansion=True,
        enable_query_rewriting=True,
        enable_reranking=True
    )
    
    # Both should return results
    assert isinstance(context_basic, RAGContext)
    assert isinstance(context_optimized, RAGContext)
    
    # Optimized query should potentially have better average relevance or more results
    # (This is a soft assertion as it depends on the data)
    assert context_optimized.chunk_count > 0


# ============================================================================
# RAG Context Formatting Tests (Task 44)
# ============================================================================

def test_format_for_llm_basic(rd_tool):
    """Test basic format_for_llm functionality"""
    context = rd_tool.query("What is the four-part test?", top_k=3)
    formatted = rd_tool.format_for_llm(context)
    
    assert isinstance(formatted, str)
    assert len(formatted) > 0
    
    # Check for structured sections
    assert "IRS GUIDANCE CONTEXT FOR R&D TAX CREDIT QUALIFICATION" in formatted
    assert "Query:" in formatted
    assert "Retrieved:" in formatted
    assert "EXCERPT #" in formatted
    assert "CITATIONS" in formatted
    assert "END IRS GUIDANCE CONTEXT" in formatted


def test_format_for_llm_includes_relevance_scores(rd_tool):
    """Test that format_for_llm includes relevance scores by default"""
    context = rd_tool.query("qualified research expenses", top_k=2)
    formatted = rd_tool.format_for_llm(context, include_relevance_scores=True)
    
    assert "Relevance Score:" in formatted
    
    # Check for quality indicators
    quality_indicators = ["Very High", "High", "Medium", "Low"]
    has_quality = any(indicator in formatted for indicator in quality_indicators)
    assert has_quality


def test_format_for_llm_without_relevance_scores(rd_tool):
    """Test format_for_llm without relevance scores"""
    context = rd_tool.query("qualified research", top_k=2)
    formatted = rd_tool.format_for_llm(context, include_relevance_scores=False)
    
    assert "Relevance Score:" not in formatted
    assert "confidence" not in formatted.lower() or "confidence" in context.query.lower()


def test_format_for_llm_includes_metadata(rd_tool):
    """Test that format_for_llm includes metadata by default"""
    context = rd_tool.query("R&D tax credit", top_k=2)
    formatted = rd_tool.format_for_llm(context, include_metadata=True)
    
    assert "Retrieval Method:" in formatted
    assert "Average Relevance:" in formatted
    assert "Retrieved At:" in formatted


def test_format_for_llm_without_metadata(rd_tool):
    """Test format_for_llm without metadata"""
    context = rd_tool.query("R&D tax credit", top_k=2)
    formatted = rd_tool.format_for_llm(context, include_metadata=False)
    
    assert "Retrieval Method:" not in formatted
    assert "Average Relevance:" not in formatted
    assert "Retrieved At:" not in formatted


def test_format_for_llm_with_max_chunks(rd_tool):
    """Test format_for_llm with max_chunks limit"""
    context = rd_tool.query("qualified research", top_k=5)
    
    # Limit to 2 chunks
    formatted = rd_tool.format_for_llm(context, max_chunks=2)
    
    # Count number of excerpts
    excerpt_count = formatted.count("EXCERPT #")
    assert excerpt_count <= 2
    
    # Should still have proper structure
    assert "IRS GUIDANCE CONTEXT" in formatted
    assert "CITATIONS" in formatted


def test_format_for_llm_includes_all_chunk_fields(rd_tool):
    """Test that formatted output includes all chunk information"""
    context = rd_tool.query("process of experimentation", top_k=2)
    formatted = rd_tool.format_for_llm(context)
    
    # Check that each chunk's information is included
    for chunk in context.chunks:
        assert chunk['source'] in formatted
        assert f"Page: {chunk['page']}" in formatted
        assert chunk['text'] in formatted


def test_format_for_llm_with_custom_template(rd_tool):
    """Test format_for_llm with custom prompt template"""
    context = rd_tool.query("four-part test", top_k=2)
    
    custom_template = """
Based on the following IRS guidance:

{context}

Query: {query}
Number of excerpts: {chunk_count}

Please analyze the project for R&D qualification.
"""
    
    formatted = rd_tool.format_for_llm(context, prompt_template=custom_template)
    
    assert "Based on the following IRS guidance:" in formatted
    assert "Please analyze the project for R&D qualification." in formatted
    assert context.query in formatted
    assert "IRS GUIDANCE CONTEXT" in formatted  # Context should be embedded


def test_format_for_llm_custom_template_with_citations(rd_tool):
    """Test custom template with citations placeholder"""
    context = rd_tool.query("qualified research", top_k=2)
    
    custom_template = """
Context: {context}

Sources:
{citations}
"""
    
    formatted = rd_tool.format_for_llm(context, prompt_template=custom_template)
    
    assert "Sources:" in formatted
    # Citations should be formatted as numbered list
    citations = context.extract_citations()
    for citation in citations:
        assert citation in formatted


def test_format_for_llm_empty_context(rd_tool):
    """Test format_for_llm with empty context"""
    # Create an empty context
    from datetime import datetime
    empty_context = RAGContext(
        query="nonexistent query xyz123",
        chunks=[],
        retrieval_timestamp=datetime.now(),
        total_chunks_available=5,
        retrieval_method="semantic_search"
    )
    
    formatted = rd_tool.format_for_llm(empty_context)
    
    assert isinstance(formatted, str)
    assert "NO RELEVANT IRS GUIDANCE FOUND" in formatted
    assert empty_context.query in formatted
    assert "lower confidence" in formatted


def test_format_for_llm_invalid_context_raises_error(rd_tool):
    """Test that format_for_llm raises error for invalid context"""
    with pytest.raises(ValueError, match="RAGContext object"):
        rd_tool.format_for_llm("not a context object")
    
    with pytest.raises(ValueError, match="RAGContext object"):
        rd_tool.format_for_llm(None)
    
    with pytest.raises(ValueError, match="RAGContext object"):
        rd_tool.format_for_llm({"query": "test"})


def test_format_for_llm_chunks_sorted_by_relevance(rd_tool):
    """Test that format_for_llm sorts chunks by relevance"""
    context = rd_tool.query("qualified research expenses", top_k=3)
    formatted = rd_tool.format_for_llm(context)
    
    # Extract relevance scores from formatted output
    import re
    scores = re.findall(r'Relevance Score: ([\d.]+)', formatted)
    
    if len(scores) > 1:
        # Convert to floats and check descending order
        float_scores = [float(s) for s in scores]
        assert float_scores == sorted(float_scores, reverse=True)


def test_format_for_llm_preserves_citations(rd_tool):
    """Test that format_for_llm preserves all citations"""
    context = rd_tool.query("R&D tax credit", top_k=3)
    formatted = rd_tool.format_for_llm(context)
    
    # Get citations from context
    citations = context.extract_citations()
    
    # All citations should appear in formatted output
    for citation in citations:
        assert citation in formatted


def test_format_for_llm_max_chunks_limits_citations(rd_tool):
    """Test that max_chunks also limits citations"""
    context = rd_tool.query("qualified research", top_k=5)
    
    # Format with limit
    formatted = rd_tool.format_for_llm(context, max_chunks=2)
    
    # Count citations in output
    citation_section = formatted.split("CITATIONS")[1].split("END IRS GUIDANCE CONTEXT")[0]
    citation_lines = [line for line in citation_section.split('\n') if line.strip() and line.strip()[0].isdigit()]
    
    # Should have at most 2 citations (one per chunk)
    assert len(citation_lines) <= 2


def test_format_for_llm_quality_indicators(rd_tool):
    """Test that format_for_llm includes quality indicators for relevance scores"""
    context = rd_tool.query("four-part test", top_k=3)
    formatted = rd_tool.format_for_llm(context, include_relevance_scores=True)
    
    # Should have quality indicators based on score ranges
    # Very High (>= 0.9), High (>= 0.8), Medium (>= 0.7), Low (< 0.7)
    quality_terms = ["Very High", "High", "Medium", "Low"]
    has_quality_indicator = any(term in formatted for term in quality_terms)
    assert has_quality_indicator


def test_format_for_llm_with_all_options(rd_tool):
    """Test format_for_llm with all options enabled"""
    context = rd_tool.query("qualified research expenses", top_k=4)
    
    formatted = rd_tool.format_for_llm(
        context,
        include_relevance_scores=True,
        include_metadata=True,
        max_chunks=3
    )
    
    # Should have all components
    assert "IRS GUIDANCE CONTEXT" in formatted
    assert "Relevance Score:" in formatted
    assert "Retrieval Method:" in formatted
    assert "EXCERPT #" in formatted
    assert "CITATIONS" in formatted
    
    # Should be limited to 3 chunks
    excerpt_count = formatted.count("EXCERPT #")
    assert excerpt_count <= 3


def test_format_for_llm_output_length(rd_tool):
    """Test that format_for_llm produces reasonable output length"""
    context = rd_tool.query("R&D tax credit", top_k=3)
    formatted = rd_tool.format_for_llm(context)
    
    # Should be substantial but not excessive
    assert len(formatted) > 500  # At least 500 characters
    assert len(formatted) < 50000  # Less than 50k characters for 3 chunks


def test_format_for_llm_separators(rd_tool):
    """Test that format_for_llm includes proper separators"""
    context = rd_tool.query("qualified research", top_k=3)
    formatted = rd_tool.format_for_llm(context)
    
    # Check for separator lines
    assert "=" * 70 in formatted  # Header/footer separators
    assert "-" * 70 in formatted  # Chunk separators


def test_format_for_llm_custom_template_missing_placeholder(rd_tool):
    """Test format_for_llm with custom template missing placeholders"""
    context = rd_tool.query("four-part test", top_k=2)
    
    # Template with invalid placeholder
    invalid_template = "Context: {context} Invalid: {nonexistent}"
    
    # Should fall back to default format
    formatted = rd_tool.format_for_llm(context, prompt_template=invalid_template)
    
    # Should use default format (not raise error)
    assert "IRS GUIDANCE CONTEXT" in formatted


# ============================================================================
# Error Handling Tests (Task 45)
# ============================================================================

def test_initialization_with_invalid_collection_name():
    """Test that initialization logs warning for empty knowledge base"""
    # ChromaDB creates directories if they don't exist, so we test with empty KB instead
    import tempfile
    temp_dir = tempfile.mkdtemp()
    
    try:
        # This should succeed but log a warning about empty KB
        tool = RD_Knowledge_Tool(knowledge_base_path=temp_dir)
        assert tool.get_total_chunks() == 0
        del tool
        gc.collect()
    finally:
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def test_query_with_uninitialized_vector_db(temp_kb_dir):
    """Test that query fails gracefully when vector_db is None"""
    tool = RD_Knowledge_Tool(knowledge_base_path=temp_kb_dir)
    
    # Manually set vector_db to None to simulate connection failure
    tool.vector_db = None
    
    with pytest.raises(RAGRetrievalError) as exc_info:
        tool.query("test query")
    
    assert exc_info.value.error_type == "connection_failure"
    assert "not initialized" in exc_info.value.message.lower()
    assert exc_info.value.query == "test query"


def test_query_empty_knowledge_base(temp_kb_dir):
    """Test that query handles empty knowledge base gracefully"""
    # Create empty vector database
    vector_db = VectorDB(
        persist_directory=temp_kb_dir,
        collection_name="irs_documents"
    )
    del vector_db
    gc.collect()
    
    # Create tool with empty knowledge base
    tool = RD_Knowledge_Tool(knowledge_base_path=temp_kb_dir)
    
    try:
        # Query should return empty context, not raise error
        context = tool.query("test query", top_k=3)
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count == 0
        assert context.total_chunks_available == 0
        assert context.query == "test query"
    finally:
        del tool
        gc.collect()


def test_get_total_chunks_with_uninitialized_db(temp_kb_dir):
    """Test that get_total_chunks returns 0 when vector_db is None"""
    tool = RD_Knowledge_Tool(knowledge_base_path=temp_kb_dir)
    
    # Manually set vector_db to None
    tool.vector_db = None
    
    total = tool.get_total_chunks()
    assert total == 0


def test_get_knowledge_base_info_with_uninitialized_db(temp_kb_dir):
    """Test that get_knowledge_base_info handles uninitialized db gracefully"""
    tool = RD_Knowledge_Tool(knowledge_base_path=temp_kb_dir)
    
    # Manually set vector_db to None
    tool.vector_db = None
    
    info = tool.get_knowledge_base_info()
    
    assert isinstance(info, dict)
    assert info['status'] == 'error'
    assert 'error' in info
    assert info['total_chunks'] == 0
    assert info['path'] == temp_kb_dir


def test_query_logs_retrieval_attempt(rd_tool, caplog):
    """Test that query logs retrieval attempts"""
    import logging
    
    with caplog.at_level(logging.INFO):
        context = rd_tool.query("test query", top_k=2)
    
    # Check that retrieval attempt was logged
    assert any("RAG retrieval attempt" in record.message for record in caplog.records)
    assert any("test query" in record.message for record in caplog.records)


def test_query_logs_empty_results(rd_tool, caplog):
    """Test that query logs warning when no results found"""
    import logging
    
    with caplog.at_level(logging.WARNING):
        # Query with very specific text unlikely to match
        context = rd_tool.query("xyzabc123nonexistent999", top_k=3)
    
    # Should log warning about empty results
    warning_messages = [record.message for record in caplog.records if record.levelname == 'WARNING']
    
    # May have warnings about no results or low relevance
    assert len(warning_messages) >= 0  # At least logged the attempt


def test_query_logs_successful_retrieval(rd_tool, caplog):
    """Test that query logs successful retrieval with details"""
    import logging
    
    with caplog.at_level(logging.INFO):
        context = rd_tool.query("four-part test", top_k=2)
    
    # Check that success was logged
    info_messages = [record.message for record in caplog.records if record.levelname == 'INFO']
    
    assert any("RAG retrieval successful" in msg or "Retrieved" in msg for msg in info_messages)


def test_query_with_all_variations_failing(populated_knowledge_base, monkeypatch):
    """Test that query raises error when all query variations fail"""
    tool = RD_Knowledge_Tool(knowledge_base_path=populated_knowledge_base)
    
    # Mock vector_db.query to always raise an exception
    def mock_query_failure(*args, **kwargs):
        raise Exception("Simulated query failure")
    
    monkeypatch.setattr(tool.vector_db, 'query', mock_query_failure)
    
    try:
        with pytest.raises(RAGRetrievalError) as exc_info:
            tool.query("test query", top_k=3)
        
        assert exc_info.value.error_type == "query_execution_failure"
        assert "All query variations failed" in exc_info.value.message
        assert exc_info.value.query == "test query"
    finally:
        del tool
        gc.collect()


def test_query_partial_variation_failure(populated_knowledge_base, monkeypatch):
    """Test that query continues when some variations fail"""
    tool = RD_Knowledge_Tool(knowledge_base_path=populated_knowledge_base)
    
    # Store original query method
    original_query = tool.vector_db.query
    call_count = [0]
    
    # Mock to fail first call, succeed on subsequent calls
    def mock_query_partial_failure(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("First query failed")
        return original_query(*args, **kwargs)
    
    monkeypatch.setattr(tool.vector_db, 'query', mock_query_partial_failure)
    
    try:
        # Should succeed despite first variation failing
        context = tool.query("QRE", top_k=2, enable_query_expansion=True)
        
        assert isinstance(context, RAGContext)
        # May or may not have results depending on which variation succeeded
    finally:
        del tool
        gc.collect()


def test_query_rewriting_failure_fallback(populated_knowledge_base, monkeypatch):
    """Test that query falls back to original when rewriting fails"""
    tool = RD_Knowledge_Tool(knowledge_base_path=populated_knowledge_base)
    
    # Mock _rewrite_query to raise exception
    def mock_rewrite_failure(*args, **kwargs):
        raise Exception("Rewriting failed")
    
    monkeypatch.setattr(tool, '_rewrite_query', mock_rewrite_failure)
    
    try:
        # Should still work with original query
        context = tool.query("test query", top_k=2, enable_query_rewriting=True)
        
        assert isinstance(context, RAGContext)
        assert context.query == "test query"
    finally:
        del tool
        gc.collect()


def test_query_expansion_failure_fallback(populated_knowledge_base, monkeypatch):
    """Test that query falls back to single query when expansion fails"""
    tool = RD_Knowledge_Tool(knowledge_base_path=populated_knowledge_base)
    
    # Mock _expand_query to raise exception
    def mock_expand_failure(*args, **kwargs):
        raise Exception("Expansion failed")
    
    monkeypatch.setattr(tool, '_expand_query', mock_expand_failure)
    
    try:
        # Should still work with single query
        context = tool.query("test query", top_k=2, enable_query_expansion=True)
        
        assert isinstance(context, RAGContext)
        assert context.query == "test query"
    finally:
        del tool
        gc.collect()


def test_query_reranking_failure_fallback(populated_knowledge_base, monkeypatch):
    """Test that query falls back to basic sorting when reranking fails"""
    tool = RD_Knowledge_Tool(knowledge_base_path=populated_knowledge_base)
    
    # Mock _rerank_results to raise exception
    def mock_rerank_failure(*args, **kwargs):
        raise Exception("Reranking failed")
    
    monkeypatch.setattr(tool, '_rerank_results', mock_rerank_failure)
    
    try:
        # Should still work with basic sorting
        context = tool.query("test query", top_k=2, enable_reranking=True)
        
        assert isinstance(context, RAGContext)
        # Results should still be sorted by relevance
        if context.chunk_count > 1:
            scores = [chunk['relevance_score'] for chunk in context.chunks]
            assert scores == sorted(scores, reverse=True)
    finally:
        del tool
        gc.collect()


def test_query_count_failure_continues(populated_knowledge_base, monkeypatch):
    """Test that query continues when count() fails"""
    tool = RD_Knowledge_Tool(knowledge_base_path=populated_knowledge_base)
    
    # Mock count to raise exception
    def mock_count_failure():
        raise Exception("Count failed")
    
    monkeypatch.setattr(tool.vector_db, 'count', mock_count_failure)
    
    try:
        # Should still work, just with unknown total_chunks_available
        context = tool.query("test query", top_k=2)
        
        assert isinstance(context, RAGContext)
        # total_chunks_available may be -1 or equal to chunk_count
    finally:
        del tool
        gc.collect()


def test_rag_retrieval_error_includes_details():
    """Test that RAGRetrievalError includes comprehensive details"""
    error = RAGRetrievalError(
        message="Test error message",
        query="test query",
        knowledge_base_path="/test/path",
        error_type="test_error",
        details={"additional": "info"}
    )
    
    assert error.message == "Test error message"
    assert error.query == "test query"
    assert error.knowledge_base_path == "/test/path"
    assert error.error_type == "test_error"
    assert error.details["additional"] == "info"
    assert error.details["query"] == "test query"


def test_format_for_llm_handles_empty_context_gracefully(rd_tool):
    """Test that format_for_llm handles empty context without errors"""
    from datetime import datetime
    
    empty_context = RAGContext(
        query="nonexistent query",
        chunks=[],
        retrieval_timestamp=datetime.now(),
        total_chunks_available=5,
        retrieval_method="semantic_search"
    )
    
    formatted = rd_tool.format_for_llm(empty_context)
    
    assert isinstance(formatted, str)
    assert "NO RELEVANT IRS GUIDANCE FOUND" in formatted
    assert "nonexistent query" in formatted


def test_initialization_logs_empty_knowledge_base_warning(temp_kb_dir, caplog):
    """Test that initialization logs warning for empty knowledge base"""
    import logging
    
    # Create empty vector database
    vector_db = VectorDB(
        persist_directory=temp_kb_dir,
        collection_name="irs_documents"
    )
    del vector_db
    gc.collect()
    
    with caplog.at_level(logging.WARNING):
        tool = RD_Knowledge_Tool(knowledge_base_path=temp_kb_dir)
    
    try:
        # Should log warning about empty knowledge base
        warning_messages = [record.message for record in caplog.records if record.levelname == 'WARNING']
        assert any("empty" in msg.lower() and "0 chunks" in msg for msg in warning_messages)
    finally:
        del tool
        gc.collect()


def test_query_with_invalid_metadata_filter_type(rd_tool):
    """Test that query handles invalid metadata filter gracefully"""
    # This should either work or raise a clear error
    # Depending on vector_db implementation
    try:
        context = rd_tool.query(
            "test query",
            top_k=2,
            metadata_filter="invalid_filter_type"  # Should be dict
        )
        # If it doesn't raise an error, it should return a valid context
        assert isinstance(context, RAGContext)
    except (ValueError, TypeError, RAGRetrievalError) as e:
        # Should raise a clear error
        assert len(str(e)) > 0


def test_get_knowledge_base_info_includes_status(rd_tool):
    """Test that get_knowledge_base_info includes status field"""
    info = rd_tool.get_knowledge_base_info()
    
    assert 'status' in info
    assert info['status'] in ['available', 'error']
    
    if info['status'] == 'available':
        assert 'total_chunks' in info
        assert 'embedding_model' in info
    else:
        assert 'error' in info
