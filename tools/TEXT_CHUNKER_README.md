# Text Chunker Module

## Overview

The `text_chunker.py` module provides functionality to split text into token-sized chunks with overlap for use in RAG (Retrieval-Augmented Generation) systems. It uses tiktoken for accurate token counting and preserves sentence boundaries to maintain context.

## Features

- **Accurate Token Counting**: Uses tiktoken library for precise token counting compatible with OpenAI models
- **Sentence Boundary Preservation**: Avoids splitting sentences mid-way to maintain context
- **Configurable Overlap**: Supports overlapping tokens between chunks to preserve context across boundaries
- **Metadata Tracking**: Attaches source document, page number, and position metadata to each chunk
- **PDF Integration**: Works seamlessly with the pdf_extractor module
- **Batch Processing**: Supports chunking multiple documents efficiently
- **Error Handling**: Graceful error handling with detailed logging

## Requirements

This module satisfies **Requirement 2.1** from the R&D Tax Credit Automation Agent specification.

## Installation

The required dependencies are already included in `requirements.txt`:

```
tiktoken==0.8.0
```

## Core Functions

### `chunk_text()`

Chunks text into token-sized segments with overlap.

**Parameters:**
- `text` (str): The text to chunk
- `chunk_size` (int, default=512): Target size of each chunk in tokens
- `overlap` (int, default=50): Number of tokens to overlap between chunks
- `source_document` (str, optional): Name of the source document for metadata
- `page_number` (int, optional): Page number in the source document
- `encoding_name` (str, default="cl100k_base"): Tiktoken encoding to use

**Returns:**
List of dictionaries, each containing:
- `text`: The chunk text
- `token_count`: Number of tokens in the chunk
- `char_count`: Number of characters in the chunk
- `chunk_index`: Index of this chunk (0-based)
- `source_document`: Source document name (if provided)
- `page_number`: Page number (if provided)
- `start_char`: Starting character position in original text
- `end_char`: Ending character position in original text

**Example:**
```python
from tools.text_chunker import chunk_text

text = "Your long text here..."
chunks = chunk_text(
    text,
    chunk_size=512,
    overlap=50,
    source_document="document.pdf",
    page_number=1
)

for chunk in chunks:
    print(f"Chunk {chunk['chunk_index']}: {chunk['token_count']} tokens")
```

### `chunk_document()`

Chunks a document extracted by `pdf_extractor.py`.

**Parameters:**
- `document` (dict): Document dictionary from `extract_text_from_pdf()`
- `chunk_size` (int, default=512): Target size of each chunk in tokens
- `overlap` (int, default=50): Number of tokens to overlap between chunks
- `encoding_name` (str, default="cl100k_base"): Tiktoken encoding to use

**Returns:**
List of chunk dictionaries with metadata

**Example:**
```python
from tools.pdf_extractor import extract_text_from_pdf
from tools.text_chunker import chunk_document

# Extract text from PDF
document = extract_text_from_pdf('knowledge_base/tax_docs/form_6765.pdf')

# Chunk the document
chunks = chunk_document(document, chunk_size=512, overlap=50)

print(f"Created {len(chunks)} chunks from {document['total_pages']} pages")
```

### `chunk_multiple_documents()`

Chunks multiple documents in batch.

**Parameters:**
- `documents` (list): List of document dictionaries from `extract_text_from_pdf()`
- `chunk_size` (int, default=512): Target size of each chunk in tokens
- `overlap` (int, default=50): Number of tokens to overlap between chunks
- `encoding_name` (str, default="cl100k_base"): Tiktoken encoding to use
- `continue_on_error` (bool, default=True): Continue processing if some documents fail

**Returns:**
Dictionary containing:
- `chunks`: List of all chunks from all documents
- `total_chunks`: Total number of chunks created
- `documents_processed`: Number of successfully processed documents
- `documents_failed`: Number of failed documents
- `errors`: List of error messages for failed documents

**Example:**
```python
from tools.pdf_extractor import extract_text_from_multiple_pdfs
from tools.text_chunker import chunk_multiple_documents

# Extract text from multiple PDFs
pdf_files = ['doc1.pdf', 'doc2.pdf', 'doc3.pdf']
extraction_result = extract_text_from_multiple_pdfs(pdf_files)

# Chunk all documents
chunking_result = chunk_multiple_documents(
    extraction_result['documents'],
    chunk_size=512,
    overlap=50
)

print(f"Created {chunking_result['total_chunks']} chunks")
print(f"Processed {chunking_result['documents_processed']} documents")
```

## Design Decisions

### Token Counting

We use tiktoken with the `cl100k_base` encoding (used by GPT-4 and GPT-3.5-turbo) for accurate token counting. This ensures chunks fit within LLM context windows.

### Sentence Boundary Preservation

The chunker attempts to split text at sentence boundaries rather than mid-sentence. This is achieved by:

1. Splitting text into sentences using regex patterns
2. Accumulating sentences until the chunk size is reached
3. Starting a new chunk at the next sentence boundary

This approach maintains semantic coherence within chunks.

### Overlap Strategy

Overlap between chunks helps preserve context across boundaries. The overlap is implemented by:

1. When creating a new chunk, including the last N tokens from the previous chunk
2. Selecting complete sentences that fit within the overlap token count
3. This ensures no information is lost at chunk boundaries

### Metadata Tracking

Each chunk includes comprehensive metadata:
- Source document path
- Page number (for PDF documents)
- Chunk index (sequential numbering)
- Character positions (start and end)
- Token and character counts

This metadata is essential for:
- Citation generation in RAG systems
- Debugging and validation
- Tracing chunks back to source documents

## Usage Patterns

### Pattern 1: Basic Text Chunking

```python
from tools.text_chunker import chunk_text

text = "Your text here..."
chunks = chunk_text(text, chunk_size=512, overlap=50)
```

### Pattern 2: PDF to Chunks Pipeline

```python
from tools.pdf_extractor import extract_text_from_pdf
from tools.text_chunker import chunk_document

# Extract and chunk in one pipeline
document = extract_text_from_pdf('document.pdf')
chunks = chunk_document(document)
```

### Pattern 3: Batch Processing

```python
from tools.pdf_extractor import extract_text_from_multiple_pdfs
from tools.text_chunker import chunk_multiple_documents

# Process multiple PDFs
pdf_files = ['doc1.pdf', 'doc2.pdf', 'doc3.pdf']
documents = extract_text_from_multiple_pdfs(pdf_files)
result = chunk_multiple_documents(documents['documents'])
```

### Pattern 4: RAG System Integration

```python
from tools.text_chunker import chunk_document
from tools.pdf_extractor import extract_text_from_pdf

# Prepare chunks for vector database
document = extract_text_from_pdf('irs_guidance.pdf')
chunks = chunk_document(document, chunk_size=512, overlap=50)

# Format for ChromaDB or similar
for chunk in chunks:
    vector_db.add(
        id=f"{chunk['source_document']}_p{chunk['page_number']}_c{chunk['chunk_index']}",
        text=chunk['text'],
        metadata={
            'source': chunk['source_document'],
            'page': chunk['page_number'],
            'tokens': chunk['token_count']
        }
    )
```

## Configuration Guidelines

### Chunk Size

- **Default: 512 tokens**
- **Small chunks (128-256 tokens)**: Better for precise retrieval, more chunks to manage
- **Medium chunks (512-1024 tokens)**: Balanced approach, good for most use cases
- **Large chunks (1024-2048 tokens)**: More context per chunk, fewer chunks, may exceed some model limits

### Overlap

- **Default: 50 tokens**
- **Small overlap (10-25 tokens)**: Minimal redundancy, risk of losing context at boundaries
- **Medium overlap (50-100 tokens)**: Good balance, recommended for most cases
- **Large overlap (100-200 tokens)**: Maximum context preservation, more redundancy

### Encoding

- **cl100k_base** (default): For GPT-4, GPT-3.5-turbo, text-embedding-ada-002
- **p50k_base**: For older GPT-3 models
- **r50k_base**: For older Codex models

## Error Handling

The module includes comprehensive error handling:

```python
from tools.text_chunker import chunk_text, TextChunkingError

try:
    chunks = chunk_text(text, chunk_size=512, overlap=50)
except ValueError as e:
    print(f"Invalid parameters: {e}")
except TextChunkingError as e:
    print(f"Chunking failed: {e}")
```

Common errors:
- `ValueError`: Invalid parameters (negative chunk_size, overlap >= chunk_size)
- `TextChunkingError`: Chunking process failed
- Empty text returns empty list (not an error)

## Performance Considerations

### Token Counting Performance

Token counting is the most expensive operation. For large documents:
- Expect ~1-2 seconds per 10,000 characters
- Token counting is cached within each chunk operation
- Consider batch processing for multiple documents

### Memory Usage

- Each chunk stores the full text plus metadata
- For a 100-page PDF with 512-token chunks, expect ~5-10 MB memory usage
- Use batch processing with `continue_on_error=True` for large document sets

### Optimization Tips

1. **Batch Processing**: Use `chunk_multiple_documents()` instead of looping
2. **Appropriate Chunk Size**: Larger chunks = fewer chunks = less overhead
3. **Reuse Encoding**: The encoding is initialized once per function call
4. **Stream Processing**: For very large documents, consider processing pages individually

## Testing

Comprehensive tests are available in `tests/test_text_chunker.py`:

```bash
# Run all tests
pytest tests/test_text_chunker.py -v

# Run specific test class
pytest tests/test_text_chunker.py::TestChunkText -v

# Run with coverage
pytest tests/test_text_chunker.py --cov=tools.text_chunker
```

Test coverage: **93%**

## Examples

See `examples/text_chunker_usage_example.py` for comprehensive usage examples including:
- Basic text chunking
- Chunking with metadata
- PDF document chunking
- Multiple document processing
- Overlap demonstration
- RAG pipeline preparation

Run examples:
```bash
cd rd_tax_agent
python examples/text_chunker_usage_example.py
```

## Integration with RAG System

The text chunker is designed to integrate seamlessly with the RAG (Retrieval-Augmented Generation) system:

1. **PDF Extraction** → `pdf_extractor.py`
2. **Text Chunking** → `text_chunker.py` (this module)
3. **Embedding Generation** → `embedder.py` (to be implemented)
4. **Vector Storage** → `vector_db.py` (to be implemented)
5. **Retrieval** → `rd_knowledge_tool.py` (to be implemented)

## Logging

The module uses Python's logging framework:

```python
import logging

# Configure logging level
logging.basicConfig(level=logging.INFO)

# The chunker will log:
# - INFO: Start/completion of chunking operations
# - DEBUG: Detailed chunk creation information
# - WARNING: Empty text or unusual conditions
# - ERROR: Chunking failures
```

## Future Enhancements

Potential improvements for future versions:
- Support for custom sentence splitting patterns
- Semantic chunking (split by topic/section)
- Adaptive chunk sizing based on content
- Parallel processing for large document sets
- Support for additional encodings
- Chunk quality metrics

## Support

For issues or questions:
1. Check the examples in `examples/text_chunker_usage_example.py`
2. Review test cases in `tests/test_text_chunker.py`
3. Check logs for detailed error messages
4. Refer to the main project documentation

## License

Part of the R&D Tax Credit Automation Agent project.
