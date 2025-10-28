# RD_Knowledge_Tool

## Overview

The `RD_Knowledge_Tool` is a RAG (Retrieval-Augmented Generation) knowledge tool that provides access to IRS document guidance for R&D tax credit qualification decisions. It queries a vector database of indexed IRS documents and returns relevant context with citations and relevance scores.

## Features

- **Natural Language Queries**: Query the knowledge base using plain English questions
- **Query Optimization** (NEW): Advanced query processing for better retrieval
  - Query expansion with technical term synonyms
  - Query rewriting for improved semantic matching
  - Re-ranking based on metadata and source preference
  - Document source filtering
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

### Query Optimization (NEW)

The tool now includes advanced query optimization features that are enabled by default:

#### All Optimizations Enabled (Default)

```python
# Query with all optimizations (default behavior)
context = tool.query(
    "What is QRE?",
    top_k=3,
    enable_query_expansion=True,      # Expands abbreviations and technical terms
    enable_query_rewriting=True,      # Rewrites questions for better retrieval
    enable_reranking=True,            # Re-ranks results based on metadata
    source_preference="Form 6765"     # Boost results from preferred source
)

# Retrieval method shows which optimizations were used
print(context.retrieval_method)
# Output: "semantic_search+query_expansion+query_rewriting+metadata_reranking"
```

#### Query Expansion

Automatically expands technical terms and abbreviations:

```python
# "QRE" is expanded to "qualified research expenditure", "qualified research expense"
# "R&D" is expanded to "research and development", "research", "development"
context = tool.query("What is QRE?", enable_query_expansion=True)
```

#### Query Rewriting

Converts questions to declarative statements for better semantic matching:

```python
# "What is the four-part test?" -> "four-part test definition"
# "How does experimentation work?" -> "experimentation work process"
context = tool.query("What is the four-part test?", enable_query_rewriting=True)
```

#### Re-ranking with Source Preference

Boost results from authoritative or preferred sources:

```python
# Results from Form 6765 will be boosted in ranking
context = tool.query(
    "wage limitations",
    enable_reranking=True,
    source_preference="Form 6765"
)

# Check boost factors applied
for chunk in context.chunks:
    if 'boost_factors' in chunk:
        print(f"Boosts applied: {chunk['boost_factors']}")
        # Example: ['source_match:Form 6765', 'authoritative_source', 'substantial_content']
```

#### Disable Optimizations

For comparison or specific use cases, you can disable optimizations:

```python
# Query without any optimizations
context = tool.query(
    "qualified research",
    enable_query_expansion=False,
    enable_query_rewriting=False,
    enable_reranking=False
)

print(context.retrieval_method)
# Output: "semantic_search"
```

#### Testing Individual Optimization Methods

```python
# Test query expansion
expansions = tool._expand_query("What is QRE?")
print(f"Generated {len(expansions)} query variations")

# Test query rewriting
rewritten = tool._rewrite_query("What is the four-part test?")
print(f"Rewritten: {rewritten}")

# Test re-ranking
chunks = [...]  # Your chunks
reranked = tool._rerank_results(chunks, "query", source_preference="Form 6765")
```

### Format for LLM Prompts (Basic)

```python
# Get formatted context for LLM using RAGContext method
context = tool.query("process of experimentation", top_k=3)
formatted = context.format_for_llm_prompt()

# Use in LLM prompt
prompt = f"""
Based on the following IRS guidance:

{formatted}

Determine if the following project qualifies for R&D tax credit...
"""
```

### Format for LLM with Advanced Options (NEW)

The `format_for_llm()` method provides comprehensive formatting with additional features:

#### Basic Formatting

```python
# Query and format with all default options
context = tool.query("What is the four-part test?", top_k=3)
formatted = tool.format_for_llm(context)

# Output includes:
# - Structured header with query information
# - Relevance scores with quality indicators (Very High, High, Medium, Low)
# - Retrieval metadata (method, timestamp, average relevance)
# - Source citations for each excerpt
# - Formatted citations section
```

#### Control Relevance Scores

```python
# Include relevance scores (default: True)
formatted = tool.format_for_llm(
    context,
    include_relevance_scores=True
)
# Shows: "Relevance Score: 0.92 (Very High confidence)"

# Exclude relevance scores
formatted = tool.format_for_llm(
    context,
    include_relevance_scores=False
)
```

#### Control Metadata

```python
# Include retrieval metadata (default: True)
formatted = tool.format_for_llm(
    context,
    include_metadata=True
)
# Shows: Retrieval Method, Average Relevance, Retrieved At

# Exclude metadata for cleaner output
formatted = tool.format_for_llm(
    context,
    include_metadata=False
)
```

#### Limit Number of Chunks

```python
# Retrieve 5 chunks but only format top 2
context = tool.query("qualified research expenses", top_k=5)
formatted = tool.format_for_llm(
    context,
    max_chunks=2  # Only include top 2 most relevant chunks
)
```

#### Custom Prompt Templates

```python
# Define custom template with placeholders
custom_template = """
Based on the following IRS guidance:

{context}

Query: {query}
Number of excerpts: {chunk_count}

Please analyze the project for R&D qualification.

Sources:
{citations}
"""

# Format with custom template
formatted = tool.format_for_llm(
    context,
    prompt_template=custom_template
)
```

#### Comprehensive Example

```python
# Query with optimizations
context = tool.query(
    "What is QRE?",
    top_k=5,
    enable_query_expansion=True,
    enable_reranking=True,
    source_preference="Form 6765"
)

# Format with all options
formatted = tool.format_for_llm(
    context,
    include_relevance_scores=True,
    include_metadata=True,
    max_chunks=3
)

# Output structure:
# ======================================================================
# IRS GUIDANCE CONTEXT FOR R&D TAX CREDIT QUALIFICATION
# ======================================================================
# 
# Query: What is QRE?
# Retrieved: 3 relevant document excerpt(s)
# Retrieval Method: semantic_search+query_expansion+metadata_reranking
# Average Relevance: 0.87
# Retrieved At: 2024-03-15 14:30:00
# 
# ----------------------------------------------------------------------
# 
# EXCERPT #1
# Source: Form 6765 Instructions
# Page: 2
# Relevance Score: 0.92 (Very High confidence)
# 
# [Document text...]
# 
# ----------------------------------------------------------------------
# [Additional excerpts...]
# 
# ======================================================================
# CITATIONS
# ======================================================================
# 
# 1. Form 6765 Instructions, Page 2
# 2. CFR Title 26 § 1.41-4, Page 3
# 3. IRS Publication 542, Page 15
# 
# ======================================================================
# END IRS GUIDANCE CONTEXT
# ======================================================================
```

#### Empty Context Handling

```python
# If no relevant chunks are found
empty_context = RAGContext(
    query="nonexistent topic",
    chunks=[],
    retrieval_timestamp=datetime.now(),
    total_chunks_available=150
)

formatted = tool.format_for_llm(empty_context)
# Returns helpful message about no guidance found
# and suggests proceeding with lower confidence
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

## API Reference

### query() Method

The primary method for querying the knowledge base with natural language questions.

#### Signature

```python
def query(
    self,
    question: str,
    top_k: Optional[int] = None,
    metadata_filter: Optional[Dict[str, Any]] = None,
    enable_query_expansion: bool = True,
    enable_query_rewriting: bool = True,
    enable_reranking: bool = True,
    source_preference: Optional[str] = None
) -> RAGContext
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `question` | `str` | Required | Natural language question to query the knowledge base. Must be non-empty. |
| `top_k` | `Optional[int]` | `None` | Number of chunks to retrieve. If `None`, uses `default_top_k` (3). Must be ≥ 1. |
| `metadata_filter` | `Optional[Dict[str, Any]]` | `None` | Filter results by metadata. Example: `{"source": "Form 6765"}` |
| `enable_query_expansion` | `bool` | `True` | Enable query expansion with technical term synonyms. |
| `enable_query_rewriting` | `bool` | `True` | Enable query rewriting for better semantic matching. |
| `enable_reranking` | `bool` | `True` | Enable re-ranking based on metadata and source preference. |
| `source_preference` | `Optional[str]` | `None` | Preferred document source for boosting in re-ranking. Example: `"Form 6765"` |

#### Returns

Returns a `RAGContext` object with the following structure:

```python
RAGContext(
    query: str,                          # Original query text
    chunks: List[Dict[str, Any]],        # Retrieved chunks with metadata
    retrieval_timestamp: datetime,       # When context was retrieved
    total_chunks_available: int,         # Total chunks in knowledge base
    retrieval_method: str                # Method used (e.g., "semantic_search+query_expansion")
)
```

Each chunk in `chunks` has this structure:

```python
{
    'text': str,                # Document text content
    'source': str,              # Document source (e.g., "Form 6765 Instructions")
    'page': int,                # Page number in source document
    'relevance_score': float,   # Relevance score (0.0 to 1.0)
    'original_score': float,    # Original score before re-ranking (if re-ranking enabled)
    'boost_factors': List[str]  # Applied boost factors (if re-ranking enabled)
}
```

#### Raises

| Exception | When | Example |
|-----------|------|---------|
| `ValueError` | Invalid input parameters | Empty question, `top_k < 1` |
| `RAGRetrievalError` | Database connection failure | Vector DB not initialized |
| `RAGRetrievalError` | Query execution failure | All query variations failed |
| `RAGRetrievalError` | Unexpected errors | Unhandled exceptions during retrieval |

#### Examples

**Basic Query**

```python
from tools.rd_knowledge_tool import RD_Knowledge_Tool

tool = RD_Knowledge_Tool()

# Simple query with default settings
context = tool.query("What is the four-part test?")

print(f"Retrieved {context.chunk_count} chunks")
print(f"Average relevance: {context.average_relevance:.2f}")

# Access first chunk
if context.chunks:
    top_chunk = context.chunks[0]
    print(f"Top result from: {top_chunk['source']}, Page {top_chunk['page']}")
    print(f"Relevance: {top_chunk['relevance_score']:.2f}")
    print(f"Text: {top_chunk['text'][:200]}...")
```

**Query with Custom Top-K**

```python
# Retrieve more chunks for comprehensive context
context = tool.query(
    "What are qualified research expenses?",
    top_k=5
)

# Iterate through all chunks
for i, chunk in enumerate(context.chunks, 1):
    print(f"\nChunk {i}:")
    print(f"  Source: {chunk['source']}")
    print(f"  Relevance: {chunk['relevance_score']:.2f}")
```

**Query with Metadata Filtering**

```python
# Filter to specific document source
context = tool.query(
    "qualified research wages",
    top_k=5,
    metadata_filter={"source": "Form 6765 Instructions"}
)

# All results will be from Form 6765 Instructions only
for chunk in context.chunks:
    assert "Form 6765" in chunk['source']
```

**Query with Source Preference**

```python
# Boost results from authoritative source
context = tool.query(
    "wage limitations",
    top_k=5,
    enable_reranking=True,
    source_preference="Form 6765"
)

# Check which boost factors were applied
for chunk in context.chunks:
    if 'boost_factors' in chunk:
        print(f"Boosts: {chunk['boost_factors']}")
        # Example: ['source_match:Form 6765', 'authoritative_source']
```

**Query Without Optimizations**

```python
# Disable all optimizations for baseline comparison
context = tool.query(
    "qualified research",
    enable_query_expansion=False,
    enable_query_rewriting=False,
    enable_reranking=False
)

print(f"Retrieval method: {context.retrieval_method}")
# Output: "semantic_search"
```

**Query with All Features**

```python
# Comprehensive query with all features
context = tool.query(
    question="What is QRE?",
    top_k=5,
    metadata_filter={"source": "Form 6765"},
    enable_query_expansion=True,
    enable_query_rewriting=True,
    enable_reranking=True,
    source_preference="Form 6765"
)

print(f"Method: {context.retrieval_method}")
# Output: "semantic_search+query_expansion+query_rewriting+metadata_reranking"

print(f"Retrieved {context.chunk_count} chunks")
print(f"Average relevance: {context.average_relevance:.2f}")
```

### batch_query() Method

Query the knowledge base with multiple questions efficiently.

#### Signature

```python
def batch_query(
    self,
    questions: List[str],
    top_k: Optional[int] = None,
    metadata_filter: Optional[Dict[str, Any]] = None,
    enable_query_expansion: bool = True,
    enable_query_rewriting: bool = True,
    enable_reranking: bool = True,
    source_preference: Optional[str] = None,
    continue_on_error: bool = True
) -> Dict[str, Any]
```

#### Parameters

Same as `query()` method, plus:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `questions` | `List[str]` | Required | List of natural language questions to query. |
| `continue_on_error` | `bool` | `True` | If `True`, continues processing even if some queries fail. |

#### Returns

Returns a dictionary with batch processing results:

```python
{
    'results': List[Optional[RAGContext]],  # RAGContext for each question (None if failed)
    'questions': List[str],                 # Original list of questions
    'total_queries': int,                   # Total number of queries processed
    'successful_queries': int,              # Number of successful queries
    'failed_queries': int,                  # Number of failed queries
    'cache_hits': int,                      # Number of queries served from cache
    'cache_hit_rate': float,                # Cache hit rate percentage
    'success_rate': float,                  # Success rate percentage
    'errors': List[Dict[str, Any]]          # Error information for failed queries
}
```

#### Example

```python
# Batch query multiple questions
questions = [
    "What is the four-part test?",
    "What are qualified research expenses?",
    "What is a process of experimentation?"
]

batch_result = tool.batch_query(questions, top_k=3)

print(f"Processed {batch_result['successful_queries']}/{batch_result['total_queries']} queries")
print(f"Cache hits: {batch_result['cache_hits']} ({batch_result['cache_hit_rate']:.1f}%)")

# Access individual results
for question, context in zip(questions, batch_result['results']):
    if context is not None:
        print(f"\n{question}")
        print(f"  Retrieved {context.chunk_count} chunks")
        print(f"  Average relevance: {context.average_relevance:.2f}")
    else:
        print(f"\n{question}")
        print(f"  FAILED")

# Check errors
if batch_result['errors']:
    print("\nErrors:")
    for error in batch_result['errors']:
        print(f"  Question {error['question_index']}: {error['error']}")
```

### format_for_llm() Method

Format retrieved RAG context for LLM consumption with structured prompt template.

#### Signature

```python
def format_for_llm(
    self,
    context: RAGContext,
    include_relevance_scores: bool = True,
    include_metadata: bool = True,
    max_chunks: Optional[int] = None,
    prompt_template: Optional[str] = None
) -> str
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `context` | `RAGContext` | Required | The RAG context object containing retrieved chunks. |
| `include_relevance_scores` | `bool` | `True` | Include relevance scores with quality indicators. |
| `include_metadata` | `bool` | `True` | Include retrieval metadata (timestamp, method, etc.). |
| `max_chunks` | `Optional[int]` | `None` | Maximum number of chunks to include. If `None`, includes all. |
| `prompt_template` | `Optional[str]` | `None` | Custom prompt template with placeholders: `{context}`, `{query}`, `{chunk_count}`, `{citations}` |

#### Returns

Returns a formatted string ready for LLM consumption.

#### Example

```python
# Query and format
context = tool.query("What is the four-part test?", top_k=3)
formatted = tool.format_for_llm(context)

# Use in LLM prompt
llm_prompt = f"""
{formatted}

Based on the IRS guidance above, analyze the following project:

Project: AI-powered recommendation engine
Description: Developing novel machine learning algorithms...

Determine if this project qualifies for R&D tax credit.
"""
```

### Caching Methods

#### clear_cache()

Clear all cached query results.

```python
# Clear cache
count = tool.clear_cache()
print(f"Cleared {count} cached entries")
```

#### get_cache_stats()

Get statistics about the query cache.

```python
# Get cache statistics
stats = tool.get_cache_stats()
print(f"Cache enabled: {stats['enabled']}")
print(f"Cache size: {stats['size']}")
print(f"TTL: {stats['ttl_seconds']}s")
print(f"Oldest entry age: {stats['oldest_entry_age_seconds']:.1f}s")
```

### Information Methods

#### get_total_chunks()

Get the total number of chunks in the knowledge base.

```python
total = tool.get_total_chunks()
print(f"Knowledge base contains {total} chunks")
```

#### get_knowledge_base_info()

Get comprehensive information about the knowledge base.

```python
info = tool.get_knowledge_base_info()
print(f"Path: {info['path']}")
print(f"Status: {info['status']}")
print(f"Total chunks: {info['total_chunks']}")
print(f"Collection: {info['collection_name']}")
print(f"Embedding model: {info['embedding_model']}")
```

## Input Format Guidelines

### Question Format

**Good Questions:**
- Specific and focused: "What is the four-part test for qualified research?"
- Use technical terms: "What are qualified research expenses?"
- Reference specific concepts: "What is a process of experimentation?"

**Poor Questions:**
- Too vague: "Tell me about R&D"
- Too broad: "What is everything about tax credits?"
- Non-questions: "R&D tax credit"

**Tips:**
- Use complete sentences
- Include relevant technical terms (QRE, four-part test, etc.)
- Be specific about what you want to know
- Query expansion will handle abbreviations automatically

### Metadata Filter Format

Metadata filters use ChromaDB's `where` clause syntax:

```python
# Filter by exact source match
metadata_filter = {"source": "Form 6765 Instructions"}

# Filter by source containing text (use $contains)
metadata_filter = {"source": {"$contains": "Form 6765"}}

# Filter by page number
metadata_filter = {"page": 5}

# Filter by page range (use $gte, $lte)
metadata_filter = {"page": {"$gte": 5, "$lte": 10}}

# Combine multiple filters (AND logic)
metadata_filter = {
    "source": "Form 6765 Instructions",
    "page": {"$gte": 1, "$lte": 5}
}
```

## Output Format Reference

### RAGContext Object

```python
class RAGContext(BaseModel):
    query: str                          # Original query text
    chunks: List[Dict[str, Any]]        # Retrieved chunks
    retrieval_timestamp: datetime       # Retrieval time
    total_chunks_available: int         # Total chunks in KB
    retrieval_method: str               # Method used
    
    # Computed properties
    @property
    def chunk_count(self) -> int:
        """Number of chunks retrieved"""
        return len(self.chunks)
    
    @property
    def average_relevance(self) -> float:
        """Average relevance score across chunks"""
        if not self.chunks:
            return 0.0
        return sum(c['relevance_score'] for c in self.chunks) / len(self.chunks)
    
    # Methods
    def format_for_llm_prompt(self, max_chunks: Optional[int] = None) -> str:
        """Format context for LLM prompts"""
        ...
    
    def extract_citations(self) -> List[str]:
        """Extract unique source citations"""
        ...
```

### Chunk Dictionary Structure

```python
{
    'text': str,                # Document text content (full chunk)
    'source': str,              # Document source name
    'page': int,                # Page number in source document
    'relevance_score': float,   # Final relevance score (0.0 to 1.0)
    'original_score': float,    # Original score before re-ranking (optional)
    'boost_factors': List[str]  # Applied boost factors (optional)
}
```

### Relevance Score Interpretation

| Score Range | Quality | Interpretation |
|-------------|---------|----------------|
| 0.90 - 1.00 | Very High | Highly relevant, strong semantic match |
| 0.80 - 0.89 | High | Relevant, good semantic match |
| 0.70 - 0.79 | Medium | Moderately relevant, acceptable match |
| 0.00 - 0.69 | Low | Weakly relevant, may not be useful |

### Retrieval Method Strings

The `retrieval_method` field indicates which optimizations were used:

| Method String | Description |
|---------------|-------------|
| `semantic_search` | Basic semantic search only |
| `semantic_search+query_expansion` | With query expansion |
| `semantic_search+query_rewriting` | With query rewriting |
| `semantic_search+metadata_reranking` | With re-ranking |
| `semantic_search+query_expansion+query_rewriting+metadata_reranking` | All optimizations |

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Empty Results (0 chunks returned)

**Symptoms:**
```python
context = tool.query("my question")
print(context.chunk_count)  # Output: 0
```

**Possible Causes:**
1. Knowledge base is empty (not indexed)
2. Query too specific or uses unknown terms
3. Metadata filter too restrictive

**Solutions:**

```python
# Check if knowledge base is populated
info = tool.get_knowledge_base_info()
print(f"Total chunks: {info['total_chunks']}")

# If 0 chunks, run indexing pipeline
# See tools/indexing_pipeline.py

# Try broader query
context = tool.query("qualified research")  # Instead of very specific terms

# Remove or relax metadata filter
context = tool.query("my question", metadata_filter=None)

# Enable query expansion for better matching
context = tool.query("my question", enable_query_expansion=True)
```

#### Issue: Low Relevance Scores

**Symptoms:**
```python
context = tool.query("my question")
print(context.average_relevance)  # Output: 0.45 (low)
```

**Possible Causes:**
1. Query doesn't match document content well
2. Using non-technical language
3. Query too vague

**Solutions:**

```python
# Use technical terms from IRS documents
context = tool.query("qualified research expenditure")  # Instead of "R&D costs"

# Enable query expansion to match synonyms
context = tool.query("QRE", enable_query_expansion=True)

# Try query rewriting
context = tool.query("What is QRE?", enable_query_rewriting=True)

# Increase top_k to get more results
context = tool.query("my question", top_k=10)
```

#### Issue: RAGRetrievalError - Connection Failure

**Symptoms:**
```python
RAGRetrievalError: Vector database is not initialized
```

**Possible Causes:**
1. Knowledge base path doesn't exist
2. ChromaDB collection not created
3. Permissions issue

**Solutions:**

```python
# Check if path exists
from pathlib import Path
kb_path = Path("./knowledge_base/indexed")
print(f"Path exists: {kb_path.exists()}")

# Create directory if needed
kb_path.mkdir(parents=True, exist_ok=True)

# Re-initialize tool with correct path
tool = RD_Knowledge_Tool(knowledge_base_path=str(kb_path))

# Run indexing pipeline to create collection
# See tools/indexing_pipeline.py
```

#### Issue: Slow Query Performance

**Symptoms:**
- Queries take > 5 seconds
- High memory usage

**Possible Causes:**
1. Large top_k value
2. Query expansion creating too many variations
3. Cache disabled

**Solutions:**

```python
# Enable caching (default)
tool = RD_Knowledge_Tool(enable_cache=True, cache_ttl=3600)

# Reduce top_k
context = tool.query("my question", top_k=3)  # Instead of 10+

# Disable query expansion if not needed
context = tool.query("my question", enable_query_expansion=False)

# Check cache stats
stats = tool.get_cache_stats()
print(f"Cache hit rate: {stats.get('cache_hit_rate', 0):.1f}%")
```

#### Issue: Incorrect or Irrelevant Results

**Symptoms:**
- Retrieved chunks don't match query intent
- Wrong document sources returned

**Possible Causes:**
1. Query ambiguous or unclear
2. Need source filtering
3. Re-ranking not helping

**Solutions:**

```python
# Use metadata filter to restrict sources
context = tool.query(
    "wage limitations",
    metadata_filter={"source": "Form 6765 Instructions"}
)

# Use source preference for re-ranking
context = tool.query(
    "wage limitations",
    enable_reranking=True,
    source_preference="Form 6765"
)

# Make query more specific
context = tool.query(
    "qualified research wage limitations under Section 41"
)  # Instead of just "wage limitations"

# Disable optimizations to see baseline
context = tool.query(
    "my question",
    enable_query_expansion=False,
    enable_query_rewriting=False,
    enable_reranking=False
)
```

#### Issue: Cache Not Working

**Symptoms:**
- Same query always takes full time
- Cache hit rate is 0%

**Possible Causes:**
1. Cache disabled
2. Cache TTL too short
3. Query parameters changing

**Solutions:**

```python
# Check if cache is enabled
stats = tool.get_cache_stats()
print(f"Cache enabled: {stats['enabled']}")

# Enable cache with longer TTL
tool = RD_Knowledge_Tool(enable_cache=True, cache_ttl=7200)  # 2 hours

# Use consistent parameters for cache hits
# These will NOT hit cache (different parameters):
context1 = tool.query("test", top_k=3)
context2 = tool.query("test", top_k=5)  # Different top_k

# These WILL hit cache (same parameters):
context1 = tool.query("test", top_k=3)
context2 = tool.query("test", top_k=3)  # Same parameters

# Clear cache if needed
tool.clear_cache()
```

#### Issue: ValueError - Invalid Input

**Symptoms:**
```python
ValueError: Question must be a non-empty string
ValueError: top_k must be at least 1
```

**Solutions:**

```python
# Ensure question is non-empty string
question = "What is QRE?"
if question and isinstance(question, str):
    context = tool.query(question)

# Ensure top_k is positive integer
top_k = max(1, top_k)  # Ensure at least 1
context = tool.query("my question", top_k=top_k)

# Handle None values
top_k = None  # Will use default_top_k
context = tool.query("my question", top_k=top_k)
```

### Debugging Tips

#### Enable Debug Logging

```python
import logging

# Set logging level to DEBUG
logging.basicConfig(level=logging.DEBUG)

# Or just for RD_Knowledge_Tool
logger = logging.getLogger('tools.rd_knowledge_tool')
logger.setLevel(logging.DEBUG)

# Now queries will show detailed logs
context = tool.query("my question")
```

#### Inspect Query Processing

```python
# Test query expansion
expansions = tool._expand_query("What is QRE?")
print(f"Query variations: {expansions}")

# Test query rewriting
rewritten = tool._rewrite_query("What is the four-part test?")
print(f"Rewritten: {rewritten}")

# Test re-ranking
chunks = [...]  # Your chunks
reranked = tool._rerank_results(chunks, "query", source_preference="Form 6765")
for chunk in reranked:
    print(f"Score: {chunk['relevance_score']}, Boosts: {chunk.get('boost_factors', [])}")
```

#### Check Knowledge Base Status

```python
# Get comprehensive info
info = tool.get_knowledge_base_info()
print(f"Status: {info['status']}")
print(f"Total chunks: {info['total_chunks']}")

# If status is 'error', check the error message
if info['status'] == 'error':
    print(f"Error: {info['error']}")

# Get total chunks directly
total = tool.get_total_chunks()
if total == 0:
    print("WARNING: Knowledge base is empty!")
```

#### Test with Known Good Query

```python
# Use a query that should definitely return results
test_query = "qualified research"
context = tool.query(test_query, top_k=5)

if context.chunk_count == 0:
    print("ERROR: Even basic query returned no results")
    print("Knowledge base may not be indexed properly")
else:
    print(f"SUCCESS: Retrieved {context.chunk_count} chunks")
    print(f"Average relevance: {context.average_relevance:.2f}")
```

### Performance Benchmarks

Expected performance metrics:

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| Single query (cold) | < 5 seconds | First query, no cache |
| Single query (cached) | < 0.1 seconds | Cache hit |
| Batch query (10 questions) | < 30 seconds | With caching |
| Format for LLM | < 0.5 seconds | Any size context |

If performance is significantly worse, check:
- Knowledge base size (very large = slower)
- top_k value (higher = slower)
- Query expansion (more variations = slower)
- System resources (CPU, memory)

## Testing

Run the tests with:

```bash
pytest tests/test_rd_knowledge_tool.py -v
```

## Example Scripts

- `examples/rd_knowledge_tool_usage_example.py`: Basic usage examples
- `examples/rd_knowledge_tool_query_optimization_example.py`: Query optimization features
- `examples/rd_knowledge_tool_format_for_llm_example.py`: LLM formatting examples

## Requirements

- Python 3.8+
- ChromaDB vector database must be initialized and populated
- IRS documents must be indexed (see `tools/indexing_pipeline.py`)

## Related Modules

- `tools/vector_db.py`: Vector database wrapper
- `tools/embedder.py`: Text embedding generation
- `tools/indexing_pipeline.py`: Document indexing
- `models/tax_models.py`: RAGContext and related models
