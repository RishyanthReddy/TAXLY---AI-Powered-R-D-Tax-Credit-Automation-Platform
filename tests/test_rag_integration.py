"""
Integration tests for the RAG pipeline.

This module tests the complete RAG (Retrieval-Augmented Generation) pipeline:
- Full indexing pipeline with sample PDFs
- Query retrieval with known questions
- Relevance of retrieved chunks
- Error handling for missing documents
- End-to-end workflow from PDF to query results

Requirements: Testing (Task 48)
"""

import pytest
import os
import tempfile
import shutil
import gc
import time
from pathlib import Path

from tools.indexing_pipeline import index_documents, index_single_document, get_indexing_status
from tools.rd_knowledge_tool import RD_Knowledge_Tool
from tools.vector_db import VectorDB
from tools.embedder import Embedder
from tools.pdf_extractor import extract_text_from_pdf
from tools.text_chunker import chunk_document
from models.tax_models import RAGContext
from utils.exceptions import RAGRetrievalError


@pytest.fixture
def temp_kb_dir():
    """Create a temporary directory for test knowledge base"""
    temp_dir = tempfile.mkdtemp()
    
    # Create subdirectories
    tax_docs_dir = Path(temp_dir) / "tax_docs"
    indexed_dir = Path(temp_dir) / "indexed"
    tax_docs_dir.mkdir(exist_ok=True)
    indexed_dir.mkdir(exist_ok=True)
    
    yield temp_dir
    
    # Cleanup
    gc.collect()
    time.sleep(0.1)
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except PermissionError:
        pass


@pytest.fixture
def sample_pdf_path():
    """Get path to a sample PDF from the knowledge base"""
    kb_path = Path("rd_tax_agent/knowledge_base/tax_docs")
    
    # Try to find a PDF file
    pdf_files = list(kb_path.glob("*.pdf"))
    
    if pdf_files:
        return str(pdf_files[0])
    
    # If no PDF, try text file
    txt_files = list(kb_path.glob("*.txt"))
    if txt_files:
        return str(txt_files[0])
    
    pytest.skip("No sample PDF or text file found in knowledge base")


@pytest.fixture
def sample_metadata(temp_kb_dir):
    """Create sample metadata.json for testing"""
    import json
    
    metadata = {
        "last_updated": "2024-01-01T00:00:00",
        "documents": [
            {
                "id": "test_doc_1",
                "filename": "test_document.txt",
                "title": "Test IRS Document",
                "source": "IRS Test Source",
                "download_date": "2024-01-01",
                "version": "2024",
                "description": "Test document for integration testing",
                "key_topics": ["qualified research", "four-part test"],
                "page_count": 1,
                "file_size_kb": 1,
                "indexed": False
            }
        ]
    }
    
    metadata_path = Path(temp_kb_dir) / "metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    # Create the test document
    test_doc_path = Path(temp_kb_dir) / "tax_docs" / "test_document.txt"
    test_content = """
    Section 41 of the Internal Revenue Code provides a research and development tax credit.
    
    Qualified research must meet the four-part test:
    1. The research must be technological in nature
    2. The research must be undertaken for a qualified purpose
    3. The research must involve a process of experimentation
    4. The research must relate to a new or improved business component
    
    Qualified research expenses (QREs) include wages paid to employees for qualified services,
    supplies used in the conduct of qualified research, and amounts paid for computer use.
    """
    
    with open(test_doc_path, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    return metadata_path


# ============================================================================
# Full Indexing Pipeline Tests
# ============================================================================

class TestFullIndexingPipeline:
    """Test the complete indexing pipeline with sample documents"""
    
    def test_index_documents_with_sample_metadata(self, temp_kb_dir, sample_metadata):
        """Test full indexing pipeline with sample metadata"""
        # Run indexing pipeline
        results = index_documents(
            knowledge_base_path=temp_kb_dir,
            chunk_size=512,
            overlap=50,
            force_reindex=False
        )
        
        # Verify results
        assert results['total_documents'] == 1
        assert results['documents_indexed'] == 1
        assert results['documents_failed'] == 0
        assert results['total_chunks'] > 0
        assert results['total_embeddings'] > 0
        assert results['duration_seconds'] > 0
        
        # Verify metadata was updated
        import json
        with open(sample_metadata, 'r', encoding='utf-8') as f:
            updated_metadata = json.load(f)
        
        assert updated_metadata['documents'][0]['indexed'] is True
        assert updated_metadata['documents'][0]['chunk_count'] > 0
    
    def test_index_documents_skip_already_indexed(self, temp_kb_dir, sample_metadata):
        """Test that already indexed documents are skipped"""
        # Index once
        results1 = index_documents(
            knowledge_base_path=temp_kb_dir,
            chunk_size=512,
            overlap=50
        )
        
        assert results1['documents_indexed'] == 1
        
        # Index again without force_reindex
        results2 = index_documents(
            knowledge_base_path=temp_kb_dir,
            chunk_size=512,
            overlap=50,
            force_reindex=False
        )
        
        # Should skip already indexed documents
        assert results2['documents_indexed'] == 0
        assert results2['documents_skipped'] == 1
    
    def test_index_documents_force_reindex(self, temp_kb_dir, sample_metadata):
        """Test force reindexing of already indexed documents"""
        # Index once
        results1 = index_documents(
            knowledge_base_path=temp_kb_dir,
            chunk_size=512,
            overlap=50
        )
        
        assert results1['documents_indexed'] == 1
        
        # Force reindex
        results2 = index_documents(
            knowledge_base_path=temp_kb_dir,
            chunk_size=512,
            overlap=50,
            force_reindex=True
        )
        
        # Should reindex all documents
        assert results2['documents_indexed'] == 1
        assert results2['documents_skipped'] == 0
    
    def test_indexing_creates_vector_database(self, temp_kb_dir, sample_metadata):
        """Test that indexing creates and populates vector database"""
        # Run indexing
        results = index_documents(
            knowledge_base_path=temp_kb_dir,
            chunk_size=512,
            overlap=50
        )
        
        assert results['documents_indexed'] == 1
        
        # Verify vector database was created
        indexed_path = Path(temp_kb_dir) / "indexed"
        assert indexed_path.exists()
        
        # Verify we can query the database
        vector_db = VectorDB(
            persist_directory=str(indexed_path),
            collection_name="irs_documents"
        )
        
        try:
            count = vector_db.count()
            assert count > 0
            assert count == results['total_chunks']
        finally:
            del vector_db
            gc.collect()
    
    def test_get_indexing_status(self, temp_kb_dir, sample_metadata):
        """Test getting indexing status"""
        # Before indexing
        status_before = get_indexing_status(temp_kb_dir)
        assert status_before['total_documents'] == 1
        assert status_before['indexed_documents'] == 0
        assert status_before['unindexed_documents'] == 1
        
        # Index documents
        index_documents(temp_kb_dir, chunk_size=512, overlap=50)
        
        # After indexing
        status_after = get_indexing_status(temp_kb_dir)
        assert status_after['total_documents'] == 1
        assert status_after['indexed_documents'] == 1
        assert status_after['unindexed_documents'] == 0


# ============================================================================
# Query Retrieval Tests
# ============================================================================

class TestQueryRetrieval:
    """Test query retrieval with known questions"""
    
    @pytest.fixture(autouse=True)
    def setup_indexed_kb(self, temp_kb_dir, sample_metadata):
        """Set up indexed knowledge base for query tests"""
        # Index the documents
        index_documents(
            knowledge_base_path=temp_kb_dir,
            chunk_size=512,
            overlap=50
        )
        
        self.kb_path = temp_kb_dir
        # RD_Knowledge_Tool needs the path to the indexed directory
        indexed_path = str(Path(temp_kb_dir) / "indexed")
        self.rd_tool = RD_Knowledge_Tool(knowledge_base_path=indexed_path)
        
        yield
        
        # Cleanup
        try:
            del self.rd_tool
        except:
            pass
        gc.collect()
    
    def test_query_four_part_test(self):
        """Test querying for the four-part test"""
        context = self.rd_tool.query("What is the four-part test?", top_k=3)
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        # Should retrieve relevant chunks about four-part test
        found_relevant = any(
            "four-part test" in chunk['text'].lower()
            for chunk in context.chunks
        )
        assert found_relevant, "Should find chunks about four-part test"
    
    def test_query_qualified_research_expenses(self):
        """Test querying for qualified research expenses"""
        context = self.rd_tool.query("What are qualified research expenses?", top_k=3)
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        # Should retrieve relevant chunks about QREs
        found_relevant = any(
            "qualified research expenses" in chunk['text'].lower() or
            "qre" in chunk['text'].lower()
            for chunk in context.chunks
        )
        assert found_relevant, "Should find chunks about QREs"
    
    def test_query_with_abbreviation(self):
        """Test querying with abbreviation (QRE)"""
        context = self.rd_tool.query("QRE", top_k=3, enable_query_expansion=True)
        
        assert isinstance(context, RAGContext)
        assert context.chunk_count > 0
        
        # Query expansion should help find relevant results
        assert context.average_relevance > 0
    
    def test_query_returns_sorted_by_relevance(self):
        """Test that query results are sorted by relevance"""
        context = self.rd_tool.query("qualified research", top_k=5)
        
        if context.chunk_count > 1:
            scores = [chunk['relevance_score'] for chunk in context.chunks]
            assert scores == sorted(scores, reverse=True), "Results should be sorted by relevance"
    
    def test_query_includes_source_citations(self):
        """Test that query results include source citations"""
        context = self.rd_tool.query("four-part test", top_k=3)
        
        assert context.chunk_count > 0
        
        for chunk in context.chunks:
            assert 'source' in chunk
            assert 'page' in chunk
            assert isinstance(chunk['source'], str)
            assert isinstance(chunk['page'], int)


# ============================================================================
# Relevance Verification Tests
# ============================================================================

class TestRelevanceVerification:
    """Test that retrieved chunks are relevant to queries"""
    
    @pytest.fixture(autouse=True)
    def setup_indexed_kb(self, temp_kb_dir, sample_metadata):
        """Set up indexed knowledge base"""
        index_documents(temp_kb_dir, chunk_size=512, overlap=50)
        indexed_path = str(Path(temp_kb_dir) / "indexed")
        self.rd_tool = RD_Knowledge_Tool(knowledge_base_path=indexed_path)
        yield
        try:
            del self.rd_tool
        except:
            pass
        gc.collect()
    
    def test_relevance_scores_are_reasonable(self):
        """Test that relevance scores are in reasonable range"""
        context = self.rd_tool.query("qualified research", top_k=3)
        
        assert context.chunk_count > 0
        
        for chunk in context.chunks:
            # Relevance scores should be between 0 and 1
            assert 0 <= chunk['relevance_score'] <= 1
            
            # For a direct query match, scores should be reasonably high
            if "qualified research" in chunk['text'].lower():
                assert chunk['relevance_score'] > 0.3, "Direct matches should have decent relevance"
    
    def test_high_relevance_for_exact_matches(self):
        """Test that exact phrase matches have high relevance"""
        context = self.rd_tool.query("four-part test", top_k=3)
        
        # Find chunks with exact phrase match
        exact_matches = [
            chunk for chunk in context.chunks
            if "four-part test" in chunk['text'].lower()
        ]
        
        if exact_matches:
            # Exact matches should have high relevance
            for chunk in exact_matches:
                assert chunk['relevance_score'] > 0.5, "Exact matches should have high relevance"
    
    def test_semantic_similarity_retrieval(self):
        """Test that semantically similar content is retrieved"""
        # Query with paraphrased question
        context = self.rd_tool.query("What are the requirements for R&D credit?", top_k=3)
        
        assert context.chunk_count > 0
        
        # Should retrieve content about requirements/criteria even if exact words differ
        found_relevant = any(
            "qualified" in chunk['text'].lower() or
            "research" in chunk['text'].lower() or
            "test" in chunk['text'].lower()
            for chunk in context.chunks
        )
        assert found_relevant, "Should find semantically similar content"
    
    def test_average_relevance_calculation(self):
        """Test that average relevance is calculated correctly"""
        context = self.rd_tool.query("qualified research expenses", top_k=3)
        
        if context.chunk_count > 0:
            expected_avg = sum(c['relevance_score'] for c in context.chunks) / context.chunk_count
            assert abs(context.average_relevance - expected_avg) < 0.01


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling for missing documents and edge cases"""
    
    def test_missing_knowledge_base_directory(self):
        """Test handling of missing knowledge base directory"""
        with pytest.raises(FileNotFoundError):
            index_documents(
                knowledge_base_path="/nonexistent/path",
                chunk_size=512,
                overlap=50
            )
    
    def test_missing_tax_docs_directory(self, temp_kb_dir):
        """Test handling of missing tax_docs directory"""
        # Remove the tax_docs directory that was created by fixture
        tax_docs_path = Path(temp_kb_dir) / "tax_docs"
        if tax_docs_path.exists():
            shutil.rmtree(tax_docs_path)
        
        # Create metadata
        metadata_path = Path(temp_kb_dir) / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            import json
            json.dump({"documents": []}, f)
        
        with pytest.raises(FileNotFoundError, match="Tax documents directory"):
            index_documents(
                knowledge_base_path=temp_kb_dir,
                chunk_size=512,
                overlap=50
            )
    
    def test_missing_metadata_file(self, temp_kb_dir):
        """Test handling of missing metadata.json"""
        # Create tax_docs directory but no metadata
        tax_docs_dir = Path(temp_kb_dir) / "tax_docs"
        tax_docs_dir.mkdir(exist_ok=True)
        
        with pytest.raises(Exception):  # Should raise IndexingPipelineError
            index_documents(
                knowledge_base_path=temp_kb_dir,
                chunk_size=512,
                overlap=50
            )
    
    def test_corrupted_metadata_file(self, temp_kb_dir):
        """Test handling of corrupted metadata.json"""
        tax_docs_dir = Path(temp_kb_dir) / "tax_docs"
        tax_docs_dir.mkdir(exist_ok=True)
        
        # Create corrupted metadata
        metadata_path = Path(temp_kb_dir) / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write("{ invalid json }")
        
        with pytest.raises(Exception):  # Should raise IndexingPipelineError
            index_documents(
                knowledge_base_path=temp_kb_dir,
                chunk_size=512,
                overlap=50
            )
    
    def test_missing_document_file(self, temp_kb_dir):
        """Test handling of missing document file referenced in metadata"""
        import json
        
        # Create metadata referencing non-existent file
        tax_docs_dir = Path(temp_kb_dir) / "tax_docs"
        tax_docs_dir.mkdir(exist_ok=True)
        
        metadata = {
            "documents": [
                {
                    "id": "missing_doc",
                    "filename": "nonexistent.pdf",
                    "title": "Missing Document",
                    "indexed": False
                }
            ]
        }
        
        metadata_path = Path(temp_kb_dir) / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f)
        
        # Should handle missing file gracefully
        results = index_documents(
            knowledge_base_path=temp_kb_dir,
            chunk_size=512,
            overlap=50
        )
        
        assert results['documents_failed'] == 1
        assert len(results['errors']) > 0
    
    def test_empty_knowledge_base_query(self, temp_kb_dir):
        """Test querying an empty knowledge base"""
        # Create empty vector database
        indexed_dir = Path(temp_kb_dir) / "indexed"
        indexed_dir.mkdir(exist_ok=True)
        
        vector_db = VectorDB(
            persist_directory=str(indexed_dir),
            collection_name="irs_documents"
        )
        del vector_db
        gc.collect()
        
        # Create RD tool with empty KB
        indexed_path = str(Path(temp_kb_dir) / "indexed")
        rd_tool = RD_Knowledge_Tool(knowledge_base_path=indexed_path)
        
        try:
            # Query should return empty context
            context = rd_tool.query("test query", top_k=3)
            
            assert isinstance(context, RAGContext)
            assert context.chunk_count == 0
            assert context.total_chunks_available == 0
        finally:
            del rd_tool
            gc.collect()
    
    def test_query_with_invalid_parameters(self, temp_kb_dir, sample_metadata):
        """Test query with invalid parameters"""
        index_documents(temp_kb_dir, chunk_size=512, overlap=50)
        indexed_path = str(Path(temp_kb_dir) / "indexed")
        rd_tool = RD_Knowledge_Tool(knowledge_base_path=indexed_path)
        
        try:
            # Empty query
            with pytest.raises(ValueError):
                rd_tool.query("", top_k=3)
            
            # Invalid top_k
            with pytest.raises(ValueError):
                rd_tool.query("test", top_k=0)
            
            with pytest.raises(ValueError):
                rd_tool.query("test", top_k=-1)
        finally:
            del rd_tool
            gc.collect()


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================

class TestEndToEndWorkflow:
    """Test complete end-to-end RAG workflow"""
    
    def test_complete_workflow_from_pdf_to_query(self, temp_kb_dir, sample_metadata):
        """Test complete workflow: index documents -> query -> format for LLM"""
        # Step 1: Index documents
        index_results = index_documents(
            knowledge_base_path=temp_kb_dir,
            chunk_size=512,
            overlap=50
        )
        
        assert index_results['documents_indexed'] == 1
        assert index_results['total_chunks'] > 0
        
        # Step 2: Create RD Knowledge Tool
        indexed_path = str(Path(temp_kb_dir) / "indexed")
        rd_tool = RD_Knowledge_Tool(knowledge_base_path=indexed_path)
        
        try:
            # Step 3: Query the knowledge base
            context = rd_tool.query("What is the four-part test?", top_k=3)
            
            assert isinstance(context, RAGContext)
            assert context.chunk_count > 0
            
            # Step 4: Format for LLM
            formatted = rd_tool.format_for_llm(context)
            
            assert isinstance(formatted, str)
            assert len(formatted) > 0
            assert "IRS GUIDANCE CONTEXT" in formatted
            assert "four-part test" in context.query.lower()
            
            # Step 5: Extract citations
            citations = context.extract_citations()
            
            assert isinstance(citations, list)
            assert len(citations) > 0
        finally:
            del rd_tool
            gc.collect()
    
    def test_workflow_with_multiple_queries(self, temp_kb_dir, sample_metadata):
        """Test workflow with multiple sequential queries"""
        # Index documents
        index_documents(temp_kb_dir, chunk_size=512, overlap=50)
        
        # Create tool
        indexed_path = str(Path(temp_kb_dir) / "indexed")
        rd_tool = RD_Knowledge_Tool(knowledge_base_path=indexed_path)
        
        try:
            # Multiple queries
            queries = [
                "What is the four-part test?",
                "What are qualified research expenses?",
                "What is Section 41?"
            ]
            
            for query_text in queries:
                context = rd_tool.query(query_text, top_k=2)
                
                assert isinstance(context, RAGContext)
                assert context.query == query_text
                # May or may not have results depending on content
        finally:
            del rd_tool
            gc.collect()
    
    def test_workflow_with_query_optimizations(self, temp_kb_dir, sample_metadata):
        """Test workflow with all query optimizations enabled"""
        # Index documents
        index_documents(temp_kb_dir, chunk_size=512, overlap=50)
        
        # Create tool
        indexed_path = str(Path(temp_kb_dir) / "indexed")
        rd_tool = RD_Knowledge_Tool(knowledge_base_path=indexed_path)
        
        try:
            # Query with all optimizations
            context = rd_tool.query(
                "QRE",
                top_k=3,
                enable_query_expansion=True,
                enable_query_rewriting=True,
                enable_reranking=True
            )
            
            assert isinstance(context, RAGContext)
            assert "semantic_search" in context.retrieval_method
            
            # Format for LLM
            formatted = rd_tool.format_for_llm(
                context,
                include_relevance_scores=True,
                include_metadata=True
            )
            
            assert "IRS GUIDANCE CONTEXT" in formatted
            assert "Retrieval Method:" in formatted
        finally:
            del rd_tool
            gc.collect()
    
    def test_reindexing_workflow(self, temp_kb_dir, sample_metadata):
        """Test reindexing workflow"""
        # Initial indexing
        results1 = index_documents(temp_kb_dir, chunk_size=512, overlap=50)
        assert results1['documents_indexed'] == 1
        
        # Query to verify
        indexed_path = str(Path(temp_kb_dir) / "indexed")
        rd_tool1 = RD_Knowledge_Tool(knowledge_base_path=indexed_path)
        try:
            context1 = rd_tool1.query("qualified research", top_k=2)
            initial_chunk_count = context1.chunk_count
        finally:
            del rd_tool1
            gc.collect()
        
        # Force reindex with different chunk size
        results2 = index_documents(
            temp_kb_dir,
            chunk_size=256,  # Smaller chunks
            overlap=25,
            force_reindex=True
        )
        
        assert results2['documents_indexed'] == 1
        
        # Query again
        rd_tool2 = RD_Knowledge_Tool(knowledge_base_path=indexed_path)
        try:
            context2 = rd_tool2.query("qualified research", top_k=2)
            # Different chunk size may result in different number of chunks
            assert isinstance(context2, RAGContext)
        finally:
            del rd_tool2
            gc.collect()


# ============================================================================
# Performance and Scalability Tests
# ============================================================================

class TestPerformanceAndScalability:
    """Test performance characteristics of the RAG pipeline"""
    
    def test_indexing_performance(self, temp_kb_dir, sample_metadata):
        """Test that indexing completes in reasonable time"""
        import time
        
        start_time = time.time()
        
        results = index_documents(
            knowledge_base_path=temp_kb_dir,
            chunk_size=512,
            overlap=50
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 30 seconds for small document)
        assert duration < 30, f"Indexing took {duration:.2f} seconds"
        assert results['duration_seconds'] > 0
    
    def test_query_performance(self, temp_kb_dir, sample_metadata):
        """Test that queries complete in reasonable time"""
        import time
        
        # Index documents
        index_documents(temp_kb_dir, chunk_size=512, overlap=50)
        
        # Create tool
        indexed_path = str(Path(temp_kb_dir) / "indexed")
        rd_tool = RD_Knowledge_Tool(knowledge_base_path=indexed_path)
        
        try:
            # Measure query time
            start_time = time.time()
            
            context = rd_tool.query("qualified research", top_k=3)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Query should complete quickly (< 5 seconds per requirement)
            assert duration < 5, f"Query took {duration:.2f} seconds"
            assert isinstance(context, RAGContext)
        finally:
            del rd_tool
            gc.collect()
    
    def test_multiple_concurrent_queries(self, temp_kb_dir, sample_metadata):
        """Test handling of multiple queries in sequence"""
        # Index documents
        index_documents(temp_kb_dir, chunk_size=512, overlap=50)
        
        # Create tool
        indexed_path = str(Path(temp_kb_dir) / "indexed")
        rd_tool = RD_Knowledge_Tool(knowledge_base_path=indexed_path)
        
        try:
            # Run multiple queries
            for i in range(5):
                context = rd_tool.query(f"query {i}", top_k=2)
                assert isinstance(context, RAGContext)
        finally:
            del rd_tool
            gc.collect()


# ============================================================================
# Integration with Real Knowledge Base (Optional)
# ============================================================================

class TestRealKnowledgeBase:
    """Test with real IRS documents if available"""
    
    @pytest.mark.skipif(
        not Path("knowledge_base/tax_docs").exists(),
        reason="Real knowledge base not available"
    )
    def test_query_real_knowledge_base(self):
        """Test querying the real knowledge base"""
        kb_path = "knowledge_base"
        
        # Check if already indexed
        status = get_indexing_status(kb_path)
        
        if status.get('indexed_documents', 0) == 0:
            pytest.skip("Real knowledge base not indexed")
        
        # Create tool with correct indexed path
        indexed_path = str(Path(kb_path) / "indexed")
        rd_tool = RD_Knowledge_Tool(knowledge_base_path=indexed_path)
        
        try:
            # Test known queries
            test_queries = [
                "What is the four-part test?",
                "What are qualified research expenses?",
                "What is a process of experimentation?"
            ]
            
            for query_text in test_queries:
                context = rd_tool.query(query_text, top_k=3)
                
                assert isinstance(context, RAGContext)
                # Real KB should have relevant results
                if context.chunk_count > 0:
                    assert context.average_relevance > 0
        finally:
            try:
                del rd_tool
            except:
                pass
            gc.collect()
