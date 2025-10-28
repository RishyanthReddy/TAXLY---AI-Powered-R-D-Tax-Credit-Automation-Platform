# Document Indexing Pipeline

## Overview

The Document Indexing Pipeline orchestrates the complete process of indexing IRS tax documents for the RAG (Retrieval-Augmented Generation) system. It extracts text from PDFs, chunks the text with overlap, generates embeddings, and stores them in ChromaDB.

## Features

- **Automated Pipeline**: Single function call to index all documents
- **Progress Tracking**: Detailed logging of each step
- **Error Handling**: Continues processing even if some documents fail
- **Metadata Management**: Automatically updates metadata.json with indexing status
- **Flexible Configuration**: Customizable chunk size, overlap, and embedding model
- **Force Reindex**: Option to reindex already-indexed documents
- **Status Checking**: Query current indexing status

## Architecture

The pipeline consists of four main steps:

```
1. Text Extraction (pdf_extractor.py)
   ↓
2. Text Chunking (text_chunker.py)
   ↓
3. Embedding Generation (embedder.py)
   ↓
4. Vector Storage (vector_db.py)
```

## Usage

### Basic Usage

```python
from tools.indexing_pipeline import index_documents

# Index all documents in knowledge base
results = index_documents()

print(f"Indexed {results['documents_indexed']} documents")
print(f"Created {results['total_chunks']} chunks")
```

### Custom Configuration

```python
# Index with custom parameters
results = index_documents(
    knowledge_base_path="./knowledge_base",
    chunk_size=1024,           # Larger chunks for more context
    overlap=100,               # More overlap to preserve context
    embedding_model="all-MiniLM-L6-v2",
    force_reindex=False        # Skip already indexed documents
)
```

### Force Reindex

```python
# Reindex all documents (even if already indexed)
results = index_documents(force_reindex=True)
```

### Check Indexing Status

```python
from tools.indexing_pipeline import get_indexing_status

status = get_indexing_status()
print(f"Indexed: {status['indexed_documents']}/{status['total_documents']}")

for doc in status['documents']:
    if doc['indexed']:
        print(f"✓ {doc['filename']} ({doc['chunk_count']} chunks)")
    else:
        print(f"✗ {doc['filename']} (not indexed)")
```

## Function Reference

### `index_documents()`

Main function to orchestrate the full indexing pipeline.

**Parameters:**
- `knowledge_base_path` (str): Path to knowledge base directory. Default: `"./knowledge_base"`
- `chunk_size` (int): Target size of each chunk in tokens. Default: `512`
- `overlap` (int): Number of tokens to overlap between chunks. Default: `50`
- `embedding_model` (str): SentenceTransformer model name. Default: `"all-MiniLM-L6-v2"`
- `force_reindex` (bool): If True, reindex even if already indexed. Default: `False`

**Returns:**
Dictionary containing:
- `total_documents`: Total number of documents found
- `documents_indexed`: Number of documents successfully indexed
- `documents_skipped`: Number of documents skipped (already indexed)
- `documents_failed`: Number of documents that failed
- `total_chunks`: Total number of chunks created
- `total_embeddings`: Total number of embeddings generated
- `errors`: List of error messages for failed documents
- `duration_seconds`: Total time taken for indexing

**Example:**
```python
results = index_documents(
    chunk_size=512,
    overlap=50,
    force_reindex=False
)
```

### `index_single_document()`

Index a single document through the complete pipeline.

**Parameters:**
- `doc_metadata` (Dict): Document metadata from metadata.json
- `tax_docs_path` (Path): Path to tax_docs directory
- `vector_db` (VectorDB): Initialized VectorDB instance
- `embedder` (Embedder): Initialized Embedder instance
- `chunk_size` (int): Target chunk size in tokens
- `overlap` (int): Overlap between chunks in tokens

**Returns:**
Dictionary containing:
- `chunk_count`: Number of chunks created
- `embedding_count`: Number of embeddings generated
- `document_id`: Document ID

### `get_indexing_status()`

Get the current indexing status from metadata.json.

**Parameters:**
- `knowledge_base_path` (str): Path to knowledge base directory. Default: `"./knowledge_base"`

**Returns:**
Dictionary containing:
- `total_documents`: Total number of documents
- `indexed_documents`: Number of indexed documents
- `unindexed_documents`: Number of unindexed documents
- `documents`: List of document statuses

**Example:**
```python
status = get_indexing_status()
print(f"Progress: {status['indexed_documents']}/{status['total_documents']}")
```

## Pipeline Steps

### Step 1: Text Extraction

Extracts text from PDF files or reads text files directly.

- Uses `pypdf` for PDF extraction
- Preserves formatting (headings, lists)
- Tracks page numbers
- Handles both PDF and text files

### Step 2: Text Chunking

Splits text into token-sized segments with overlap.

- Uses `tiktoken` for accurate token counting
- Preserves sentence boundaries
- Configurable chunk size and overlap
- Maintains metadata (source, page, position)

### Step 3: Embedding Generation

Generates dense vector embeddings for each chunk.

- Uses SentenceTransformer models
- Batch processing for efficiency
- Caching to avoid recomputation
- 384-dimensional embeddings (all-MiniLM-L6-v2)

### Step 4: Vector Storage

Stores embeddings and metadata in ChromaDB.

- Persistent storage
- Cosine similarity metric
- Metadata filtering support
- Efficient similarity search

## Configuration

### Chunk Size

The `chunk_size` parameter controls how large each text chunk should be:

- **Small chunks (256-512 tokens)**: More precise retrieval, but less context
- **Medium chunks (512-1024 tokens)**: Balanced precision and context
- **Large chunks (1024-2048 tokens)**: More context, but less precise

**Recommendation**: Use 512 tokens for most use cases.

### Overlap

The `overlap` parameter controls how much text is shared between consecutive chunks:

- **Small overlap (25-50 tokens)**: Less redundancy, faster indexing
- **Medium overlap (50-100 tokens)**: Good context preservation
- **Large overlap (100-200 tokens)**: Maximum context, but more storage

**Recommendation**: Use 50 tokens for most use cases.

### Embedding Model

The `embedding_model` parameter specifies which SentenceTransformer model to use:

- **all-MiniLM-L6-v2** (default): Fast, 384 dimensions, good quality
- **all-mpnet-base-v2**: Slower, 768 dimensions, higher quality
- **multi-qa-MiniLM-L6-cos-v1**: Optimized for question-answering

**Recommendation**: Use all-MiniLM-L6-v2 for speed and efficiency.

## Logging

The pipeline provides detailed logging at each step:

```
INFO - Starting Document Indexing Pipeline
INFO - Knowledge base path: ./knowledge_base
INFO - Chunk size: 512 tokens
INFO - Overlap: 50 tokens
INFO - Loaded metadata for 4 documents
INFO - Initializing indexing components...
INFO - Components initialized successfully
INFO - Processing document: CFR-2012-title26-vol1-sec1-41-4.pdf
INFO - Step 1/4: Extracting text from CFR-2012-title26-vol1-sec1-41-4.pdf
INFO - Extracted 15234 characters from 8 pages
INFO - Step 2/4: Chunking text (chunk_size=512, overlap=50)
INFO - Created 42 chunks
INFO - Step 3/4: Generating embeddings for 42 chunks
INFO - Generated 42 embeddings
INFO - Step 4/4: Storing 42 chunks in vector database
INFO - Successfully stored 42 chunks in vector database
INFO - Successfully indexed CFR-2012-title26-vol1-sec1-41-4.pdf: 42 chunks, 42 embeddings
...
INFO - Indexing Pipeline Complete
INFO - Total documents: 4
INFO - Documents indexed: 4
INFO - Documents skipped: 0
INFO - Documents failed: 0
INFO - Total chunks created: 156
INFO - Total embeddings generated: 156
INFO - Duration: 45.23 seconds
```

## Error Handling

The pipeline handles errors gracefully:

- **PDF Extraction Errors**: Logs error and continues with next document
- **Chunking Errors**: Logs error and continues with next document
- **Embedding Errors**: Logs error and continues with next document
- **Vector DB Errors**: Logs error and continues with next document

All errors are collected in the `errors` list in the results dictionary.

## Metadata Updates

After indexing, the pipeline updates `metadata.json` with:

- `indexed`: Boolean indicating if document is indexed
- `index_date`: ISO timestamp of when indexing occurred
- `chunk_count`: Number of chunks created for this document
- `last_updated`: ISO timestamp of metadata update

Example:
```json
{
  "id": "cfr-title-26-sec-1-41-4",
  "filename": "CFR-2012-title26-vol1-sec1-41-4.pdf",
  "indexed": true,
  "index_date": "2025-10-28T16:30:00.123456",
  "chunk_count": 42
}
```

## Performance

Typical performance on a modern laptop:

- **Text Extraction**: ~1-2 seconds per document
- **Chunking**: ~0.5-1 second per document
- **Embedding Generation**: ~5-10 seconds per 100 chunks
- **Vector Storage**: ~1-2 seconds per 100 chunks

**Total**: ~10-15 seconds per document (depending on size)

## Troubleshooting

### Issue: "Knowledge base path not found"

**Solution**: Ensure the knowledge base directory exists:
```bash
mkdir -p knowledge_base/tax_docs
mkdir -p knowledge_base/indexed
```

### Issue: "Failed to load metadata.json"

**Solution**: Ensure metadata.json exists and is valid JSON:
```bash
cat knowledge_base/metadata.json
```

### Issue: "No documents to index"

**Solution**: Check that PDF files exist in `knowledge_base/tax_docs/`:
```bash
ls knowledge_base/tax_docs/
```

### Issue: "ChromaDB initialization failed"

**Solution**: Ensure the indexed directory is writable:
```bash
chmod -R 755 knowledge_base/indexed
```

### Issue: "Out of memory during embedding generation"

**Solution**: Reduce batch size in embedder.py or process documents one at a time.

## Requirements

- Python 3.8+
- pypdf
- tiktoken
- sentence-transformers
- chromadb
- numpy

## Related Modules

- `pdf_extractor.py`: PDF text extraction
- `text_chunker.py`: Text chunking with overlap
- `embedder.py`: Embedding generation
- `vector_db.py`: ChromaDB vector database

## Examples

See `examples/indexing_pipeline_usage_example.py` for complete usage examples.
