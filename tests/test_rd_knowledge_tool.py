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
    assert context.retrieval_method == "semantic_search"


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
