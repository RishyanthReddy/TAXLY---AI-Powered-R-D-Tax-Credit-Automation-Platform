# RD_Knowledge_Tool

## Overview

The `RD_Knowledge_Tool` is a RAG (Retrieval-Augmented Generation) knowledge tool that provides access to IRS document guidance for R&D tax credit qualification decisions. It queries a vector database of indexed IRS documents and returns relevant context with citations and relevance scores.

## Features

- **Natural Language Queries**: Query the knowledge base using plain English questions
- **Relevance Scoring**: Each retrieved chunk includes a relevance score (0-1)
- **Structured Results**: Returns `RAGContext` objects with metadata and citations
- **Metadata Filtering**: Filter results by document source
- **LLM-Ready Formatting**: Format retrieved context for LLM prompts
- **Citation Extraction**: Extract unique citations for audit trails

## Installation

The tool requires the following dependencies:
- `chromadb`: Vector database
- `sentence-transformers`: Embedding model
- `pydantic`: Data validation

These are included in the project's `requirements.txt`.

## Usage

### Basic Usage

```python
from tools.rd_knowledge_tool import RD_Knowledge_Tool

# Initialize the tool
tool = RD_Knowledge_Tool(
    knowledge_base_path="./knowledge_base/indexed",
    default_top_k=3
)

# Query the knowledge base
context = tool.query("What is the four-part test for qualified research?")

# Access results
print(f"Retrieved {context.chunk_count} chunks")
print(f"Average relevance: {context.average_relevance:.2f}")

# Iterate through chunks
for chunk in context.chunks:
    print(f"Source: {chunk['source']}, Page {chunk['page']}")
    print(f"Relevance: {chunk['relevance_score']:.2f}")
    print(f"Text: {chunk['text'][:200]}...")
```

### Custom Top-K

```python
# Retrieve more chunks
context = tool.query(
    "What are qualified research expenses?",
    top_k=5
)
```

### Metadata Filtering

```python
# Filter by document source
context = tool.query(
    "qualified research wages",
    top_k=5,
    metadata_filter={"source": "Form 6765 Instructions"}
)
```

### Format for LLM Prompts

```python
# Get formatted context for LLM
context = tool.query("process of experimentation", top_k=3)
formatted = context.format_for_llm_prompt()

# Use in LLM prompt
prompt = f"""
Based on the following IRS guidance:

{formatted}

Determine if the following project qualifies for R&D tax credit...
"""
```

### Extract Citations

```python
# Get unique citations for audit reports
context = tool.query("software development R&D", top_k=5)
citations = context.extract_citations()

for citation in citations:
    print(f"- {citation}")
# Output:
# - CFR Title 26 § 1.41-4(a)(1), Page 3
# - IRS Audit Guidelines for Software, Page 8
```

## RAGContext Object

The `query()` method returns a `RAGContext` object with the following attributes:

### Attributes

- `query` (str): The original query text
- `chunks` (List[Dict]): Retrieved chunks with metadata
- `retrieval_timestamp` (datetime): When the context was retrieved
- `total_chunks_available` (int): Total chunks in the knowledge base
- `retrieval_method` (str): Method used (e.g., "semantic_search")

### Computed Properties

- `chunk_count` (int): Number of chunks retrieved
- `average_relevance` (float): Average relevance score across chunks

### Methods

- `format_for_llm_prompt(max_chunks=None)`: Format context for LLM prompts
- `extract_citations()`: Extract unique source citations

## Chunk Structure

Each chunk in `context.chunks` has the following fields:

```python
{
    'text': str,              # The document text
    'source': str,            # Document source (e.g., "Form 6765 Instructions")
    'page': int,              # Page number
    'relevance_score': float  # Relevance score (0-1)
}
```

## Knowledge Base Information

```python
# Get information about the knowledge base
info = tool.get_knowledge_base_info()

print(f"Path: {info['path']}")
print(f"Total chunks: {info['total_chunks']}")
print(f"Collection: {info['collection_name']}")
print(f"Embedding model: {info['embedding_model']}")
```

## Error Handling

The tool raises `RAGRetrievalError` for database-related errors and `ValueError` for invalid inputs:

```python
from utils.exceptions import RAGRetrievalError

try:
    context = tool.query("my question", top_k=3)
except ValueError as e:
    print(f"Invalid input: {e}")
except RAGRetrievalError as e:
    print(f"Retrieval error: {e}")
```

## Performance Considerations

### Relevance Scores

- Relevance scores are calculated from cosine similarity distances
- Scores range from 0 (not relevant) to 1 (highly relevant)
- Chunks are automatically sorted by relevance (highest first)

### Query Optimization

- Use specific queries for better results
- Adjust `top_k` based on your needs (default: 3)
- Use metadata filters to narrow results to specific documents

### Caching

The underlying vector database uses persistent storage, so embeddings are cached between sessions.

## Integration with Qualification Agent

The RD_Knowledge_Tool is designed to be used by the Qualification Agent:

```python
# In Qualification Agent
tool = RD_Knowledge_Tool()

# For each project to qualify
context = tool.query(
    f"Does {project.description} qualify as R&D under the four-part test?",
    top_k=3
)

# Format context for LLM
formatted_context = context.format_for_llm_prompt()

# Send to LLM with project data
llm_prompt = f"""
{formatted_context}

Project: {project.name}
Description: {project.description}
Activities: {project.activities}

Based on the IRS guidance above, determine the qualification percentage...
"""

# Store citations in QualifiedProject
qualified_project = QualifiedProject(
    project_name=project.name,
    supporting_citation=context.chunks[0]['text'],
    irs_source=context.chunks[0]['source'],
    ...
)
```

## Testing

Run the tests with:

```bash
pytest tests/test_rd_knowledge_tool.py -v
```

## Example Script

See `examples/rd_knowledge_tool_usage_example.py` for a complete usage example.

## Requirements

- Python 3.8+
- ChromaDB vector database must be initialized and populated
- IRS documents must be indexed (see `tools/indexing_pipeline.py`)

## Related Modules

- `tools/vector_db.py`: Vector database wrapper
- `tools/embedder.py`: Text embedding generation
- `tools/indexing_pipeline.py`: Document indexing
- `models/tax_models.py`: RAGContext and related models
