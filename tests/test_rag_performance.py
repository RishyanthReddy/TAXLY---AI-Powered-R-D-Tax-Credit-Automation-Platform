"""
RAG Performance Benchmarks

This module contains performance benchmarks for the RAG (Retrieval-Augmented Generation) system.
Tests measure query latency, retrieval accuracy, and performance with various query types.

Performance Targets:
- Query latency: < 5 seconds per query
- Retrieval accuracy: > 80% for known test questions
- Consistent performance across query types (specific vs. general)

Requirements: 2.2 (Task 50)
"""

import pytest
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any
import tempfile
import shutil
import gc

from tools.rd_knowledge_tool import RD_Knowledge_Tool
from tools.indexing_pipeline import index_documents
from models.tax_models import RAGContext


# ============================================================================
# Test Data: Known Questions with Expected Keywords
# ============================================================================

# Specific queries - target specific IRS guidance sections
SPECIFIC_QUERIES = [
    {
        "query": "What is the four-part test for qualified research?",
        "expected_keywords": ["technological", "qualified purpose", "experimentation", "business component"],
        "min_relevance": 0.6
    },
    {
        "query": "What are qualified research expenses?",
        "expected_keywords": ["wages", "supplies", "research", "expense"],
        "min_relevance": 0.6
    },
    {
        "query": "What is a process of experimentation?",
        "expected_keywords": ["evaluate", "alternatives", "uncertain", "capability"],
        "min_relevance": 0.6
    },
    {
        "query": "What are the wage limitations for R&D credit?",
        "expected_keywords": ["wage", "research", "credit", "expense"],
        "min_relevance": 0.5
    },
    {
        "query": "Can software development qualify for R&D credit?",
        "expected_keywords": ["software", "development", "technological", "uncertainty"],
        "min_relevance": 0.5
    }
]

# General queries - broader topics that may retrieve multiple relevant sections
GENERAL_QUERIES = [
    {
        "query": "R&D tax credit requirements",
        "expected_keywords": ["qualified", "research", "credit", "requirements"],
        "min_relevance": 0.4
    },
    {
        "query": "How to qualify for research and development tax credit",
        "expected_keywords": ["qualify", "research", "development", "test"],
        "min_relevance": 0.4
    },
    {
        "query": "IRS Section 41 research credit",
        "expected_keywords": ["section", "41", "research", "credit"],
        "min_relevance": 0.4
    },
    {
        "query": "What costs are eligible for R&D credit",
        "expected_keywords": ["costs", "expenses", "eligible", "qualified"],
        "min_relevance": 0.4
    }
]

# Edge case queries - challenging queries to test robustness
EDGE_CASE_QUERIES = [
    {
        "query": "QRE",  # Abbreviation only
        "expected_keywords": ["qualified", "research", "expense"],
        "min_relevance": 0.3
    },
    {
        "query": "What is the definition of technological uncertainty in the context of R&D?",  # Very long query
        "expected_keywords": ["technological", "uncertainty", "research"],
        "min_relevance": 0.4
    },
    {
        "query": "four part test",  # Informal phrasing
        "expected_keywords": ["four", "test", "qualified"],
        "min_relevance": 0.4
    }
]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def indexed_knowledge_base():
    """
    Create and index a knowledge base for performance testing.
    Uses module scope to avoid re-indexing for each test.
    """
    # Use the real knowledge base if available
    kb_path = Path("knowledge_base")
    
    if not kb_path.exists():
        pytest.skip("Knowledge base not available for performance testing")
    
    # Check if already indexed
    indexed_path = kb_path / "indexed"
    metadata_path = kb_path / "metadata.json"
    
    if not metadata_path.exists():
        pytest.skip("Knowledge base metadata not available")
    
    # Index if needed
    import json
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Check if any documents need indexing
    needs_indexing = any(
        not doc.get('indexed', False)
        for doc in metadata.get('documents', [])
    )
    
    if needs_indexing:
        print("\nIndexing knowledge base for performance tests...")
        index_documents(
            knowledge_base_path=str(kb_path),
            chunk_size=512,
            overlap=50,
            force_reindex=False
        )
    
    yield str(indexed_path)
    
    # Cleanup
    gc.collect()


@pytest.fixture
def rd_tool(indexed_knowledge_base):
    """Create RD_Knowledge_Tool instance for testing"""
    tool = RD_Knowledge_Tool(knowledge_base_path=indexed_knowledge_base)
    yield tool
    try:
        del tool
    except:
        pass
    gc.collect()


# ============================================================================
# Query Latency Benchmarks
# ============================================================================

class TestQueryLatency:
    """Test query latency performance (target < 5 seconds)"""
    
    def test_single_query_latency(self, rd_tool):
        """Test that a single query completes within 5 seconds"""
        query = "What is the four-part test for qualified research?"
        
        start_time = time.time()
        context = rd_tool.query(query, top_k=3)
        end_time = time.time()
        
        latency = end_time - start_time
        
        assert isinstance(context, RAGContext)
        assert latency < 5.0, f"Query took {latency:.2f} seconds (target: < 5 seconds)"
        
        print(f"\n  Single query latency: {latency:.3f} seconds")
    
    def test_multiple_queries_latency(self, rd_tool):
        """Test latency for multiple sequential queries"""
        queries = [q["query"] for q in SPECIFIC_QUERIES[:3]]
        latencies = []
        
        for query in queries:
            start_time = time.time()
            context = rd_tool.query(query, top_k=3)
            end_time = time.time()
            
            latency = end_time - start_time
            latencies.append(latency)
            
            assert isinstance(context, RAGContext)
            assert latency < 5.0, f"Query '{query[:50]}...' took {latency:.2f} seconds"
        
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        print(f"\n  Multiple queries latency:")
        print(f"    Average: {avg_latency:.3f} seconds")
        print(f"    Min: {min_latency:.3f} seconds")
        print(f"    Max: {max_latency:.3f} seconds")
        
        assert avg_latency < 5.0, f"Average latency {avg_latency:.2f}s exceeds target"
    
    def test_query_with_optimizations_latency(self, rd_tool):
        """Test latency with all query optimizations enabled"""
        query = "What are QRE?"
        
        start_time = time.time()
        context = rd_tool.query(
            query,
            top_k=3,
            enable_query_expansion=True,
            enable_query_rewriting=True,
            enable_reranking=True
        )
        end_time = time.time()
        
        latency = end_time - start_time
        
        assert isinstance(context, RAGContext)
        assert latency < 5.0, f"Optimized query took {latency:.2f} seconds"
        
        print(f"\n  Query with optimizations latency: {latency:.3f} seconds")
    
    def test_query_without_optimizations_latency(self, rd_tool):
        """Test latency without query optimizations (baseline)"""
        query = "What are qualified research expenses?"
        
        start_time = time.time()
        context = rd_tool.query(
            query,
            top_k=3,
            enable_query_expansion=False,
            enable_query_rewriting=False,
            enable_reranking=False
        )
        end_time = time.time()
        
        latency = end_time - start_time
        
        assert isinstance(context, RAGContext)
        assert latency < 5.0, f"Basic query took {latency:.2f} seconds"
        
        print(f"\n  Query without optimizations latency: {latency:.3f} seconds")
    
    def test_large_top_k_latency(self, rd_tool):
        """Test latency when retrieving many chunks"""
        query = "R&D tax credit"
        
        start_time = time.time()
        context = rd_tool.query(query, top_k=10)
        end_time = time.time()
        
        latency = end_time - start_time
        
        assert isinstance(context, RAGContext)
        assert latency < 5.0, f"Large top_k query took {latency:.2f} seconds"
        
        print(f"\n  Large top_k (10) query latency: {latency:.3f} seconds")


# ============================================================================
# Retrieval Accuracy Benchmarks
# ============================================================================

class TestRetrievalAccuracy:
    """Test retrieval accuracy with known test questions"""
    
    def _check_keywords_in_chunks(
        self,
        chunks: List[Dict[str, Any]],
        expected_keywords: List[str]
    ) -> float:
        """
        Check how many expected keywords appear in retrieved chunks.
        
        Returns:
            float: Percentage of keywords found (0.0 to 1.0)
        """
        if not chunks or not expected_keywords:
            return 0.0
        
        # Combine all chunk text
        combined_text = " ".join(chunk['text'].lower() for chunk in chunks)
        
        # Count how many keywords are found
        found_keywords = sum(
            1 for keyword in expected_keywords
            if keyword.lower() in combined_text
        )
        
        return found_keywords / len(expected_keywords)
    
    def test_specific_queries_accuracy(self, rd_tool):
        """Test retrieval accuracy for specific queries"""
        results = []
        
        for test_case in SPECIFIC_QUERIES:
            query = test_case["query"]
            expected_keywords = test_case["expected_keywords"]
            min_relevance = test_case["min_relevance"]
            
            context = rd_tool.query(query, top_k=3)
            
            # Check keyword coverage
            keyword_coverage = self._check_keywords_in_chunks(
                context.chunks,
                expected_keywords
            )
            
            # Check relevance scores
            avg_relevance = context.average_relevance if context.chunk_count > 0 else 0.0
            
            results.append({
                "query": query,
                "keyword_coverage": keyword_coverage,
                "avg_relevance": avg_relevance,
                "chunk_count": context.chunk_count,
                "passed": keyword_coverage >= 0.5 and avg_relevance >= min_relevance
            })
        
        # Calculate overall accuracy
        passed_count = sum(1 for r in results if r["passed"])
        accuracy = passed_count / len(results)
        
        print(f"\n  Specific queries accuracy: {accuracy:.1%} ({passed_count}/{len(results)})")
        for result in results:
            status = "✓" if result["passed"] else "✗"
            print(f"    {status} {result['query'][:50]}... "
                  f"(keywords: {result['keyword_coverage']:.1%}, "
                  f"relevance: {result['avg_relevance']:.2f})")
        
        # Target: > 80% accuracy
        assert accuracy >= 0.8, f"Accuracy {accuracy:.1%} below target (80%)"
    
    def test_general_queries_accuracy(self, rd_tool):
        """Test retrieval accuracy for general queries"""
        results = []
        
        for test_case in GENERAL_QUERIES:
            query = test_case["query"]
            expected_keywords = test_case["expected_keywords"]
            min_relevance = test_case["min_relevance"]
            
            context = rd_tool.query(query, top_k=5)  # More chunks for general queries
            
            # Check keyword coverage
            keyword_coverage = self._check_keywords_in_chunks(
                context.chunks,
                expected_keywords
            )
            
            # Check relevance scores
            avg_relevance = context.average_relevance if context.chunk_count > 0 else 0.0
            
            results.append({
                "query": query,
                "keyword_coverage": keyword_coverage,
                "avg_relevance": avg_relevance,
                "chunk_count": context.chunk_count,
                "passed": keyword_coverage >= 0.5 and avg_relevance >= min_relevance
            })
        
        # Calculate overall accuracy
        passed_count = sum(1 for r in results if r["passed"])
        accuracy = passed_count / len(results)
        
        print(f"\n  General queries accuracy: {accuracy:.1%} ({passed_count}/{len(results)})")
        for result in results:
            status = "✓" if result["passed"] else "✗"
            print(f"    {status} {result['query'][:50]}... "
                  f"(keywords: {result['keyword_coverage']:.1%}, "
                  f"relevance: {result['avg_relevance']:.2f})")
        
        # Target: > 70% accuracy for general queries (more lenient)
        assert accuracy >= 0.7, f"Accuracy {accuracy:.1%} below target (70%)"
    
    def test_edge_case_queries_robustness(self, rd_tool):
        """Test robustness with edge case queries"""
        results = []
        
        for test_case in EDGE_CASE_QUERIES:
            query = test_case["query"]
            expected_keywords = test_case["expected_keywords"]
            min_relevance = test_case["min_relevance"]
            
            try:
                context = rd_tool.query(query, top_k=3)
                
                # Check keyword coverage
                keyword_coverage = self._check_keywords_in_chunks(
                    context.chunks,
                    expected_keywords
                )
                
                # Check relevance scores
                avg_relevance = context.average_relevance if context.chunk_count > 0 else 0.0
                
                results.append({
                    "query": query,
                    "keyword_coverage": keyword_coverage,
                    "avg_relevance": avg_relevance,
                    "chunk_count": context.chunk_count,
                    "passed": keyword_coverage >= 0.3 and avg_relevance >= min_relevance,
                    "error": None
                })
            except Exception as e:
                results.append({
                    "query": query,
                    "keyword_coverage": 0.0,
                    "avg_relevance": 0.0,
                    "chunk_count": 0,
                    "passed": False,
                    "error": str(e)
                })
        
        # Calculate robustness (no errors)
        no_errors = sum(1 for r in results if r["error"] is None)
        robustness = no_errors / len(results)
        
        print(f"\n  Edge case queries robustness: {robustness:.1%} ({no_errors}/{len(results)})")
        for result in results:
            if result["error"]:
                print(f"    ✗ {result['query'][:50]}... ERROR: {result['error']}")
            else:
                status = "✓" if result["passed"] else "~"
                print(f"    {status} {result['query'][:50]}... "
                      f"(keywords: {result['keyword_coverage']:.1%}, "
                      f"relevance: {result['avg_relevance']:.2f})")
        
        # All queries should execute without errors
        assert robustness == 1.0, "Some edge case queries failed with errors"
    
    def test_relevance_score_consistency(self, rd_tool):
        """Test that relevance scores are consistent and meaningful"""
        query = "What is the four-part test?"
        
        # Run same query multiple times
        contexts = [rd_tool.query(query, top_k=3) for _ in range(3)]
        
        # Check that we get results
        assert all(c.chunk_count > 0 for c in contexts), "Should retrieve chunks"
        
        # Check relevance scores are in valid range
        for context in contexts:
            for chunk in context.chunks:
                assert 0 <= chunk['relevance_score'] <= 1, "Relevance score out of range"
        
        # Check consistency (top result should be similar across runs)
        top_sources = [c.chunks[0]['source'] for c in contexts if c.chunk_count > 0]
        if len(top_sources) > 1:
            # Most common source should appear in majority of runs
            from collections import Counter
            most_common_source, count = Counter(top_sources).most_common(1)[0]
            consistency = count / len(top_sources)
            
            print(f"\n  Relevance score consistency: {consistency:.1%}")
            print(f"    Top source: {most_common_source}")
            
            # Should be reasonably consistent (>= 66%)
            assert consistency >= 0.66, f"Inconsistent results: {consistency:.1%}"


# ============================================================================
# Query Type Performance Comparison
# ============================================================================

class TestQueryTypePerformance:
    """Test performance across different query types"""
    
    def test_specific_vs_general_query_performance(self, rd_tool):
        """Compare performance between specific and general queries"""
        # Test specific queries
        specific_latencies = []
        specific_relevances = []
        
        for test_case in SPECIFIC_QUERIES[:3]:
            start_time = time.time()
            context = rd_tool.query(test_case["query"], top_k=3)
            latency = time.time() - start_time
            
            specific_latencies.append(latency)
            if context.chunk_count > 0:
                specific_relevances.append(context.average_relevance)
        
        # Test general queries
        general_latencies = []
        general_relevances = []
        
        for test_case in GENERAL_QUERIES[:3]:
            start_time = time.time()
            context = rd_tool.query(test_case["query"], top_k=3)
            latency = time.time() - start_time
            
            general_latencies.append(latency)
            if context.chunk_count > 0:
                general_relevances.append(context.average_relevance)
        
        # Calculate statistics
        specific_avg_latency = statistics.mean(specific_latencies)
        general_avg_latency = statistics.mean(general_latencies)
        
        specific_avg_relevance = statistics.mean(specific_relevances) if specific_relevances else 0
        general_avg_relevance = statistics.mean(general_relevances) if general_relevances else 0
        
        print(f"\n  Query type performance comparison:")
        print(f"    Specific queries:")
        print(f"      Avg latency: {specific_avg_latency:.3f}s")
        print(f"      Avg relevance: {specific_avg_relevance:.2f}")
        print(f"    General queries:")
        print(f"      Avg latency: {general_avg_latency:.3f}s")
        print(f"      Avg relevance: {general_avg_relevance:.2f}")
        
        # Both should meet latency target
        assert specific_avg_latency < 5.0, "Specific queries too slow"
        assert general_avg_latency < 5.0, "General queries too slow"
        
        # Specific queries should generally have higher relevance
        # (but this is not a hard requirement)
        if specific_avg_relevance > 0 and general_avg_relevance > 0:
            print(f"    Relevance difference: {specific_avg_relevance - general_avg_relevance:+.2f}")
    
    def test_short_vs_long_query_performance(self, rd_tool):
        """Compare performance between short and long queries"""
        # Short query
        short_query = "QRE"
        start_time = time.time()
        short_context = rd_tool.query(short_query, top_k=3)
        short_latency = time.time() - start_time
        
        # Long query
        long_query = "What is the definition of technological uncertainty in the context of research and development tax credit qualification under Section 41?"
        start_time = time.time()
        long_context = rd_tool.query(long_query, top_k=3)
        long_latency = time.time() - start_time
        
        print(f"\n  Query length performance comparison:")
        print(f"    Short query ({len(short_query)} chars): {short_latency:.3f}s")
        print(f"    Long query ({len(long_query)} chars): {long_latency:.3f}s")
        print(f"    Latency difference: {long_latency - short_latency:+.3f}s")
        
        # Both should meet latency target
        assert short_latency < 5.0, "Short query too slow"
        assert long_latency < 5.0, "Long query too slow"
        
        # Latency difference should be reasonable (< 2 seconds)
        assert abs(long_latency - short_latency) < 2.0, "Large latency difference"
    
    def test_optimized_vs_basic_query_performance(self, rd_tool):
        """Compare performance with and without optimizations"""
        query = "What are qualified research expenses?"
        
        # Basic query (no optimizations)
        start_time = time.time()
        basic_context = rd_tool.query(
            query,
            top_k=3,
            enable_query_expansion=False,
            enable_query_rewriting=False,
            enable_reranking=False
        )
        basic_latency = time.time() - start_time
        
        # Optimized query (all optimizations)
        start_time = time.time()
        optimized_context = rd_tool.query(
            query,
            top_k=3,
            enable_query_expansion=True,
            enable_query_rewriting=True,
            enable_reranking=True
        )
        optimized_latency = time.time() - start_time
        
        print(f"\n  Optimization performance comparison:")
        print(f"    Basic query: {basic_latency:.3f}s")
        print(f"    Optimized query: {optimized_latency:.3f}s")
        print(f"    Overhead: {optimized_latency - basic_latency:+.3f}s")
        
        # Both should meet latency target
        assert basic_latency < 5.0, "Basic query too slow"
        assert optimized_latency < 5.0, "Optimized query too slow"
        
        # Optimization overhead should be reasonable (< 3 seconds)
        overhead = optimized_latency - basic_latency
        assert overhead < 3.0, f"Optimization overhead too high: {overhead:.2f}s"


# ============================================================================
# Performance Metrics Documentation
# ============================================================================

class TestPerformanceMetrics:
    """Document overall performance metrics"""
    
    def test_comprehensive_performance_report(self, rd_tool):
        """Generate comprehensive performance report"""
        print("\n" + "=" * 70)
        print("RAG SYSTEM PERFORMANCE REPORT")
        print("=" * 70)
        
        # Test various query types
        test_queries = [
            ("Specific", "What is the four-part test?"),
            ("General", "R&D tax credit requirements"),
            ("Abbreviation", "QRE"),
            ("Long", "What is the definition of technological uncertainty in R&D?")
        ]
        
        results = []
        
        for query_type, query in test_queries:
            start_time = time.time()
            context = rd_tool.query(query, top_k=3)
            latency = time.time() - start_time
            
            results.append({
                "type": query_type,
                "query": query,
                "latency": latency,
                "chunks": context.chunk_count,
                "avg_relevance": context.average_relevance if context.chunk_count > 0 else 0.0
            })
        
        # Print results
        print("\nQuery Performance:")
        print(f"{'Type':<15} {'Latency':<12} {'Chunks':<8} {'Avg Relevance':<15}")
        print("-" * 70)
        
        for result in results:
            print(f"{result['type']:<15} "
                  f"{result['latency']:.3f}s{'':<6} "
                  f"{result['chunks']:<8} "
                  f"{result['avg_relevance']:.2f}")
        
        # Calculate summary statistics
        latencies = [r["latency"] for r in results]
        relevances = [r["avg_relevance"] for r in results if r["avg_relevance"] > 0]
        
        print("\nSummary Statistics:")
        print(f"  Average latency: {statistics.mean(latencies):.3f}s")
        print(f"  Max latency: {max(latencies):.3f}s")
        print(f"  Min latency: {min(latencies):.3f}s")
        if relevances:
            print(f"  Average relevance: {statistics.mean(relevances):.2f}")
        
        # Performance targets
        print("\nPerformance Targets:")
        print(f"  ✓ Query latency < 5 seconds: {max(latencies) < 5.0}")
        print(f"  ✓ Average relevance > 0.5: {statistics.mean(relevances) > 0.5 if relevances else False}")
        
        # Knowledge base info
        kb_info = rd_tool.get_knowledge_base_info()
        print("\nKnowledge Base Info:")
        print(f"  Total chunks: {kb_info.get('total_chunks', 'unknown')}")
        print(f"  Embedding model: {kb_info.get('embedding_model', 'unknown')}")
        
        print("=" * 70)
        
        # All queries should meet latency target
        assert all(r["latency"] < 5.0 for r in results), "Some queries exceeded latency target"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
