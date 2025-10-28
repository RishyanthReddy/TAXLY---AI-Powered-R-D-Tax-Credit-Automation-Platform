"""
Text Chunker Usage Examples

This script demonstrates how to use the text_chunker module to chunk text
for RAG (Retrieval-Augmented Generation) systems.
"""

from tools.text_chunker import (
    chunk_text,
    chunk_document,
    chunk_multiple_documents
)
from tools.pdf_extractor import extract_text_from_pdf


def example_1_basic_text_chunking():
    """Example 1: Basic text chunking with custom parameters"""
    print("=" * 60)
    print("Example 1: Basic Text Chunking")
    print("=" * 60)
    
    text = """
    Section 41 of the Internal Revenue Code provides a tax credit for increasing 
    research activities. The credit is equal to 20 percent of the excess of qualified 
    research expenses for the taxable year over the base amount. Qualified research 
    expenses include in-house research expenses and contract research expenses.
    """
    
    # Chunk with default parameters (512 tokens, 50 token overlap)
    chunks = chunk_text(text)
    
    print(f"\nCreated {len(chunks)} chunk(s) with default parameters")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i}:")
        print(f"  Token count: {chunk['token_count']}")
        print(f"  Char count: {chunk['char_count']}")
        print(f"  Text preview: {chunk['text'][:100]}...")
    
    # Chunk with custom parameters
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    
    print(f"\n\nCreated {len(chunks)} chunk(s) with custom parameters (50 tokens, 10 overlap)")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i}:")
        print(f"  Token count: {chunk['token_count']}")
        print(f"  Text: {chunk['text']}")


def example_2_chunking_with_metadata():
    """Example 2: Chunking with source metadata"""
    print("\n" + "=" * 60)
    print("Example 2: Chunking with Metadata")
    print("=" * 60)
    
    text = """
    In-house research expenses consist of wages paid to employees, supplies used in 
    the conduct of qualified research, and amounts paid for the use of computers in 
    qualified research. The term 'qualified research' means research with respect to 
    which expenditures may be treated as expenses under section 174.
    """
    
    chunks = chunk_text(
        text,
        chunk_size=100,
        overlap=20,
        source_document="IRS_Publication_542.pdf",
        page_number=15
    )
    
    print(f"\nCreated {len(chunks)} chunk(s) with metadata")
    for chunk in chunks:
        print(f"\nChunk {chunk['chunk_index']}:")
        print(f"  Source: {chunk['source_document']}")
        print(f"  Page: {chunk['page_number']}")
        print(f"  Tokens: {chunk['token_count']}")
        print(f"  Position: chars {chunk['start_char']}-{chunk['end_char']}")


def example_3_chunking_pdf_document():
    """Example 3: Chunking a PDF document"""
    print("\n" + "=" * 60)
    print("Example 3: Chunking PDF Document")
    print("=" * 60)
    
    # First, extract text from a PDF
    # Note: This assumes you have a PDF file in the knowledge_base directory
    pdf_path = "knowledge_base/tax_docs/CFR-2012-title26-vol1-sec1-41-4.pdf"
    
    try:
        # Extract text from PDF
        print(f"\nExtracting text from: {pdf_path}")
        document = extract_text_from_pdf(pdf_path)
        
        print(f"Extracted {document['total_pages']} pages")
        print(f"Total characters: {document['total_chars']}")
        
        # Chunk the document
        print("\nChunking document...")
        chunks = chunk_document(
            document,
            chunk_size=512,
            overlap=50
        )
        
        print(f"\nCreated {len(chunks)} chunks from document")
        
        # Show statistics
        total_tokens = sum(chunk['token_count'] for chunk in chunks)
        avg_tokens = total_tokens / len(chunks) if chunks else 0
        
        print(f"Total tokens: {total_tokens}")
        print(f"Average tokens per chunk: {avg_tokens:.1f}")
        
        # Show first few chunks
        print("\nFirst 3 chunks:")
        for chunk in chunks[:3]:
            print(f"\n  Chunk {chunk['chunk_index']} (Page {chunk['page_number']}):")
            print(f"    Tokens: {chunk['token_count']}")
            print(f"    Preview: {chunk['text'][:150]}...")
    
    except FileNotFoundError:
        print(f"\nPDF file not found: {pdf_path}")
        print("Please ensure the PDF exists in the knowledge_base directory")
    except Exception as e:
        print(f"\nError processing PDF: {e}")


def example_4_chunking_multiple_documents():
    """Example 4: Chunking multiple PDF documents"""
    print("\n" + "=" * 60)
    print("Example 4: Chunking Multiple Documents")
    print("=" * 60)
    
    # Simulate multiple extracted documents
    documents = [
        {
            'file_path': 'doc1.pdf',
            'pages': [
                {
                    'page_number': 1,
                    'text': 'This is the first document. ' * 50
                }
            ],
            'total_pages': 1
        },
        {
            'file_path': 'doc2.pdf',
            'pages': [
                {
                    'page_number': 1,
                    'text': 'This is the second document. ' * 50
                }
            ],
            'total_pages': 1
        }
    ]
    
    # Chunk all documents
    result = chunk_multiple_documents(
        documents,
        chunk_size=100,
        overlap=20
    )
    
    print(f"\nProcessed {result['documents_processed']} documents")
    print(f"Failed: {result['documents_failed']}")
    print(f"Total chunks created: {result['total_chunks']}")
    
    # Group chunks by source document
    chunks_by_doc = {}
    for chunk in result['chunks']:
        doc = chunk['source_document']
        if doc not in chunks_by_doc:
            chunks_by_doc[doc] = []
        chunks_by_doc[doc].append(chunk)
    
    print("\nChunks per document:")
    for doc, chunks in chunks_by_doc.items():
        print(f"  {doc}: {len(chunks)} chunks")


def example_5_overlap_demonstration():
    """Example 5: Demonstrating overlap between chunks"""
    print("\n" + "=" * 60)
    print("Example 5: Overlap Demonstration")
    print("=" * 60)
    
    text = """
    First sentence about research. Second sentence about development. 
    Third sentence about innovation. Fourth sentence about technology. 
    Fifth sentence about experimentation. Sixth sentence about discovery.
    """
    
    chunks = chunk_text(text, chunk_size=20, overlap=8)
    
    print(f"\nCreated {len(chunks)} chunks with 8-token overlap")
    
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i}:")
        print(f"  Tokens: {chunk['token_count']}")
        print(f"  Text: {chunk['text']}")
        
        # Show overlap with next chunk
        if i < len(chunks) - 1:
            next_chunk = chunks[i + 1]
            current_words = set(chunk['text'].split())
            next_words = set(next_chunk['text'].split())
            overlap_words = current_words & next_words
            print(f"  Overlapping words with next chunk: {len(overlap_words)}")


def example_6_rag_pipeline_preparation():
    """Example 6: Preparing chunks for RAG system"""
    print("\n" + "=" * 60)
    print("Example 6: RAG Pipeline Preparation")
    print("=" * 60)
    
    # Simulate IRS document text
    irs_text = """
    The four-part test for qualified research requires that the research must:
    (1) Be undertaken for the purpose of discovering information that is technological in nature.
    (2) The application of the information must be intended to be useful in the development of a new or improved business component.
    (3) Substantially all of the activities must constitute elements of a process of experimentation.
    (4) The process of experimentation must fundamentally rely on principles of physical or biological sciences, engineering, or computer science.
    """
    
    # Chunk for RAG system
    chunks = chunk_text(
        irs_text,
        chunk_size=100,
        overlap=20,
        source_document="IRS_Section_41_Guidelines.pdf",
        page_number=3
    )
    
    print(f"\nPrepared {len(chunks)} chunks for RAG system")
    
    # Format chunks for vector database storage
    print("\nFormatted for vector database:")
    for chunk in chunks:
        # This is the format you'd use for ChromaDB or similar
        vector_db_entry = {
            'id': f"{chunk['source_document']}_p{chunk['page_number']}_c{chunk['chunk_index']}",
            'text': chunk['text'],
            'metadata': {
                'source': chunk['source_document'],
                'page': chunk['page_number'],
                'chunk_index': chunk['chunk_index'],
                'token_count': chunk['token_count']
            }
        }
        print(f"\n  ID: {vector_db_entry['id']}")
        print(f"  Tokens: {vector_db_entry['metadata']['token_count']}")
        print(f"  Text preview: {vector_db_entry['text'][:100]}...")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TEXT CHUNKER USAGE EXAMPLES")
    print("=" * 60)
    
    # Run all examples
    example_1_basic_text_chunking()
    example_2_chunking_with_metadata()
    example_3_chunking_pdf_document()
    example_4_chunking_multiple_documents()
    example_5_overlap_demonstration()
    example_6_rag_pipeline_preparation()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
