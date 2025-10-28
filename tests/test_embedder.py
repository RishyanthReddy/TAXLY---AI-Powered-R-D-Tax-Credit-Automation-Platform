"""
Unit tests for the Embedder class.

Tests cover:
- Single text encoding
- Batch text encoding
- Caching functionality
- Error handling
- Embedding dimensions
"""

import pytest
import numpy as np
from tools.embedder import Embedder


class TestEmbedderInitialization:
    """Tests for Embedder initialization"""
    
    def test_default_initialization(self):
        """Test initialization with default model"""
        embedder = Embedder()
        assert embedder.model_name == 'all-MiniLM-L6-v2'
        assert embedder.model is not None
        assert embedder.embedding_dim == 384  # all-MiniLM-L6-v2 produces 384-dim embeddings
        assert isinstance(embedder.cache, dict)
        assert len(embedder.cache) == 0
    
    def test_custom_model_initialization(self):
        """Test initialization with custom model name"""
        # Using the same model but verifying the parameter works
        embedder = Embedder(model_name='all-MiniLM-L6-v2')
        assert embedder.model_name == 'all-MiniLM-L6-v2'
        assert embedder.model is not None
    
    def test_get_embedding_dimension(self):
        """Test getting embedding dimension"""
        embedder = Embedder()
        dim = embedder.get_embedding_dimension()
        assert dim == 384
        assert isinstance(dim, int)


class TestSingleTextEncoding:
    """Tests for encoding single texts"""
    
    def test_encode_simple_text(self):
        """Test encoding a simple text"""
        embedder = Embedder()
        text = "This is a test sentence."
        embedding = embedder.encode_text(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert not np.all(embedding == 0)  # Embedding should not be all zeros
    
    def test_encode_empty_text_raises_error(self):
        """Test that encoding empty text raises ValueError"""
        embedder = Embedder()
        
        with pytest.raises(ValueError, match="Text must be a non-empty string"):
            embedder.encode_text("")
    
    def test_encode_none_raises_error(self):
        """Test that encoding None raises ValueError"""
        embedder = Embedder()
        
        with pytest.raises(ValueError, match="Text must be a non-empty string"):
            embedder.encode_text(None)
    
    def test_encode_different_texts_produce_different_embeddings(self):
        """Test that different texts produce different embeddings"""
        embedder = Embedder()
        
        text1 = "Software development"
        text2 = "Accounting procedures"
        
        emb1 = embedder.encode_text(text1)
        emb2 = embedder.encode_text(text2)
        
        assert not np.array_equal(emb1, emb2)
    
    def test_encode_same_text_produces_same_embedding(self):
        """Test that encoding the same text twice produces identical embeddings"""
        embedder = Embedder()
        text = "Consistent text for testing"
        
        emb1 = embedder.encode_text(text, use_cache=False)
        emb2 = embedder.encode_text(text, use_cache=False)
        
        # Should be very close (allowing for floating point precision)
        assert np.allclose(emb1, emb2, rtol=1e-5)


class TestBatchEncoding:
    """Tests for batch text encoding"""
    
    def test_encode_batch_simple(self):
        """Test encoding a batch of texts"""
        embedder = Embedder()
        texts = [
            "First text",
            "Second text",
            "Third text"
        ]
        
        embeddings = embedder.encode_batch(texts)
        
        assert len(embeddings) == 3
        assert all(isinstance(emb, np.ndarray) for emb in embeddings)
        assert all(emb.shape == (384,) for emb in embeddings)
    
    def test_encode_batch_empty_list_raises_error(self):
        """Test that encoding empty list raises ValueError"""
        embedder = Embedder()
        
        with pytest.raises(ValueError, match="Texts must be a non-empty list"):
            embedder.encode_batch([])
    
    def test_encode_batch_with_empty_string_raises_error(self):
        """Test that batch with empty string raises ValueError"""
        embedder = Embedder()
        texts = ["Valid text", "", "Another valid text"]
        
        with pytest.raises(ValueError, match="All texts must be non-empty strings"):
            embedder.encode_batch(texts)
    
    def test_encode_batch_preserves_order(self):
        """Test that batch encoding preserves input order"""
        embedder = Embedder()
        texts = ["Text A", "Text B", "Text C"]
        
        # Encode individually
        individual_embeddings = [embedder.encode_text(t, use_cache=False) for t in texts]
        
        # Clear cache and encode as batch
        embedder.clear_cache()
        batch_embeddings = embedder.encode_batch(texts, use_cache=False)
        
        # Compare
        for ind_emb, batch_emb in zip(individual_embeddings, batch_embeddings):
            assert np.allclose(ind_emb, batch_emb, rtol=1e-5)
    
    def test_encode_batch_with_custom_batch_size(self):
        """Test batch encoding with custom batch size"""
        embedder = Embedder()
        texts = [f"Text number {i}" for i in range(10)]
        
        embeddings = embedder.encode_batch(texts, batch_size=2)
        
        assert len(embeddings) == 10
        assert all(emb.shape == (384,) for emb in embeddings)


class TestCaching:
    """Tests for caching functionality"""
    
    def test_cache_stores_embedding(self):
        """Test that cache stores embeddings"""
        embedder = Embedder()
        text = "Text to cache"
        
        assert embedder.get_cache_size() == 0
        
        embedder.encode_text(text)
        
        assert embedder.get_cache_size() == 1
    
    def test_cache_retrieves_same_embedding(self):
        """Test that cache returns the same embedding object"""
        embedder = Embedder()
        text = "Cached text"
        
        # First encoding
        emb1 = embedder.encode_text(text)
        
        # Second encoding (should use cache)
        emb2 = embedder.encode_text(text)
        
        # Should be the exact same object from cache
        assert np.array_equal(emb1, emb2)
        assert embedder.get_cache_size() == 1
    
    def test_cache_disabled(self):
        """Test encoding with cache disabled"""
        embedder = Embedder()
        text = "No cache text"
        
        emb1 = embedder.encode_text(text, use_cache=False)
        assert embedder.get_cache_size() == 0
        
        emb2 = embedder.encode_text(text, use_cache=False)
        assert embedder.get_cache_size() == 0
        
        # Embeddings should still be the same
        assert np.allclose(emb1, emb2, rtol=1e-5)
    
    def test_clear_cache(self):
        """Test clearing the cache"""
        embedder = Embedder()
        
        # Add some embeddings to cache
        texts = ["Text 1", "Text 2", "Text 3"]
        for text in texts:
            embedder.encode_text(text)
        
        assert embedder.get_cache_size() == 3
        
        # Clear cache
        cleared = embedder.clear_cache()
        
        assert cleared == 3
        assert embedder.get_cache_size() == 0
    
    def test_batch_encoding_uses_cache(self):
        """Test that batch encoding uses cached embeddings"""
        embedder = Embedder()
        
        texts = ["Text A", "Text B", "Text C"]
        
        # Encode first two texts individually
        embedder.encode_text(texts[0])
        embedder.encode_text(texts[1])
        
        assert embedder.get_cache_size() == 2
        
        # Encode all three as batch (should use cache for first two)
        embeddings = embedder.encode_batch(texts)
        
        assert len(embeddings) == 3
        assert embedder.get_cache_size() == 3  # Third text now cached
    
    def test_batch_encoding_cache_disabled(self):
        """Test batch encoding with cache disabled"""
        embedder = Embedder()
        
        texts = ["Text 1", "Text 2"]
        
        embeddings = embedder.encode_batch(texts, use_cache=False)
        
        assert len(embeddings) == 2
        assert embedder.get_cache_size() == 0


class TestCacheKeyGeneration:
    """Tests for cache key generation"""
    
    def test_same_text_same_cache_key(self):
        """Test that same text produces same cache key"""
        embedder = Embedder()
        text = "Test text"
        
        key1 = embedder._get_cache_key(text)
        key2 = embedder._get_cache_key(text)
        
        assert key1 == key2
    
    def test_different_text_different_cache_key(self):
        """Test that different texts produce different cache keys"""
        embedder = Embedder()
        
        key1 = embedder._get_cache_key("Text A")
        key2 = embedder._get_cache_key("Text B")
        
        assert key1 != key2
    
    def test_cache_key_is_string(self):
        """Test that cache key is a string"""
        embedder = Embedder()
        key = embedder._get_cache_key("Test")
        
        assert isinstance(key, str)
        assert len(key) == 64  # SHA-256 produces 64 character hex string


class TestEmbeddingSimilarity:
    """Tests for embedding similarity properties"""
    
    def test_similar_texts_have_high_similarity(self):
        """Test that similar texts produce similar embeddings"""
        embedder = Embedder()
        
        text1 = "Software development for machine learning"
        text2 = "Machine learning software development"
        
        emb1 = embedder.encode_text(text1)
        emb2 = embedder.encode_text(text2)
        
        # Calculate cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        
        # Similar texts should have high similarity (> 0.7)
        assert similarity > 0.7
    
    def test_dissimilar_texts_have_low_similarity(self):
        """Test that dissimilar texts produce dissimilar embeddings"""
        embedder = Embedder()
        
        text1 = "Software development activities"
        text2 = "Cooking recipes and ingredients"
        
        emb1 = embedder.encode_text(text1)
        emb2 = embedder.encode_text(text2)
        
        # Calculate cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        
        # Dissimilar texts should have lower similarity
        assert similarity < 0.7


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""
    
    def test_encode_very_long_text(self):
        """Test encoding very long text"""
        embedder = Embedder()
        
        # Create a long text
        long_text = " ".join(["word"] * 1000)
        
        embedding = embedder.encode_text(long_text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
    
    def test_encode_text_with_special_characters(self):
        """Test encoding text with special characters"""
        embedder = Embedder()
        
        text = "Text with special chars: @#$%^&*()_+-=[]{}|;:',.<>?/~`"
        
        embedding = embedder.encode_text(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
    
    def test_encode_text_with_unicode(self):
        """Test encoding text with unicode characters"""
        embedder = Embedder()
        
        text = "Text with unicode: café, naïve, 日本語, 中文"
        
        embedding = embedder.encode_text(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
    
    def test_encode_single_word(self):
        """Test encoding a single word"""
        embedder = Embedder()
        
        embedding = embedder.encode_text("word")
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)


class TestIntegration:
    """Integration tests for realistic usage scenarios"""
    
    def test_irs_document_chunk_encoding(self):
        """Test encoding IRS document chunks for RAG system"""
        embedder = Embedder()
        
        # Simulate IRS document chunks
        chunks = [
            "The four-part test requires technological uncertainty.",
            "Qualified research expenses include employee wages.",
            "Software development may qualify under certain conditions.",
            "The process of experimentation must be documented."
        ]
        
        embeddings = embedder.encode_batch(chunks)
        
        assert len(embeddings) == 4
        assert all(emb.shape == (384,) for emb in embeddings)
        assert embedder.get_cache_size() == 4
    
    def test_query_and_retrieval_simulation(self):
        """Test simulating a query against cached document embeddings"""
        embedder = Embedder()
        
        # Encode document chunks
        documents = [
            "Software development activities for R&D",
            "Accounting and bookkeeping procedures",
            "Research into new algorithms"
        ]
        
        doc_embeddings = embedder.encode_batch(documents)
        
        # Encode query
        query = "What qualifies as R&D software development?"
        query_embedding = embedder.encode_text(query)
        
        # Calculate similarities
        similarities = []
        for doc_emb in doc_embeddings:
            sim = np.dot(query_embedding, doc_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb)
            )
            similarities.append(sim)
        
        # Most relevant should be the first document
        most_relevant_idx = np.argmax(similarities)
        assert most_relevant_idx == 0 or most_relevant_idx == 2  # Either R&D related doc
