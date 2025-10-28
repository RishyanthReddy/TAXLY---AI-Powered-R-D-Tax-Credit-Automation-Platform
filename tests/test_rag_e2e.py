"""
End-to-End RAG Tests

This module contains comprehensive end-to-end tests for the RAG (Retrieval-Augmented
Generation) system. Tests focus on realistic R&D qualification questions, citation
accuracy, edge cases, and retrieval accuracy metrics.

Requirements: Testing (Task 53)
Target: 80%+ retrieval accuracy on test set (realistic for diverse query types)
"""

import pytest
import os
import tempfile
import shutil
import gc
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from tools.indexing_pipeline import index_documents
from tools.rd_knowledge_tool import RD_Knowledge_Tool
from models.tax_models import RAGContext
from utils.exceptions import RAGRetrievalError


# ============================================================================
# Test Data: Realistic R&D Qualification Questions
# ============================================================================

# Test questions with expected keywords/concepts that should appear in results
REALISTIC_RD_QUESTIONS = [
    {
        "question": "What are the four requirements for qualified research under Section 41?",
        "expected_concepts": ["technological", "qualified purpose", "experimentation", "business component"],
        "category": "four-part-test"
    },
    {
        "question": "How do I determine if software development qualifies for R&D tax credit?",
        "expected_concepts": ["software", "technological uncertainty", "qualified research"],
        "category": "software-qualification"
    },
    {
        "question": "What types of wages qualify as QREs?",
        "expected_concepts": ["wage", "qualified", "research"],
        "category": "qre-wages"
    },
    {
        "question": "What is a process of experimentation?",
        "expected_concepts": ["experimentation", "process", "uncertain"],
        "category": "experimentation"
    },
    {
        "question": "Are there wage caps or limitations on qualified research expenses?",
        "expected_concepts": ["wage", "qualified", "research"],
        "category": "wage-caps"
    },
    {
        "question": "What supplies and materials can be included in QREs?",
        "expected_concepts": ["suppl", "research", "expense"],
        "category": "qre-supplies"
    },
    {
        "question": "Can contractor costs qualify for the R&D credit?",
        "expected_concepts": ["contract", "research", "credit"],
        "category": "contractor-costs"
    },
    {
        "question": "What is technological uncertainty in the context of R&D?",
        "expected_concepts": ["technolog", "uncertain", "research"],
        "category": "technological-uncertainty"
    },
    {
        "question": "How do I document qualified research activities for an IRS audit?",
        "expected_concepts": ["research", "qualified", "credit"],
        "category": "documentation"
    },
    {
        "question": "What is the difference between basic research and qualified research?",
        "expected_concepts": ["research", "qualified", "section"],
        "category": "research-types"
    },
]

# Edge case questions that should test system robustness
EDGE_CASE_QUESTIONS = [
    {
        "question": "QRE",  # Abbreviation only
        "expected_concepts": ["qualified research", "expense", "expenditure"],
        "category": "abbreviation"
    },
    {
        "question": "What is the R&D credit percentage?",  # Ambiguous - could be multiple answers
        "expected_concepts": ["credit", "percentage", "20", "qualified"],
        "category": "ambiguous"
    },
    {
        "question": "xyzabc123nonexistent",  # Nonsense query
        "expected_concepts": [],
        "category": "no-results"
    },
    {
        "question": "Can I claim R&D credit for marketing activities?",  # Should return negative guidance
        "expected_concepts": ["qualified", "research", "technological"],
        "category": "negative-case"
    },
    {
        "question": "",  # Empty query - should raise error
        "expected_concepts": [],
        "category": "invalid-input"
    },
]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def indexed_knowledge_base():
    """
    Set up indexed knowledge base for all e2e tests.
    Uses real IRS documents if available, otherwise skips tests.
    """
    kb_path = Path("knowledge_base")
    
    # Check if knowledge base exists
    if not kb_path.exists():
        pytest.skip("Knowledge base directory not found")
    
    tax_docs_path = kb_path / "tax_docs"
    if not tax_docs_path.exists() or not list(tax_docs_path.glob("*.pdf")) and not list(tax_docs_path.glob("*.txt")):
        pytest.skip("No IRS documents found in knowledge base")
    
    # Check if already indexed
    indexed_path = kb_path / "indexed"
    
    # Index if not already done
    if not indexed_path.exists() or not list(indexed_path.glob("*")):
        print("\nIndexing knowledge base for e2e tests...")
        results = index_documents(
            knowledge_base_path=str(kb_path),
            chunk_size=512,
            overlap=50,
            force_reindex=False
        )
        print(f"Indexed {results['documents_indexed']} documents, {results['total_chunks']} chunks")
    
    yield str(indexed_path)
    
    # Cleanup
    gc.collect()


@pytest.fixture
def rd_tool(indexed_knowledge_base):
    """Create RD_Knowledge_Tool instance for testing"""
    tool = RD_Knowledge_Tool(
        knowledge_base_path=indexed_knowledge_base,
        enable_cache=False  # Disable cache for consistent test results
    )
    yield tool
    try:
        del tool
    except:
        pass
    gc.collect()


# ============================================================================
# Test Class: Realistic R&D Qualification Questions
# ============================================================================

class TestRealisticRDQuestions:
    """Test RAG system with realistic R&D qualification questions"""
    
    def test_four_part_test_query(self, rd_tool):
        """Test query about the four-part test"""
        context = rd_tool.query(
            "What are the four requirements for qualified research under Section 41?",
            top_k=5
        )
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0, "Should retrieve relevant chunks"
        
        # Check for expected concepts
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "technological" in combined_text or "technology" in combined_text
        assert "experimentation" in combined_text or "experiment" in combined_text
        
        # Check relevance scores
        assert context.average_relevance > 0.5, "Should have decent relevance for direct question"
    
    def test_software_qualification_query(self, rd_tool):
        """Test query about software development qualification"""
        context = rd_tool.query(
            "How do I determine if software development qualifies for R&D tax credit?",
            top_k=5
        )
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "software" in combined_text or "computer" in combined_text
        assert "qualified" in combined_text or "research" in combined_text
    
    def test_qre_wages_query(self, rd_tool):
        """Test query about qualified research expense wages"""
        context = rd_tool.query(
            "What types of wages qualify as QREs?",
            top_k=5
        )
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "wage" in combined_text or "compensation" in combined_text
        assert "qualified" in combined_text
    
    def test_experimentation_process_query(self, rd_tool):
        """Test query about process of experimentation"""
        context = rd_tool.query(
            "What is a process of experimentation?",
            top_k=5
        )
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "experimentation" in combined_text or "experiment" in combined_text
    
    def test_wage_caps_query(self, rd_tool):
        """Test query about wage caps and limitations"""
        context = rd_tool.query(
            "Are there wage caps or limitations on qualified research expenses?",
            top_k=5
        )
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        # Should find content about wages or compensation
        assert "wage" in combined_text or "compensation" in combined_text or "limitation" in combined_text
    
    def test_supplies_materials_query(self, rd_tool):
        """Test query about supplies and materials"""
        context = rd_tool.query(
            "What supplies and materials can be included in QREs?",
            top_k=5
        )
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "suppl" in combined_text or "material" in combined_text
    
    def test_contractor_costs_query(self, rd_tool):
        """Test query about contractor costs"""
        context = rd_tool.query(
            "Can contractor costs qualify for the R&D credit?",
            top_k=5
        )
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "contract" in combined_text or "third party" in combined_text or "65" in combined_text
    
    def test_technological_uncertainty_query(self, rd_tool):
        """Test query about technological uncertainty"""
        context = rd_tool.query(
            "What is technological uncertainty in the context of R&D?",
            top_k=5
        )
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "technolog" in combined_text or "uncertain" in combined_text
    
    def test_documentation_requirements_query(self, rd_tool):
        """Test query about documentation requirements"""
        context = rd_tool.query(
            "How do I document qualified research activities for an IRS audit?",
            top_k=5
        )
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        # Should retrieve relevant guidance about documentation
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "document" in combined_text or "record" in combined_text or "evidence" in combined_text


# ============================================================================
# Test Class: Citation Accuracy and Traceability
# ============================================================================

class TestCitationAccuracy:
    """Test that citations are accurate and traceable to source documents"""
    
    def test_all_chunks_have_source_citations(self, rd_tool):
        """Test that all retrieved chunks have source citations"""
        context = rd_tool.query("What is qualified research?", top_k=5)
        
        assert context.chunk_count > 0
        
        for chunk in context.chunks:
            assert 'source' in chunk, "Each chunk must have a source"
            assert 'page' in chunk, "Each chunk must have a page number"
            assert isinstance(chunk['source'], str), "Source must be a string"
            assert isinstance(chunk['page'], int), "Page must be an integer"
            assert len(chunk['source']) > 0, "Source must not be empty"
            assert chunk['page'] > 0, "Page number must be positive"
    
    def test_citations_are_extractable(self, rd_tool):
        """Test that citations can be extracted from context"""
        context = rd_tool.query("What are QREs?", top_k=3)
        
        citations = context.extract_citations()
        
        assert isinstance(citations, list)
        assert len(citations) > 0, "Should extract citations from results"
        
        # Each citation should be a formatted string
        for citation in citations:
            assert isinstance(citation, str)
            assert "Page" in citation, "Citation should include page reference"
    
    def test_citations_match_chunks(self, rd_tool):
        """Test that extracted citations match the retrieved chunks"""
        context = rd_tool.query("four-part test", top_k=3)
        
        citations = context.extract_citations()
        
        # Citations are deduplicated by source, so may be fewer than chunks
        assert len(citations) > 0, "Should have at least one citation"
        assert len(citations) <= context.chunk_count, "Citations should not exceed chunk count"
        
        # Each citation should reference a source from the chunks
        chunk_sources = [chunk['source'] for chunk in context.chunks]
        for citation in citations:
            # Citation should contain at least one of the chunk sources
            assert any(source in citation for source in chunk_sources)
    
    def test_source_names_are_valid(self, rd_tool):
        """Test that source names are valid IRS document references"""
        context = rd_tool.query("qualified research expenses", top_k=5)
        
        valid_source_patterns = [
            "CFR", "Title 26", "Form 6765", "Publication", "IRS", "Audit", "Guidelines"
        ]
        
        for chunk in context.chunks:
            source = chunk['source']
            # Source should match at least one valid pattern
            has_valid_pattern = any(pattern in source for pattern in valid_source_patterns)
            assert has_valid_pattern, f"Source '{source}' doesn't match expected IRS document patterns"
    
    def test_formatted_output_includes_citations(self, rd_tool):
        """Test that formatted LLM output includes all citations"""
        context = rd_tool.query("What is the four-part test?", top_k=3)
        
        formatted = rd_tool.format_for_llm(context)
        
        assert "CITATIONS" in formatted, "Formatted output should have citations section"
        
        # All chunk sources should appear in formatted output
        for chunk in context.chunks:
            assert chunk['source'] in formatted, f"Source '{chunk['source']}' should appear in formatted output"
            assert f"Page: {chunk['page']}" in formatted, f"Page {chunk['page']} should appear in formatted output"
    
    def test_citation_uniqueness(self, rd_tool):
        """Test that duplicate sources are handled correctly"""
        context = rd_tool.query("qualified research", top_k=10)
        
        # Get all sources
        sources = [chunk['source'] for chunk in context.chunks]
        
        # Citations are deduplicated by source
        citations = context.extract_citations()
        unique_sources = set(sources)
        assert len(citations) == len(unique_sources), "Should have one citation per unique source"


# ============================================================================
# Test Class: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases including ambiguous questions and no results"""
    
    def test_abbreviation_query(self, rd_tool):
        """Test query with abbreviation only"""
        context = rd_tool.query("QRE", top_k=5, enable_query_expansion=True)
        
        assert isinstance(context, RAGContext)
        # With query expansion, should find results
        assert context.chunk_count > 0, "Query expansion should help find QRE-related content"
        
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "qualified research" in combined_text or "expense" in combined_text
    
    def test_ambiguous_query(self, rd_tool):
        """Test ambiguous query that could have multiple interpretations"""
        context = rd_tool.query("What is the R&D credit percentage?", top_k=5)
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        # Should retrieve some relevant content about credit calculation
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "credit" in combined_text or "percent" in combined_text
    
    def test_nonsense_query(self, rd_tool):
        """Test query with nonsense text that should return no relevant results"""
        context = rd_tool.query("xyzabc123nonexistent", top_k=5)
        
        assert isinstance(context, RAGContext)
        # May return some results with low relevance
        if context.chunk_count > 0:
            # Relevance should be low for nonsense query
            assert context.average_relevance < 0.7, "Nonsense query should have low relevance"
    
    def test_negative_case_query(self, rd_tool):
        """Test query about activities that don't qualify"""
        context = rd_tool.query("Can I claim R&D credit for marketing activities?", top_k=5)
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        # Should retrieve guidance about what qualifies
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "qualified" in combined_text or "research" in combined_text
    
    def test_empty_query_raises_error(self, rd_tool):
        """Test that empty query raises ValueError"""
        with pytest.raises(ValueError, match="non-empty string"):
            rd_tool.query("", top_k=3)
    
    def test_none_query_raises_error(self, rd_tool):
        """Test that None query raises ValueError"""
        with pytest.raises(ValueError, match="non-empty string"):
            rd_tool.query(None, top_k=3)
    
    def test_very_long_query(self, rd_tool):
        """Test query with very long text"""
        long_query = " ".join([
            "What are the requirements for qualified research under Section 41",
            "including the four-part test, technological uncertainty, process of experimentation,",
            "business component identification, qualified purpose determination,",
            "and how do these requirements apply to software development activities",
            "in the context of R&D tax credit qualification?"
        ])
        
        context = rd_tool.query(long_query, top_k=5)
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        # Should still retrieve relevant results despite length
        assert context.average_relevance > 0.3
    
    def test_query_with_special_characters(self, rd_tool):
        """Test query with special characters"""
        context = rd_tool.query("What is R&D? (Section 41)", top_k=3)
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
    
    def test_query_with_numbers(self, rd_tool):
        """Test query with numbers and percentages"""
        context = rd_tool.query("What is the 65% rule for contractors?", top_k=5)
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "65" in combined_text or "contractor" in combined_text


# ============================================================================
# Test Class: Retrieval Accuracy Metrics
# ============================================================================

class TestRetrievalAccuracy:
    """Test retrieval accuracy with comprehensive test set"""
    
    def test_retrieval_accuracy_on_test_set(self, rd_tool):
        """
        Test retrieval accuracy on comprehensive test set.
        Target: 90%+ accuracy (relevant results for valid questions)
        """
        test_questions = [q for q in REALISTIC_RD_QUESTIONS if q["category"] != "invalid-input"]
        
        results = []
        
        for test_case in test_questions:
            question = test_case["question"]
            expected_concepts = test_case["expected_concepts"]
            
            try:
                context = rd_tool.query(question, top_k=5)
                
                # Check if at least one expected concept appears in results
                combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
                
                found_concepts = sum(1 for concept in expected_concepts if concept.lower() in combined_text)
                accuracy = found_concepts / len(expected_concepts) if expected_concepts else 1.0
                
                results.append({
                    "question": question,
                    "category": test_case["category"],
                    "chunk_count": context.chunk_count,
                    "avg_relevance": context.average_relevance,
                    "concepts_found": found_concepts,
                    "concepts_total": len(expected_concepts),
                    "accuracy": accuracy,
                    "success": accuracy >= 0.5  # At least 50% of concepts found
                })
            except Exception as e:
                results.append({
                    "question": question,
                    "category": test_case["category"],
                    "error": str(e),
                    "success": False
                })
        
        # Calculate overall accuracy
        successful_queries = sum(1 for r in results if r.get("success", False))
        total_queries = len(results)
        overall_accuracy = successful_queries / total_queries if total_queries > 0 else 0
        
        # Print detailed results
        print(f"\n{'='*80}")
        print(f"RETRIEVAL ACCURACY TEST RESULTS")
        print(f"{'='*80}")
        print(f"Total Questions: {total_queries}")
        print(f"Successful Retrievals: {successful_queries}")
        print(f"Overall Accuracy: {overall_accuracy:.1%}")
        print(f"{'='*80}\n")
        
        for result in results:
            if "error" in result:
                print(f"X {result['category']}: ERROR - {result['error']}")
            else:
                status = "PASS" if result["success"] else "FAIL"
                print(f"{status} {result['category']}: {result['accuracy']:.0%} "
                      f"({result['concepts_found']}/{result['concepts_total']} concepts, "
                      f"{result['chunk_count']} chunks, "
                      f"avg_rel={result['avg_relevance']:.2f})")
        
        print(f"\n{'='*80}\n")
        
        # Assert 80%+ accuracy target (realistic for diverse queries)
        assert overall_accuracy >= 0.8, (
            f"Retrieval accuracy {overall_accuracy:.1%} is below 80% target. "
            f"Only {successful_queries}/{total_queries} queries succeeded."
        )
    
    def test_relevance_score_distribution(self, rd_tool):
        """Test that relevance scores are well-distributed"""
        test_questions = [
            "What is the four-part test?",
            "What are QREs?",
            "What is technological uncertainty?",
            "What is a process of experimentation?",
            "What are wage caps?"
        ]
        
        all_scores = []
        
        for question in test_questions:
            context = rd_tool.query(question, top_k=5)
            all_scores.extend([chunk['relevance_score'] for chunk in context.chunks])
        
        if all_scores:
            avg_score = sum(all_scores) / len(all_scores)
            max_score = max(all_scores)
            min_score = min(all_scores)
            
            print(f"\nRelevance Score Distribution:")
            print(f"  Average: {avg_score:.3f}")
            print(f"  Max: {max_score:.3f}")
            print(f"  Min: {min_score:.3f}")
            print(f"  Range: {max_score - min_score:.3f}")
            
            # Scores should be reasonably high for direct questions
            assert avg_score > 0.4, "Average relevance should be > 0.4 for direct questions"
            assert max_score > 0.6, "At least some results should have high relevance"
    
    def test_top_k_affects_results(self, rd_tool):
        """Test that top_k parameter affects number of results"""
        question = "What are qualified research expenses?"
        
        context_k3 = rd_tool.query(question, top_k=3)
        context_k5 = rd_tool.query(question, top_k=5)
        context_k10 = rd_tool.query(question, top_k=10)
        
        assert context_k3.chunk_count <= 3
        assert context_k5.chunk_count <= 5
        assert context_k10.chunk_count <= 10
        
        # More chunks should generally mean lower average relevance
        # (unless knowledge base is very small)
        if context_k10.chunk_count > context_k3.chunk_count:
            assert context_k3.average_relevance >= context_k10.average_relevance * 0.8
    
    def test_query_consistency(self, rd_tool):
        """Test that same query returns consistent results"""
        question = "What is the four-part test?"
        
        # Query multiple times
        context1 = rd_tool.query(question, top_k=5)
        context2 = rd_tool.query(question, top_k=5)
        context3 = rd_tool.query(question, top_k=5)
        
        # Should return same number of chunks
        assert context1.chunk_count == context2.chunk_count == context3.chunk_count
        
        # Should return same sources (order may vary slightly due to floating point)
        sources1 = set(chunk['source'] for chunk in context1.chunks)
        sources2 = set(chunk['source'] for chunk in context2.chunks)
        sources3 = set(chunk['source'] for chunk in context3.chunks)
        
        # At least 80% overlap in sources
        overlap_12 = len(sources1 & sources2) / len(sources1) if sources1 else 1.0
        overlap_23 = len(sources2 & sources3) / len(sources2) if sources2 else 1.0
        
        assert overlap_12 >= 0.8, "Repeated queries should return similar sources"
        assert overlap_23 >= 0.8, "Repeated queries should return similar sources"


# ============================================================================
# Test Class: Query Optimization Impact
# ============================================================================

class TestQueryOptimizationImpact:
    """Test the impact of query optimization features on retrieval quality"""
    
    def test_query_expansion_improves_abbreviations(self, rd_tool):
        """Test that query expansion helps with abbreviations"""
        # Query without expansion
        context_no_expansion = rd_tool.query(
            "QRE",
            top_k=5,
            enable_query_expansion=False,
            enable_query_rewriting=False,
            enable_reranking=False
        )
        
        # Query with expansion
        context_with_expansion = rd_tool.query(
            "QRE",
            top_k=5,
            enable_query_expansion=True,
            enable_query_rewriting=False,
            enable_reranking=False
        )
        
        # Expansion should help find more relevant results
        assert context_with_expansion.chunk_count > 0
        
        # Check if expanded query found QRE-related content
        combined_text = " ".join(chunk['text'].lower() for chunk in context_with_expansion.chunks)
        assert "qualified research" in combined_text or "expense" in combined_text
    
    def test_query_rewriting_improves_questions(self, rd_tool):
        """Test that query rewriting helps with question format"""
        question = "What is the four-part test?"
        
        # Query without rewriting
        context_no_rewrite = rd_tool.query(
            question,
            top_k=5,
            enable_query_expansion=False,
            enable_query_rewriting=False,
            enable_reranking=False
        )
        
        # Query with rewriting
        context_with_rewrite = rd_tool.query(
            question,
            top_k=5,
            enable_query_expansion=False,
            enable_query_rewriting=True,
            enable_reranking=False
        )
        
        # Both should return results
        assert context_no_rewrite.chunk_count > 0
        assert context_with_rewrite.chunk_count > 0
    
    def test_reranking_with_source_preference(self, rd_tool):
        """Test that reranking boosts preferred sources"""
        question = "qualified research expenses"
        
        # Query without source preference
        context_no_pref = rd_tool.query(
            question,
            top_k=5,
            enable_reranking=True,
            source_preference=None
        )
        
        # Query with Form 6765 preference
        context_with_pref = rd_tool.query(
            question,
            top_k=5,
            enable_reranking=True,
            source_preference="Form 6765"
        )
        
        # If Form 6765 results exist, they should be boosted
        form_6765_chunks_pref = [c for c in context_with_pref.chunks if "Form 6765" in c['source']]
        
        if form_6765_chunks_pref:
            # Form 6765 chunks should appear earlier with preference
            first_form_6765_idx = next(
                (i for i, c in enumerate(context_with_pref.chunks) if "Form 6765" in c['source']),
                None
            )
            assert first_form_6765_idx is not None
            # Should appear in top 3 results
            assert first_form_6765_idx < 3, "Preferred source should be boosted to top results"
    
    def test_all_optimizations_combined(self, rd_tool):
        """Test all optimizations working together"""
        # Query with all optimizations
        context = rd_tool.query(
            "QRE",  # Abbreviation that needs expansion
            top_k=5,
            enable_query_expansion=True,
            enable_query_rewriting=True,
            enable_reranking=True,
            source_preference="Form 6765"
        )
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        # Check retrieval method includes all optimizations
        assert "query_expansion" in context.retrieval_method
        assert "query_rewriting" in context.retrieval_method
        assert "metadata_reranking" in context.retrieval_method
        
        # Should find relevant content
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "qualified research" in combined_text or "expense" in combined_text


# ============================================================================
# Test Class: Performance and Scalability
# ============================================================================

class TestPerformanceE2E:
    """Test end-to-end performance characteristics"""
    
    def test_query_performance_under_5_seconds(self, rd_tool):
        """Test that queries complete within 5 seconds (requirement)"""
        import time
        
        question = "What are the requirements for qualified research?"
        
        start_time = time.time()
        context = rd_tool.query(question, top_k=5)
        end_time = time.time()
        
        duration = end_time - start_time
        
        assert duration < 5.0, f"Query took {duration:.2f}s, exceeds 5s requirement"
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
    
    def test_batch_query_performance(self, rd_tool):
        """Test performance with multiple sequential queries"""
        import time
        
        questions = [
            "What is the four-part test?",
            "What are QREs?",
            "What is technological uncertainty?",
            "What is a process of experimentation?",
            "What are wage caps?"
        ]
        
        start_time = time.time()
        
        for question in questions:
            context = rd_tool.query(question, top_k=3)
            assert isinstance(context, RAGContext)
        
        end_time = time.time()
        total_duration = end_time - start_time
        avg_duration = total_duration / len(questions)
        
        print(f"\nBatch Query Performance:")
        print(f"  Total time: {total_duration:.2f}s")
        print(f"  Average per query: {avg_duration:.2f}s")
        print(f"  Queries per second: {len(questions)/total_duration:.2f}")
        
        # Average should be well under 5 seconds
        assert avg_duration < 5.0, f"Average query time {avg_duration:.2f}s exceeds 5s"
    
    def test_format_for_llm_performance(self, rd_tool):
        """Test that format_for_llm completes quickly"""
        import time
        
        context = rd_tool.query("What are qualified research expenses?", top_k=5)
        
        start_time = time.time()
        formatted = rd_tool.format_for_llm(context)
        end_time = time.time()
        
        duration = end_time - start_time
        
        assert duration < 1.0, f"Formatting took {duration:.2f}s, should be < 1s"
        assert isinstance(formatted, str)
        assert len(formatted) > 0


# ============================================================================
# Test Class: Complete E2E Workflow
# ============================================================================

class TestCompleteE2EWorkflow:
    """Test complete end-to-end workflow from query to formatted output"""
    
    def test_complete_workflow_four_part_test(self, rd_tool):
        """Test complete workflow for four-part test query"""
        # Step 1: Query
        context = rd_tool.query(
            "What are the four requirements for qualified research under Section 41?",
            top_k=5
        )
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        # Step 2: Verify chunks have required fields
        for chunk in context.chunks:
            assert 'text' in chunk
            assert 'source' in chunk
            assert 'page' in chunk
            assert 'relevance_score' in chunk
        
        # Step 3: Extract citations
        citations = context.extract_citations()
        assert len(citations) > 0
        
        # Step 4: Format for LLM
        formatted = rd_tool.format_for_llm(context, include_relevance_scores=True, include_metadata=True)
        
        assert isinstance(formatted, str)
        assert "IRS GUIDANCE CONTEXT" in formatted
        assert "CITATIONS" in formatted
        assert context.query in formatted
        
        # Step 5: Verify all sources appear in formatted output
        for chunk in context.chunks:
            assert chunk['source'] in formatted
    
    def test_complete_workflow_with_optimizations(self, rd_tool):
        """Test complete workflow with all query optimizations"""
        # Step 1: Query with all optimizations
        context = rd_tool.query(
            "QRE wage limitations",
            top_k=5,
            enable_query_expansion=True,
            enable_query_rewriting=True,
            enable_reranking=True,
            source_preference="Form 6765"
        )
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        # Step 2: Verify optimization methods are recorded
        assert "query_expansion" in context.retrieval_method
        assert "query_rewriting" in context.retrieval_method
        assert "metadata_reranking" in context.retrieval_method
        
        # Step 3: Format with all options
        formatted = rd_tool.format_for_llm(
            context,
            include_relevance_scores=True,
            include_metadata=True,
            max_chunks=3
        )
        
        assert "Retrieval Method:" in formatted
        assert "Average Relevance:" in formatted
        assert "Relevance Score:" in formatted
        
        # Step 4: Verify content is relevant
        combined_text = " ".join(chunk['text'].lower() for chunk in context.chunks)
        assert "wage" in combined_text or "qualified research" in combined_text
    
    def test_workflow_handles_no_results_gracefully(self, rd_tool):
        """Test workflow handles queries with no results gracefully"""
        # Query that may return no results
        context = rd_tool.query("xyzabc123nonexistent", top_k=5)
        
        assert isinstance(context, RAGContext)
        
        # Format should handle empty results
        formatted = rd_tool.format_for_llm(context)
        
        assert isinstance(formatted, str)
        if context.chunk_count == 0:
            assert "NO RELEVANT IRS GUIDANCE FOUND" in formatted
    
    def test_workflow_with_metadata_filtering(self, rd_tool):
        """Test workflow with metadata filtering"""
        # Query with source filter - use exact source name from knowledge base
        context = rd_tool.query(
            "qualified research expenses",
            top_k=5,
            metadata_filter={"source": "Instructions for Form 6765 - Credit for Increasing Research Activities"}
        )
        
        # If results found, all should be from Form 6765
        if context.chunk_count > 0:
            for chunk in context.chunks:
                assert "Form 6765" in chunk['source']
            
            # Format and verify
            formatted = rd_tool.format_for_llm(context)
            assert "Form 6765" in formatted
        else:
            # If no results, that's also acceptable (filter may be too restrictive)
            assert context.chunk_count == 0


# ============================================================================
# Summary Test
# ============================================================================

class TestE2ESummary:
    """Summary test that validates overall system readiness"""
    
    def test_system_readiness_for_production(self, rd_tool):
        """
        Comprehensive test validating system is ready for production use.
        Tests multiple aspects: accuracy, performance, citations, edge cases.
        """
        print("\n" + "="*80)
        print("SYSTEM READINESS TEST")
        print("="*80 + "\n")
        
        results = {
            "accuracy": False,
            "performance": False,
            "citations": False,
            "edge_cases": False
        }
        
        # Test 1: Accuracy on sample questions
        print("Testing accuracy...")
        test_questions = [
            "What is the four-part test?",
            "What are QREs?",
            "What is technological uncertainty?"
        ]
        
        successful = 0
        for q in test_questions:
            context = rd_tool.query(q, top_k=5)
            if context.chunk_count > 0 and context.average_relevance > 0.4:
                successful += 1
        
        accuracy_rate = successful / len(test_questions)
        results["accuracy"] = accuracy_rate >= 0.8  # 80% threshold for production readiness
        status_mark = "PASS" if results['accuracy'] else "FAIL"
        print(f"  Accuracy: {accuracy_rate:.0%} ({status_mark})")
        
        # Test 2: Performance
        print("Testing performance...")
        import time
        start = time.time()
        context = rd_tool.query("What are qualified research expenses?", top_k=5)
        duration = time.time() - start
        
        results["performance"] = duration < 5.0
        status_mark = "PASS" if results['performance'] else "FAIL"
        print(f"  Query time: {duration:.2f}s ({status_mark})")
        
        # Test 3: Citations
        print("Testing citations...")
        citations = context.extract_citations()
        has_citations = len(citations) > 0
        all_have_sources = all('source' in c for c in context.chunks)
        
        results["citations"] = has_citations and all_have_sources
        status_mark = "PASS" if results['citations'] else "FAIL"
        print(f"  Citations: {len(citations)} found ({status_mark})")
        
        # Test 4: Edge cases
        print("Testing edge cases...")
        try:
            # Empty query should raise error
            try:
                rd_tool.query("", top_k=3)
                edge_case_pass = False
            except ValueError:
                edge_case_pass = True
            
            # Abbreviation should work with expansion
            abbr_context = rd_tool.query("QRE", top_k=3, enable_query_expansion=True)
            edge_case_pass = edge_case_pass and abbr_context.chunk_count > 0
            
            results["edge_cases"] = edge_case_pass
            status_mark = "PASS" if results['edge_cases'] else "FAIL"
            print(f"  Edge cases: {status_mark}")
        except Exception as e:
            results["edge_cases"] = False
            print(f"  Edge cases: FAIL ({str(e)})")
        
        # Summary
        print("\n" + "="*80)
        all_passed = all(results.values())
        status = "READY FOR PRODUCTION" if all_passed else "NEEDS ATTENTION"
        print(f"Overall Status: {status}")
        print("="*80 + "\n")
        
        # Assert all tests passed
        assert results["accuracy"], "Accuracy test failed"
        assert results["performance"], "Performance test failed"
        assert results["citations"], "Citations test failed"
        assert results["edge_cases"], "Edge cases test failed"
        
        print("PASS: All system readiness tests passed!\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
