# Embedder Module

## Overview

The Embedder module provides text embedding functionality using SentenceTransformer models. It converts text into dense vector representations (embeddings) that can be used for semantic search, similarity calculations, and RAG (Retrieval-Augmented Generation) systems.

## Features

- **Single Text Encoding**: Encode individual texts into embedding vectors
- **Batch Encoding**: Efficiently encode multiple texts at once
- **Intelligent Caching**: Automatically cache embeddings to avoid recomputation
- **Configurable Models**: Support for different SentenceTransformer models
- **High Performance**: Optimized for both single and batch operations

## Installation

The required dependencies are already included in `requirements.txt`:

```bash
pip install sentence-transformers==3.3.1
```

## Quick Start

```python
from tools.embedder import Embedder

# Initialize embedder
embedder = Embedder()

# Encode a single text
text = "Software development for R&D tax credit"
embedding = embedder.encode_text(text)
print(f"Embedding shape: {embedding.shape}")  # (384,)

# Encode multiple texts
texts = [
    "Research activities",
    "Development work",
    "Experimental testing"
]
embeddings = embedder.encode_batch(texts)
print(f"Generated {len(embeddings)} embeddings")
```

## API Reference

### Class: `Embedder`

Main class for generating text embeddings with caching support.

#### Constructor

```python
Embedder(model_name: str = 'all-MiniLM-L6-v2')
```

**Parameters:**
- `model_name` (str): Name of the SentenceTransformer model to use. Default is 'all-MiniLM-L6-v2' which produces 384-dimensional embeddings.

**Example:**
```python
embedder = Embedder()  # Uses default model
# or
embedder = Embedder(model_name='all-MiniLM-L6-v2')
```

#### Methods

##### `encode_text(text: str, use_cache: bool = True) -> np.ndarray`

Encode a single text into an embedding vector.

**Parameters:**
- `text` (str): The text to encode
- `use_cache` (bool): Whether to use cached embeddings if available. Default is True.

**Returns:**
- `np.ndarray`: The embedding vector as a numpy array

**Raises:**
- `ValueError`: If text is empty or None
- `Exception`: If encoding fails

**Example:**
```python
embedder = Embedder()
embedding = embedder.encode_text("Sample text")
print(f"Embedding dimension: {len(embedding)}")  # 384
```

##### `encode_batch(texts: List[str], use_cache: bool = True, batch_size: int = 32, show_progress_bar: bool = False) -> List[np.ndarray]`

Encode multiple texts into embedding vectors.

**Parameters:**
- `texts` (List[str]): List of texts to encode
- `use_cache` (bool): Whether to use cached embeddings if available. Default is True.
- `batch_size` (int): Batch size for encoding. Default is 32.
- `show_progress_bar` (bool): Whether to show a progress bar. Default is False.

**Returns:**
- `List[np.ndarray]`: List of embedding vectors, one per input text

**Raises:**
- `ValueError`: If texts is empty or contains invalid entries
- `Exception`: If encoding fails

**Example:**
```python
embedder = Embedder()
texts = ["Text 1", "Text 2", "Text 3"]
embeddings = embedder.encode_batch(texts, batch_size=16)
print(f"Generated {len(embeddings)} embeddings")
```

##### `clear_cache() -> int`

Clear the embedding cache.

**Returns:**
- `int`: Number of cached embeddings that were cleared

**Example:**
```python
embedder = Embedder()
embedder.encode_text("Test")
count = embedder.clear_cache()
print(f"Cleared {count} cached embeddings")
```

##### `get_cache_size() -> int`

Get the number of embeddings currently in cache.

**Returns:**
- `int`: Number of cached embeddings

**Example:**
```python
embedder = Embedder()
embedder.encode_text("Test")
print(f"Cache size: {embedder.get_cache_size()}")  # 1
```

##### `get_embedding_dimension() -> int`

Get the dimension of the embedding vectors.

**Returns:**
- `int`: Dimension of embedding vectors (384 for all-MiniLM-L6-v2)

**Example:**
```python
embedder = Embedder()
print(f"Embedding dimension: {embedder.get_embedding_dimension()}")  # 384
```

## Usage Examples

### Example 1: Basic Text Encoding

```python
from tools.embedder import Embedder

embedder = Embedder()

# Encode a single text
text = "This is a sample text for R&D tax credit qualification."
embedding = embedder.encode_text(text)

print(f"Text: {text}")
print(f"Embedding shape: {embedding.shape}")
print(f"First 5 values: {embedding[:5]}")
```

### Example 2: Batch Encoding

```python
from tools.embedder import Embedder

embedder = Embedder()

texts = [
    "Software development activities",
    "Research into machine learning",
    "Experimental database optimization",
    "Novel API architecture development"
]

embeddings = embedder.encode_batch(texts)

for i, (text, embedding) in enumerate(zip(texts, embeddings)):
    print(f"Text {i+1}: {text}")
    print(f"  Embedding shape: {embedding.shape}")
```

### Example 3: Caching Demonstration

```python
from tools.embedder import Embedder

embedder = Embedder()

text = "This text will be cached"

# First encoding (not cached)
embedding1 = embedder.encode_text(text)
print(f"Cache size: {embedder.get_cache_size()}")  # 1

# Second encoding (uses cache)
embedding2 = embedder.encode_text(text)
print(f"Cache size: {embedder.get_cache_size()}")  # Still 1

# Verify embeddings are identical
import numpy as np
print(f"Identical: {np.array_equal(embedding1, embedding2)}")  # True
```

### Example 4: Similarity Calculation

```python
from tools.embedder import Embedder
import numpy as np

embedder = Embedder()

# Similar texts
text1 = "Software development for machine learning"
text2 = "Developing machine learning software"

# Different text
text3 = "Accounting procedures"

# Encode texts
emb1 = embedder.encode_text(text1)
emb2 = embedder.encode_text(text2)
emb3 = embedder.encode_text(text3)

# Calculate cosine similarity
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

sim_1_2 = cosine_similarity(emb1, emb2)
sim_1_3 = cosine_similarity(emb1, emb3)

print(f"Similarity (text1, text2): {sim_1_2:.4f}")  # High similarity
print(f"Similarity (text1, text3): {sim_1_3:.4f}")  # Low similarity
```

### Example 5: RAG System Integration

```python
from tools.embedder import Embedder
import numpy as np

embedder = Embedder()

# Encode IRS document chunks
irs_chunks = [
    "The four-part test requires technological uncertainty.",
    "Qualified research expenses include employee wages.",
    "Software development may qualify under certain conditions.",
    "The process of experimentation must be documented."
]

chunk_embeddings = embedder.encode_batch(irs_chunks)

# Encode a query
query = "What are the requirements for software development?"
query_embedding = embedder.encode_text(query)

# Find most relevant chunks
similarities = []
for i, chunk_emb in enumerate(chunk_embeddings):
    sim = np.dot(query_embedding, chunk_emb) / (
        np.linalg.norm(query_embedding) * np.linalg.norm(chunk_emb)
    )
    similarities.append((i, sim))

# Sort by similarity
similarities.sort(key=lambda x: x[1], reverse=True)

print("Most relevant chunks:")
for rank, (idx, sim) in enumerate(similarities[:3], 1):
    print(f"{rank}. Similarity: {sim:.4f}")
    print(f"   {irs_chunks[idx]}")
```

## Model Information

### Default Model: all-MiniLM-L6-v2

- **Embedding Dimension**: 384
- **Max Sequence Length**: 256 tokens
- **Performance**: Fast inference, good quality embeddings
- **Use Case**: General-purpose semantic similarity

### Model Characteristics

- Produces normalized embeddings (unit vectors)
- Trained on large corpus of text pairs
- Optimized for semantic similarity tasks
- Suitable for RAG systems and document retrieval

## Performance Considerations

### Caching

The Embedder automatically caches embeddings to improve performance:

- **Cache Hit**: Returns cached embedding instantly (no computation)
- **Cache Miss**: Computes embedding and stores in cache
- **Memory Usage**: Each cached embedding uses ~1.5 KB (384 floats)

### Batch Processing

For encoding multiple texts:

- Use `encode_batch()` instead of multiple `encode_text()` calls
- Batch processing is significantly faster (up to 10x)
- Adjust `batch_size` parameter based on available memory

### Best Practices

1. **Reuse Embedder Instance**: Create one instance and reuse it
2. **Use Batch Encoding**: Process multiple texts together when possible
3. **Enable Caching**: Keep `use_cache=True` for repeated texts
4. **Clear Cache Periodically**: If memory is constrained, clear cache after processing

## Integration with RAG System

The Embedder is designed to work seamlessly with the RAG Knowledge Tool:

```python
from tools.embedder import Embedder
from tools.vector_db import VectorDB

# Initialize embedder
embedder = Embedder()

# Encode document chunks
chunks = ["chunk1", "chunk2", "chunk3"]
embeddings = embedder.encode_batch(chunks)

# Store in vector database
vector_db = VectorDB()
vector_db.add_documents(chunks, embeddings)

# Query
query = "sample query"
query_embedding = embedder.encode_text(query)
results = vector_db.search(query_embedding, top_k=3)
```

## Error Handling

The Embedder includes comprehensive error handling:

```python
from tools.embedder import Embedder

embedder = Embedder()

# Handle empty text
try:
    embedder.encode_text("")
except ValueError as e:
    print(f"Error: {e}")  # "Text must be a non-empty string"

# Handle invalid batch
try:
    embedder.encode_batch([])
except ValueError as e:
    print(f"Error: {e}")  # "Texts must be a non-empty list"
```

## Testing

Run the test suite:

```bash
# Run all embedder tests
pytest tests/test_embedder.py -v

# Run with coverage
pytest tests/test_embedder.py --cov=tools.embedder --cov-report=html
```

## Logging

The Embedder uses Python's logging module:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

from tools.embedder import Embedder
embedder = Embedder()
embedder.encode_text("Test")  # Will log debug messages
```

## Troubleshooting

### Issue: Model Download Fails

**Solution**: Ensure you have internet connection. The model will be downloaded on first use.

### Issue: Out of Memory

**Solution**: 
- Reduce `batch_size` parameter
- Clear cache more frequently
- Process texts in smaller batches

### Issue: Slow Performance

**Solution**:
- Use batch encoding instead of single text encoding
- Enable caching for repeated texts
- Consider using GPU if available (requires additional setup)

## Future Enhancements

Potential improvements for future versions:

- GPU acceleration support
- Persistent cache (disk-based)
- Support for additional embedding models
- Async encoding for concurrent operations
- Embedding compression for reduced memory usage

## References

- [SentenceTransformers Documentation](https://www.sbert.net/)
- [all-MiniLM-L6-v2 Model Card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [Semantic Search Guide](https://www.sbert.net/examples/applications/semantic-search/README.html)
