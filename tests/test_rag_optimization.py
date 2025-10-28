"""
RAG Optimization Tests

This module tests the optimization features added to the RD_Knowledge_Tool:
- Query caching
- Batch query support
- Cache management
- Configurable parameters

Requirements: 2.2 (Task 51)
"""

import pytest
import time
from pathlib import Path
import tempfile
import shutil

from tools.rd_knowledge_tool import RD_Knowledge_Tool
from tools.indexing_pipeline import index_documents
from models.tax_models import RAGContext


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def indexed_knowledge_base():
    """Create and index a knowledge base for testing"""
    kb_path = Path("knowledge_base")
    
    if not kb_path.exists():
        pytest.skip("Knowledge base not available for testing")
    
    indexed_path = kb_path / "indexed"
    metadata_path = kb_path / "metadata.json"
    
    if not metadata_path.exists():
        pytest.skip("Knowledge base metadata not available")
    
    # Index if needed
    import json
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    needs_indexing = any(
        not doc.get('indexed', False)
        for doc in metadata.get('documents', [])
    )
    
    if needs_indexing:
        index_documents(
            knowledge_base_path=str(kb_path),
            chunk_size=512,
            overlap=50,
            force_reindex=False
        )
    
    yield str(indexed_path)


@pytest.fixture
def rd_tool_with_cache(indexed_knowledge_base):
    """Create RD_Knowledge_Tool with caching enabled"""
    tool = RD_Knowledge_Tool(
        knowledge_base_path=indexed_knowledge_base,
        enable_cache=True,
        cache_ttl=3600
    )
    yield tool
    tool.clear_cache()


@pytest.fixture
def rd_tool_without_cache(indexed_knowledge_base):
    """Create RD_Knowledge_Tool with caching disabled"""
    tool = RD_Knowledge_Tool(
        knowledge_base_path=indexed_knowledge_base,
        enable_cache=False
    )
    yield tool


# ============================================================================
# Query Caching Tests
# ============================================================================

class TestQueryCaching:
    """Test query caching functionality"""
    
    def test_cache_enabled_by_default(self, indexed_knowledge_base):
        """Test that caching is enabled by default"""
        tool = RD_Knowledge_Tool(knowledge_base_path=indexed_knowledge_base)
        assert tool.enable_cache is True
        assert tool.cache_ttl == 3600
    
    def test_cache_can_be_disabled(self, indexed_knowledge_base):
        """Test that caching can be disabled"""
        tool = RD_Knowledge_Tool(
            knowledge_base_path=indexed_knowledge_base,
            enable_cache=False
        )
        assert tool.enable_cache is False
    
    def test_repeated_query_uses_cache(self, rd_tool_with_cache):
        """Test that repeated queries use cache"""
        question = "What is the four-part test?"
        
        # First query
        context1 = rd_tool_with_cache.query(question, top_k=3)
        assert isinstance(context1, RAGContext)
        
        # Check cache stats
        stats = rd_tool_with_cache.get_cache_stats()
        assert stats['size'] == 1
        
        # Second query (should hit cache)
        context2 = rd_tool_with_cache.query(question, top_k=3)
        assert isinstance(context2, RAGContext)
        
        # Cache size should still be 1
        stats = rd_tool_with_cache.get_cache_stats()
        assert stats['size'] == 1
        
        # Results should be identical
        assert context1.chunk_count == context2.chunk_count
        assert context1.query == context2.query
    
    def test_cache_improves_performance(self, rd_tool_with_cache):
        """Test that cache improves query performance"""
        question = "What are qualified research expenses?"
        
        # First query (no cache)
        start_time = time.time()
        context1 = rd_tool_with_cache.query(question, top_k=3)
        time1 = time.time() - start_time
        
        # Second query (from cache)
        start_time = time.time()
        context2 = rd_tool_with_cache.query(question, top_k=3)
        time2 = time.time() - start_time
        
        # Cached query should be faster
        assert time2 < time1
        print(f"\n  First query: {time1:.3f}s, Cached query: {time2:.3f}s, Speedup: {time1/time2:.1f}x")
    
    def test_different_parameters_create_different_cache_entries(self, rd_tool_with_cache):
        """Test that different query parameters create separate cache entries"""
        question = "What is the four-part test?"
        
        # Query with top_k=3
        context1 = rd_tool_with_cache.query(question, top_k=3)
        
        # Query with top_k=5 (different parameter)
        context2 = rd_tool_with_cache.query(question, top_k=5)
        
        # Should have 2 cache entries
        stats = rd_tool_with_cache.get_cache_stats()
        assert stats['size'] == 2
        
        # Results should be different
        assert context1.chunk_count != context2.chunk_count
    
    def test_cache_clear(self, rd_tool_with_cache):
        """Test cache clearing"""
        # Add some queries to cache
        questions = [
            "What is the four-part test?",
            "What are QRE?",
            "What is technological uncertainty?"
        ]
        
        for question in questions:
            rd_tool_with_cache.query(question, top_k=3)
        
        # Check cache has entries
        stats = rd_tool_with_cache.get_cache_stats()
        assert stats['size'] == 3
        
        # Clear cache
        cleared_count = rd_tool_with_cache.clear_cache()
        assert cleared_count == 3
        
        # Check cache is empty
        stats = rd_tool_with_cache.get_cache_stats()
        assert stats['size'] == 0
    
    def test_cache_stats(self, rd_tool_with_cache):
        """Test cache statistics"""
        # Empty cache
        stats = rd_tool_with_cache.get_cache_stats()
        assert stats['enabled'] is True
        assert stats['size'] == 0
        assert stats['ttl_seconds'] == 3600
        assert stats['oldest_entry_age_seconds'] is None
        
        # Add a query
        rd_tool_with_cache.query("What is the four-part test?", top_k=3)
        
        # Check stats
        stats = rd_tool_with_cache.get_cache_stats()
        assert stats['size'] == 1
        assert stats['oldest_entry_age_seconds'] is not None
        assert stats['newest_entry_age_seconds'] is not None
        assert stats['average_age_seconds'] is not None
    
    def test_cache_disabled_no_caching(self, rd_tool_without_cache):
        """Test that queries are not cached when caching is disabled"""
        question = "What is the four-part test?"
        
        # Execute query
        rd_tool_without_cache.query(question, top_k=3)
        
        # Cache should be empty
        stats = rd_tool_without_cache.get_cache_stats()
        assert stats['size'] == 0


# ============================================================================
# Batch Query Tests
# ============================================================================

class TestBatchQuery:
    """Test batch query functionality"""
    
    def test_batch_query_basic(self, rd_tool_with_cache):
        """Test basic batch query functionality"""
        questions = [
            "What is the four-part test?",
            "What are qualified research expenses?",
            "What is a process of experimentation?"
        ]
        
        result = rd_tool_with_cache.batch_query(questions, top_k=3)
        
        # Check result structure
        assert 'results' in result
        assert 'questions' in result
        assert 'total_queries' in result
        assert 'successful_queries' in result
        assert 'failed_queries' in result
        assert 'cache_hits' in result
        assert 'errors' in result
        
        # Check values
        assert result['total_queries'] == 3
        assert result['successful_queries'] == 3
        assert result['failed_queries'] == 0
        assert len(result['results']) == 3
        assert len(result['errors']) == 0
        
        # Check all results are RAGContext objects
        for context in result['results']:
            assert isinstance(context, RAGContext)
    
    def test_batch_query_with_cache_hits(self, rd_tool_with_cache):
        """Test that batch query benefits from cache"""
        questions = [
            "What is the four-part test?",
            "What are QRE?",
            "What is technological uncertainty?"
        ]
        
        # First batch (no cache hits)
        result1 = rd_tool_with_cache.batch_query(questions, top_k=3)
        assert result1['cache_hits'] == 0
        
        # Second batch (all cache hits)
        result2 = rd_tool_with_cache.batch_query(questions, top_k=3)
        assert result2['cache_hits'] == 3
        assert result2['cache_hit_rate'] == 100.0
    
    def test_batch_query_partial_cache_hits(self, rd_tool_with_cache):
        """Test batch query with partial cache hits"""
        # First batch
        batch1 = [
            "What is the four-part test?",
            "What are QRE?"
        ]
        rd_tool_with_cache.batch_query(batch1, top_k=3)
        
        # Second batch with overlap
        batch2 = [
            "What is the four-part test?",  # Cache hit
            "What is technological uncertainty?",  # Cache miss
            "What are QRE?"  # Cache hit
        ]
        
        result = rd_tool_with_cache.batch_query(batch2, top_k=3)
        assert result['cache_hits'] == 2
        assert result['cache_hit_rate'] == pytest.approx(66.67, rel=0.1)
    
    def test_batch_query_empty_list(self, rd_tool_with_cache):
        """Test batch query with empty list raises error"""
        with pytest.raises(ValueError, match="non-empty list"):
            rd_tool_with_cache.batch_query([])
    
    def test_batch_query_invalid_questions(self, rd_tool_with_cache):
        """Test batch query with invalid questions raises error"""
        with pytest.raises(ValueError, match="non-empty strings"):
            rd_tool_with_cache.batch_query(["Valid question", "", "Another valid"])
    
    def test_batch_query_continue_on_error(self, rd_tool_with_cache):
        """Test batch query continues on error when configured"""
        # Mix of valid and potentially problematic queries
        questions = [
            "What is the four-part test?",
            "What are QRE?",
            "What is technological uncertainty?"
        ]
        
        result = rd_tool_with_cache.batch_query(
            questions,
            top_k=3,
            continue_on_error=True
        )
        
        # Should complete all queries
        assert result['total_queries'] == 3
        assert result['successful_queries'] >= 0
        assert result['failed_queries'] >= 0
        assert result['successful_queries'] + result['failed_queries'] == 3
    
    def test_batch_query_performance(self, rd_tool_with_cache):
        """Test batch query performance"""
        questions = [
            "What is the four-part test?",
            "What are qualified research expenses?",
            "What is a process of experimentation?",
            "What are wage limitations?",
            "Can software development qualify?"
        ]
        
        # Measure batch query time
        start_time = time.time()
        result = rd_tool_with_cache.batch_query(questions, top_k=3)
        batch_time = time.time() - start_time
        
        # Should complete in reasonable time (< 25 seconds for 5 queries)
        assert batch_time < 25.0
        
        avg_time = batch_time / len(questions)
        print(f"\n  Batch query: {batch_time:.3f}s total, {avg_time:.3f}s per query")
        
        # All queries should succeed
        assert result['successful_queries'] == 5


# ============================================================================
# Configurable Parameters Tests
# ============================================================================

class TestConfigurableParameters:
    """Test configurable parameters"""
    
    def test_custom_default_top_k(self, indexed_knowledge_base):
        """Test custom default top_k parameter"""
        tool = RD_Knowledge_Tool(
            knowledge_base_path=indexed_knowledge_base,
            default_top_k=5
        )
        
        # Query without specifying top_k
        context = tool.query("What is the four-part test?")
        
        # Should retrieve 5 chunks (or less if not available)
        assert context.chunk_count <= 5
    
    def test_custom_cache_ttl(self, indexed_knowledge_base):
        """Test custom cache TTL parameter"""
        tool = RD_Knowledge_Tool(
            knowledge_base_path=indexed_knowledge_base,
            enable_cache=True,
            cache_ttl=7200  # 2 hours
        )
        
        stats = tool.get_cache_stats()
        assert stats['ttl_seconds'] == 7200
    
    def test_query_with_different_top_k_values(self, rd_tool_with_cache):
        """Test querying with different top_k values"""
        question = "What are qualified research expenses?"
        
        # Query with top_k=1
        context1 = rd_tool_with_cache.query(question, top_k=1)
        assert context1.chunk_count <= 1
        
        # Query with top_k=5
        context2 = rd_tool_with_cache.query(question, top_k=5)
        assert context2.chunk_count <= 5
        
        # Query with top_k=10
        context3 = rd_tool_with_cache.query(question, top_k=10)
        assert context3.chunk_count <= 10


# ============================================================================
# Integration Tests
# ============================================================================

class TestOptimizationIntegration:
    """Test integration of optimization features"""
    
    def test_batch_query_with_optimizations(self, rd_tool_with_cache):
        """Test batch query with all optimizations enabled"""
        questions = [
            "What is the four-part test?",
            "What are QRE?",  # Abbreviation (tests query expansion)
            "What is technological uncertainty?"
        ]
        
        result = rd_tool_with_cache.batch_query(
            questions,
            top_k=3,
            enable_query_expansion=True,
            enable_query_rewriting=True,
            enable_reranking=True
        )
        
        assert result['successful_queries'] == 3
        
        # Check that results have expected retrieval methods
        for context in result['results']:
            if context is not None:
                assert 'semantic_search' in context.retrieval_method
    
    def test_cache_with_different_optimization_settings(self, rd_tool_with_cache):
        """Test that different optimization settings create separate cache entries"""
        question = "What is the four-part test?"
        
        # Query with all optimizations
        context1 = rd_tool_with_cache.query(
            question,
            top_k=3,
            enable_query_expansion=True,
            enable_query_rewriting=True,
            enable_reranking=True
        )
        
        # Query with no optimizations
        context2 = rd_tool_with_cache.query(
            question,
            top_k=3,
            enable_query_expansion=False,
            enable_query_rewriting=False,
            enable_reranking=False
        )
        
        # Should have 2 cache entries
        stats = rd_tool_with_cache.get_cache_stats()
        assert stats['size'] == 2
    
    def test_realistic_workflow(self, rd_tool_with_cache):
        """Test realistic workflow with multiple projects"""
        # Simulate querying for multiple R&D projects
        project_questions = [
            "What is the four-part test for qualified research?",
            "What are qualified research expenses?",
            "Can software development qualify for R&D credit?",
            "What is a process of experimentation?",
            "What are the wage limitations for R&D credit?"
        ]
        
        # First pass - no cache
        print("\n  First pass (no cache):")
        start_time = time.time()
        result1 = rd_tool_with_cache.batch_query(project_questions, top_k=3)
        time1 = time.time() - start_time
        print(f"    Time: {time1:.3f}s, Cache hits: {result1['cache_hits']}")
        
        # Second pass - with cache
        print("  Second pass (with cache):")
        start_time = time.time()
        result2 = rd_tool_with_cache.batch_query(project_questions, top_k=3)
        time2 = time.time() - start_time
        print(f"    Time: {time2:.3f}s, Cache hits: {result2['cache_hits']}")
        
        # Second pass should be faster
        assert time2 < time1
        assert result2['cache_hits'] == len(project_questions)
        
        print(f"    Speedup: {time1/time2:.1f}x")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
