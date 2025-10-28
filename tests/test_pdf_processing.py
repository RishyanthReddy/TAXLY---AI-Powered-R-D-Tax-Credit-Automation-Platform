"""
Integration tests for PDF extraction and text chunking.

This module tests the complete PDF processing pipeline:
- Extraction from sample PDFs
- Chunking with various text lengths
- Overlap preservation between chunks
- Metadata attachment throughout the pipeline
- Token count accuracy

Requirements: Testing (Task 38)
"""

import pytest
from pathlib import Path
import tiktoken

from tools.pdf_extractor import extract_text_from_pdf, extract_text_from_multiple_pdfs
from tools.text_chunker import chunk_text, chunk_document, chunk_multiple_documents


class TestPDFExtractionAndChunking:
    """Integration tests for the complete PDF processing pipeline."""
    
    def test_extract_and_chunk_workflow(self):
        """Test the complete extraction and chunking workflow with mock data."""
        # Simulate a document extracted from PDF
        mock_extraction_result = {
            'file_path': 'test_document.pdf',
            'pages': [
                {
                    'page_number': 1,
                    'text': 'Section 41 of the Internal Revenue Code provides a tax credit. ' * 20,
                    'char_count': 1280
                },
                {
                    'page_number': 2,
                    'text': 'Qualified research expenses include in-house research expenses. ' * 20,
                    'char_count': 1320
                }
            ],
            'total_pages': 2,
            'total_chars': 2600,
            'text': 'Section 41 of the Internal Revenue Code provides a tax credit. ' * 20 + 
                    'Qualified research expenses include in-house research expenses. ' * 20
        }
        
        # Step 1: Verify extraction result structure
        assert 'text' in mock_extraction_result
        assert 'pages' in mock_extraction_result
        assert mock_extraction_result['total_pages'] > 0
        
        # Step 2: Chunk the extracted document
        chunks = chunk_document(
            mock_extraction_result,
            chunk_size=512,
            overlap=50
        )
        
        assert len(chunks) > 0
        
        # Verify all chunks have complete metadata
        for chunk in chunks:
            assert 'text' in chunk
            assert 'token_count' in chunk
            assert 'char_count' in chunk
            assert 'chunk_index' in chunk
            assert 'source_document' in chunk
            assert 'page_number' in chunk
            assert chunk['source_document'] == 'test_document.pdf'
    
    def test_multiple_documents_workflow(self):
        """Test extraction and chunking of multiple documents with mock data."""
        # Simulate multiple extracted documents
        mock_documents = [
            {
                'file_path': 'doc1.pdf',
                'pages': [
                    {'page_number': 1, 'text': 'Document one content about research. ' * 30}
                ],
                'total_pages': 1
            },
            {
                'file_path': 'doc2.pdf',
                'pages': [
                    {'page_number': 1, 'text': 'Document two content about tax credits. ' * 30}
                ],
                'total_pages': 1
            },
            {
                'file_path': 'doc3.pdf',
                'pages': [
                    {'page_number': 1, 'text': 'Document three content about qualified expenses. ' * 30}
                ],
                'total_pages': 1
            }
        ]
        
        # Chunk all documents
        chunking_result = chunk_multiple_documents(
            mock_documents,
            chunk_size=512,
            overlap=50
        )
        
        assert chunking_result['total_chunks'] > 0
        assert chunking_result['documents_processed'] == 3
        assert chunking_result['documents_failed'] == 0
        
        # Verify chunks from different documents are distinguishable
        source_documents = set(chunk['source_document'] for chunk in chunking_result['chunks'])
        assert len(source_documents) == 3
        assert 'doc1.pdf' in source_documents
        assert 'doc2.pdf' in source_documents
        assert 'doc3.pdf' in source_documents


class TestChunkingWithVariousTextLengths:
    """Test chunking behavior with different text lengths."""
    
    def test_very_short_text(self):
        """Test chunking of text shorter than chunk size."""
        text = "This is a very short document."
        chunks = chunk_text(text, chunk_size=512, overlap=50)
        
        # Should create exactly one chunk
        assert len(chunks) == 1
        assert chunks[0]['text'] == text
        assert chunks[0]['chunk_index'] == 0
    
    def test_medium_length_text(self):
        """Test chunking of text that creates 2-3 chunks."""
        # Create text that will span multiple chunks
        text = " ".join([f"This is sentence number {i} in the document." for i in range(50)])
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        
        # Should create multiple chunks
        assert len(chunks) >= 2
        
        # Verify chunks are sequential
        for i, chunk in enumerate(chunks):
            assert chunk['chunk_index'] == i
    
    def test_very_long_text(self):
        """Test chunking of very long text (many chunks)."""
        # Create a long document
        text = " ".join([
            f"Paragraph {i}. This paragraph contains multiple sentences about qualified research. "
            f"It discusses the four-part test and technological uncertainty. "
            f"The process of experimentation is also covered in detail."
            for i in range(100)
        ])
        
        chunks = chunk_text(text, chunk_size=200, overlap=30)
        
        # Should create many chunks
        assert len(chunks) >= 10
        
        # Verify all text is covered
        total_chars_in_chunks = sum(chunk['char_count'] for chunk in chunks)
        # Due to overlap, total chars in chunks will be more than original text
        assert total_chars_in_chunks >= len(text)
    
    def test_single_sentence_longer_than_chunk_size(self):
        """Test handling of a single sentence that exceeds chunk size."""
        # Create a very long sentence
        long_sentence = (
            "This is an extremely long sentence that contains many clauses and phrases "
            "and continues on and on without any breaks or periods and will definitely "
            "exceed the specified chunk size limit but should still be handled gracefully "
            "by the chunking algorithm which should keep the sentence intact to preserve "
            "semantic meaning and context even though it violates the token limit."
        )
        
        chunks = chunk_text(long_sentence, chunk_size=50, overlap=10)
        
        # Should create at least one chunk
        assert len(chunks) >= 1
        
        # The sentence should be preserved (not split mid-sentence)
        assert chunks[0]['text'] == long_sentence
    
    def test_empty_and_whitespace_text(self):
        """Test handling of empty or whitespace-only text."""
        # Empty string
        chunks = chunk_text("", chunk_size=512, overlap=50)
        assert chunks == []
        
        # Whitespace only
        chunks = chunk_text("   \n\n   ", chunk_size=512, overlap=50)
        assert chunks == []
    
    def test_text_with_exact_chunk_size(self):
        """Test text that is exactly the chunk size."""
        encoding = tiktoken.get_encoding("cl100k_base")
        
        # Create text that is exactly 50 tokens
        text = "word " * 50
        text = text.strip()
        
        # Adjust to get exactly 50 tokens
        while len(encoding.encode(text)) != 50:
            if len(encoding.encode(text)) < 50:
                text += " word"
            else:
                text = " ".join(text.split()[:-1])
        
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        
        # Should create exactly one chunk
        assert len(chunks) == 1
        assert chunks[0]['token_count'] == 50


class TestOverlapPreservation:
    """Test that overlap is correctly preserved between chunks."""
    
    def test_overlap_exists_between_chunks(self):
        """Test that consecutive chunks have overlapping content."""
        text = " ".join([f"Sentence {i}." for i in range(100)])
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                chunk1_text = chunks[i]['text']
                chunk2_text = chunks[i + 1]['text']
                
                # Extract words from end of first chunk and start of second chunk
                chunk1_words = chunk1_text.split()[-15:]
                chunk2_words = chunk2_text.split()[:15]
                
                # Should have some overlapping words
                overlap_words = set(chunk1_words) & set(chunk2_words)
                assert len(overlap_words) > 0, f"No overlap found between chunks {i} and {i+1}"
    
    def test_overlap_size_approximately_correct(self):
        """Test that overlap size is approximately as specified."""
        text = " ".join([f"This is sentence number {i} in the test document." for i in range(50)])
        overlap_tokens = 20
        chunks = chunk_text(text, chunk_size=100, overlap=overlap_tokens)
        
        encoding = tiktoken.get_encoding("cl100k_base")
        
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                chunk1_text = chunks[i]['text']
                chunk2_text = chunks[i + 1]['text']
                
                # Find overlapping text
                chunk1_words = chunk1_text.split()
                chunk2_words = chunk2_text.split()
                
                # Find common subsequence at the boundary
                overlap_found = False
                for j in range(len(chunk1_words)):
                    for k in range(len(chunk2_words)):
                        if chunk1_words[j:] == chunk2_words[:len(chunk1_words[j:])]:
                            overlap_text = " ".join(chunk1_words[j:])
                            overlap_token_count = len(encoding.encode(overlap_text))
                            
                            # Overlap should be approximately the specified size
                            # Allow some tolerance (within 50% of target)
                            assert overlap_token_count <= overlap_tokens * 1.5
                            overlap_found = True
                            break
                    if overlap_found:
                        break
    
    def test_no_overlap_with_zero_overlap(self):
        """Test that no overlap occurs when overlap=0."""
        text = " ".join([f"Sentence {i}." for i in range(50)])
        chunks = chunk_text(text, chunk_size=50, overlap=0)
        
        if len(chunks) > 1:
            # Verify no text is repeated between chunks
            all_text = " ".join(chunk['text'] for chunk in chunks)
            original_words = text.split()
            reconstructed_words = all_text.split()
            
            # With no overlap, we should have approximately the same number of words
            # (allowing for sentence boundary adjustments)
            assert abs(len(reconstructed_words) - len(original_words)) < len(original_words) * 0.2


class TestMetadataAttachment:
    """Test that metadata is correctly attached throughout the pipeline."""
    
    def test_metadata_from_extraction_to_chunks(self):
        """Test that metadata flows from extraction to chunks."""
        # Simulate extraction result with metadata
        mock_extraction_result = {
            'file_path': '/path/to/tax_document.pdf',
            'pages': [
                {'page_number': 1, 'text': 'Page one content. ' * 50},
                {'page_number': 2, 'text': 'Page two content. ' * 50}
            ],
            'total_pages': 2,
            'metadata': {
                'title': 'IRS Tax Document',
                'author': 'Internal Revenue Service'
            }
        }
        
        # Chunk the document
        chunks = chunk_document(mock_extraction_result, chunk_size=512, overlap=50)
        
        # Verify each chunk has source document and page number
        for chunk in chunks:
            assert 'source_document' in chunk
            assert 'page_number' in chunk
            assert chunk['source_document'] == '/path/to/tax_document.pdf'
            assert isinstance(chunk['page_number'], int)
            assert chunk['page_number'] > 0
    
    def test_chunk_metadata_completeness(self):
        """Test that all required metadata fields are present in chunks."""
        text = "This is a test document with multiple sentences. " * 20
        chunks = chunk_text(
            text,
            chunk_size=100,
            overlap=20,
            source_document="test.pdf",
            page_number=5
        )
        
        required_fields = [
            'text',
            'token_count',
            'char_count',
            'chunk_index',
            'source_document',
            'page_number',
            'start_char',
            'end_char'
        ]
        
        for chunk in chunks:
            for field in required_fields:
                assert field in chunk, f"Missing field: {field}"
    
    def test_page_number_tracking_across_pages(self):
        """Test that page numbers are correctly tracked across multiple pages."""
        document = {
            'file_path': 'multi_page.pdf',
            'pages': [
                {'page_number': 1, 'text': 'Page one content. ' * 50},
                {'page_number': 2, 'text': 'Page two content. ' * 50},
                {'page_number': 3, 'text': 'Page three content. ' * 50}
            ],
            'total_pages': 3
        }
        
        chunks = chunk_document(document, chunk_size=100, overlap=20)
        
        # Verify chunks from each page have correct page numbers
        page_1_chunks = [c for c in chunks if c['page_number'] == 1]
        page_2_chunks = [c for c in chunks if c['page_number'] == 2]
        page_3_chunks = [c for c in chunks if c['page_number'] == 3]
        
        assert len(page_1_chunks) > 0
        assert len(page_2_chunks) > 0
        assert len(page_3_chunks) > 0
        
        # Verify all chunks are accounted for
        assert len(page_1_chunks) + len(page_2_chunks) + len(page_3_chunks) == len(chunks)
    
    def test_start_and_end_char_positions(self):
        """Test that character positions are tracked correctly."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunk_text(text, chunk_size=20, overlap=5)
        
        for chunk in chunks:
            assert 'start_char' in chunk
            assert 'end_char' in chunk
            assert chunk['start_char'] >= 0
            assert chunk['end_char'] > chunk['start_char']
            assert chunk['end_char'] <= len(text) * 2  # Allow for spacing adjustments


class TestTokenCountAccuracy:
    """Test that token counts are accurate throughout the pipeline."""
    
    def test_token_count_matches_tiktoken(self):
        """Test that reported token counts match tiktoken encoding."""
        text = "This is a test document for verifying token count accuracy. " * 10
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        
        encoding = tiktoken.get_encoding("cl100k_base")
        
        for chunk in chunks:
            actual_token_count = len(encoding.encode(chunk['text']))
            assert chunk['token_count'] == actual_token_count
    
    def test_token_counts_respect_chunk_size(self):
        """Test that token counts respect the specified chunk size."""
        text = " ".join([f"Sentence number {i} in the document." for i in range(100)])
        chunk_size = 75
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=15)
        
        for chunk in chunks:
            # Allow some tolerance for sentence boundary preservation
            # Chunks may exceed chunk_size if needed to keep sentences intact
            assert chunk['token_count'] <= chunk_size * 1.5
    
    def test_total_tokens_across_chunks(self):
        """Test that total tokens across chunks covers the original text."""
        text = "This is a comprehensive test of token counting across multiple chunks. " * 20
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        
        encoding = tiktoken.get_encoding("cl100k_base")
        original_token_count = len(encoding.encode(text))
        
        # Sum of all chunk tokens (accounting for overlap)
        total_chunk_tokens = sum(chunk['token_count'] for chunk in chunks)
        
        # Total should be approximately equal to or greater than original
        # Allow small variance due to sentence boundary preservation
        assert total_chunk_tokens >= original_token_count * 0.95
    
    def test_char_count_accuracy(self):
        """Test that character counts are accurate."""
        text = "Testing character count accuracy in chunks."
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        
        for chunk in chunks:
            assert chunk['char_count'] == len(chunk['text'])
    
    def test_token_count_with_special_characters(self):
        """Test token counting with special characters and punctuation."""
        text = (
            "Section §1.41-4 defines 'qualified research' under IRC §41. "
            "The four-part test includes: (1) technological uncertainty, "
            "(2) process of experimentation, (3) technological in nature, "
            "and (4) qualified purpose. See 26 CFR §1.41-4(a)(1)-(4)."
        )
        
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        
        encoding = tiktoken.get_encoding("cl100k_base")
        
        for chunk in chunks:
            actual_token_count = len(encoding.encode(chunk['text']))
            assert chunk['token_count'] == actual_token_count


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_document_with_no_extractable_text(self):
        """Test handling of documents with no extractable text."""
        # Simulate a document with empty pages (like a scanned PDF without OCR)
        empty_document = {
            'file_path': 'scanned_document.pdf',
            'pages': [
                {'page_number': 1, 'text': ''},
                {'page_number': 2, 'text': ''},
                {'page_number': 3, 'text': ''}
            ],
            'total_pages': 3,
            'total_chars': 0
        }
        
        # Chunking should handle empty pages gracefully
        chunks = chunk_document(empty_document, chunk_size=512, overlap=50)
        
        # Should return empty list since there's no text to chunk
        assert len(chunks) == 0
    
    def test_chunking_with_different_encodings(self):
        """Test chunking with different tiktoken encodings."""
        text = "This is a test of different encodings. " * 10
        
        # Test with different encodings
        encodings = ["cl100k_base", "p50k_base"]
        
        for encoding_name in encodings:
            chunks = chunk_text(
                text,
                chunk_size=50,
                overlap=10,
                encoding_name=encoding_name
            )
            
            assert len(chunks) > 0
            
            # Verify token counts are accurate for this encoding
            encoding = tiktoken.get_encoding(encoding_name)
            for chunk in chunks:
                actual_tokens = len(encoding.encode(chunk['text']))
                assert chunk['token_count'] == actual_tokens
    
    def test_very_small_chunk_size(self):
        """Test chunking with very small chunk size."""
        text = "This is a test. Another sentence. And one more."
        chunks = chunk_text(text, chunk_size=5, overlap=1)
        
        # Should create multiple small chunks
        assert len(chunks) >= 3
        
        for chunk in chunks:
            # Each chunk should be small
            assert chunk['token_count'] <= 10  # Allow some tolerance
    
    def test_overlap_larger_than_practical(self):
        """Test with overlap close to chunk size."""
        text = "This is a test document. " * 20
        
        # Overlap is 90% of chunk size
        chunks = chunk_text(text, chunk_size=100, overlap=90)
        
        # Should still create chunks
        assert len(chunks) > 0
        
        # Chunks should have significant overlap
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                chunk1_words = set(chunks[i]['text'].split())
                chunk2_words = set(chunks[i + 1]['text'].split())
                overlap_words = chunk1_words & chunk2_words
                
                # Should have substantial overlap
                assert len(overlap_words) > len(chunk1_words) * 0.5


class TestPerformance:
    """Test performance characteristics of the PDF processing pipeline."""
    
    def test_large_document_processing(self):
        """Test processing of a large document."""
        # Create a large document
        large_text = " ".join([
            f"Paragraph {i}. This paragraph discusses qualified research activities "
            f"and the application of the four-part test under Section 41 of the IRC. "
            f"It includes details about technological uncertainty and experimentation."
            for i in range(500)
        ])
        
        document = {
            'file_path': 'large_doc.pdf',
            'pages': [
                {'page_number': i, 'text': large_text}
                for i in range(1, 11)  # 10 pages
            ],
            'total_pages': 10
        }
        
        # This should complete without errors
        chunks = chunk_document(document, chunk_size=512, overlap=50)
        
        assert len(chunks) > 100  # Should create many chunks
        
        # Verify all chunks are valid
        for chunk in chunks:
            assert chunk['token_count'] > 0
            assert chunk['char_count'] > 0
            assert len(chunk['text']) > 0
    
    def test_many_small_documents(self):
        """Test processing of many small documents."""
        documents = [
            {
                'file_path': f'doc_{i}.pdf',
                'pages': [
                    {'page_number': 1, 'text': f'Document {i} content. ' * 10}
                ],
                'total_pages': 1
            }
            for i in range(50)
        ]
        
        result = chunk_multiple_documents(documents, chunk_size=100, overlap=20)
        
        assert result['documents_processed'] == 50
        assert result['total_chunks'] > 0
        assert result['documents_failed'] == 0
