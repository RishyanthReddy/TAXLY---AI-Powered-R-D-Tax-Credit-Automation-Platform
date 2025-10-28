"""
Embedder Usage Examples

This script demonstrates how to use the Embedder class for generating
text embeddings with caching support.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.embedder import Embedder
import numpy as np


def example_single_text_encoding():
    """Example: Encode a single text"""
    print("=" * 60)
    print("Example 1: Single Text Encoding")
    print("=" * 60)
    
    embedder = Embedder()
    
    text = "This is a sample text for R&D tax credit qualification."
    embedding = embedder.encode_text(text)
    
    print(f"Text: {text}")
    print(f"Embedding shape: {embedding.shape}")
    print(f"Embedding dimension: {embedder.get_embedding_dimension()}")
    print(f"First 5 values: {embedding[:5]}")
    print()


def example_batch_encoding():
    """Example: Encode multiple texts in batch"""
    print("=" * 60)
    print("Example 2: Batch Text Encoding")
    print("=" * 60)
    
    embedder = Embedder()
    
    texts = [
        "Software development activities for new features",
        "Research into machine learning algorithms",
        "Experimental testing of database optimization techniques",
        "Development of novel API architecture"
    ]
    
    embeddings = embedder.encode_batch(texts)
    
    print(f"Number of texts: {len(texts)}")
    print(f"Number of embeddings: {len(embeddings)}")
    print(f"Each embedding shape: {embeddings[0].shape}")
    print()
    
    for i, (text, embedding) in enumerate(zip(texts, embeddings)):
        print(f"Text {i+1}: {text[:50]}...")
        print(f"  Embedding norm: {np.linalg.norm(embedding):.4f}")
    print()


def example_caching():
    """Example: Demonstrate caching functionality"""
    print("=" * 60)
    print("Example 3: Caching Demonstration")
    print("=" * 60)
    
    embedder = Embedder()
    
    text = "This text will be cached"
    
    # First encoding (not cached)
    print("First encoding (not cached):")
    embedding1 = embedder.encode_text(text)
    print(f"Cache size after first encoding: {embedder.get_cache_size()}")
    
    # Second encoding (cached)
    print("\nSecond encoding (should use cache):")
    embedding2 = embedder.encode_text(text)
    print(f"Cache size after second encoding: {embedder.get_cache_size()}")
    
    # Verify embeddings are identical
    print(f"\nEmbeddings are identical: {np.array_equal(embedding1, embedding2)}")
    
    # Clear cache
    cleared = embedder.clear_cache()
    print(f"\nCleared {cleared} cached embeddings")
    print(f"Cache size after clearing: {embedder.get_cache_size()}")
    print()


def example_similarity_calculation():
    """Example: Calculate similarity between texts"""
    print("=" * 60)
    print("Example 4: Text Similarity Calculation")
    print("=" * 60)
    
    embedder = Embedder()
    
    # Similar texts
    text1 = "Software development for machine learning applications"
    text2 = "Developing machine learning software solutions"
    
    # Different text
    text3 = "Accounting and financial reporting procedures"
    
    # Encode texts
    emb1 = embedder.encode_text(text1)
    emb2 = embedder.encode_text(text2)
    emb3 = embedder.encode_text(text3)
    
    # Calculate cosine similarity
    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    sim_1_2 = cosine_similarity(emb1, emb2)
    sim_1_3 = cosine_similarity(emb1, emb3)
    
    print(f"Text 1: {text1}")
    print(f"Text 2: {text2}")
    print(f"Text 3: {text3}")
    print()
    print(f"Similarity between Text 1 and Text 2: {sim_1_2:.4f}")
    print(f"Similarity between Text 1 and Text 3: {sim_1_3:.4f}")
    print()
    print("Note: Higher similarity score indicates more similar texts")
    print()


def example_irs_document_chunks():
    """Example: Encode IRS document chunks for RAG"""
    print("=" * 60)
    print("Example 5: IRS Document Chunks for RAG")
    print("=" * 60)
    
    embedder = Embedder()
    
    # Simulated IRS document chunks
    irs_chunks = [
        "The four-part test requires that activities be technological in nature.",
        "Qualified research expenses include wages paid to employees performing qualified services.",
        "The process of experimentation must fundamentally rely on principles of physical or biological sciences.",
        "Software development may qualify if it involves uncertainty about capability or method."
    ]
    
    print("Encoding IRS document chunks for vector database...")
    embeddings = embedder.encode_batch(irs_chunks, show_progress_bar=False)
    
    print(f"\nEncoded {len(embeddings)} chunks")
    print(f"Embedding dimension: {embeddings[0].shape[0]}")
    print(f"Cache size: {embedder.get_cache_size()}")
    print()
    
    # Simulate a query
    query = "What are the requirements for software development to qualify?"
    query_embedding = embedder.encode_text(query)
    
    print(f"Query: {query}")
    print("\nFinding most relevant chunks...")
    
    # Calculate similarities
    similarities = []
    for i, chunk_emb in enumerate(embeddings):
        sim = np.dot(query_embedding, chunk_emb) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(chunk_emb)
        )
        similarities.append((i, sim))
    
    # Sort by similarity
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    print("\nTop 3 most relevant chunks:")
    for rank, (idx, sim) in enumerate(similarities[:3], 1):
        print(f"\n{rank}. Similarity: {sim:.4f}")
        print(f"   Chunk: {irs_chunks[idx]}")
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("EMBEDDER USAGE EXAMPLES")
    print("=" * 60 + "\n")
    
    example_single_text_encoding()
    example_batch_encoding()
    example_caching()
    example_similarity_calculation()
    example_irs_document_chunks()
    
    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
