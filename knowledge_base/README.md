# Knowledge Base Directory

This directory contains IRS tax documents and their indexed representations for the RAG (Retrieval-Augmented Generation) system.

## Directory Structure

```
knowledge_base/
├── tax_docs/          # Source PDF documents from IRS
├── indexed/           # ChromaDB vector database storage
├── metadata.json      # Document tracking and metadata
└── README.md          # This file
```

## Source Documents

The following IRS documents should be placed in the `tax_docs/` directory:

1. **CFR-2012-title26-vol1-sec1-41-4.pdf**
   - Code of Federal Regulations Title 26 § 1.41-4
   - Defines qualified research activities and the four-part test

2. **Instructions for Form 6765.pdf**
   - Official instructions for claiming R&D tax credits
   - Contains wage caps and QRE definitions

3. **IRS Audit Guidelines for Software.pdf**
   - Guidance for auditing software development R&D claims
   - Documentation requirements and common issues

4. **IRS Publication 542 (Corporations).pdf**
   - General corporate tax information
   - Relevant sections on R&D credits

## Setup Instructions

### 1. Copy Source Documents

Copy the PDF files from the root `knowledge_base/` directory to `tax_docs/`:

```bash
# Windows
copy ..\..\..\knowledge_base\*.pdf tax_docs\

# Linux/Mac
cp ../../../knowledge_base/*.pdf tax_docs/
```

### 2. Index Documents

Run the indexing pipeline (to be implemented in Phase 2):

```bash
python -m tools.indexing_pipeline
```

This will:
- Extract text from PDFs in `tax_docs/`
- Chunk text into 512-token segments with 50-token overlap
- Generate embeddings using Sentence Transformers
- Store in ChromaDB in the `indexed/` directory
- Update `metadata.json` with indexing status

## Metadata Format

The `metadata.json` file tracks all documents with the following fields:

- `id`: Unique identifier for the document
- `filename`: Original PDF filename
- `title`: Human-readable document title
- `description`: Brief description of document contents
- `source`: Source website (e.g., irs.gov, govinfo.gov)
- `source_url`: Original download URL
- `download_date`: Date document was downloaded
- `version`: Document version or year
- `key_topics`: List of main topics covered
- `page_count`: Number of pages (populated after indexing)
- `file_size_bytes`: File size (populated after indexing)
- `indexed`: Boolean indicating if document has been indexed
- `index_date`: Date document was indexed

## Usage

The RAG Knowledge Tool (`tools/rd_knowledge_tool.py`) will use this knowledge base to:

1. Query the vector database for relevant IRS guidance
2. Retrieve top-k most relevant text chunks
3. Provide context to the LLM for R&D qualification decisions
4. Include source citations in qualification results

## Maintenance

- Update `metadata.json` when adding new documents
- Re-index documents when IRS releases updated versions
- Keep source PDFs in `tax_docs/` for reference and re-indexing
- The `indexed/` directory can be regenerated from source PDFs
