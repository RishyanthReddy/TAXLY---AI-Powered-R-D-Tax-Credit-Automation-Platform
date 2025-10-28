"""
Script to verify ChromaDB persistence issue.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tempfile
import shutil
import time
import gc

from tools.vector_db import VectorDB
from tools.embedder import Embedder

# Create temp directory
temp_dir = tempfile.mkdtemp()
indexed_dir = Path(temp_dir) / "indexed"
indexed_dir.mkdir(exist_ok=True)

print(f"Testing in: {temp_dir}")

try:
    # Step 1: Create VectorDB and add documents
    print("\n=== Step 1: Creating VectorDB and adding documents ===")
    vector_db1 = VectorDB(
        persist_directory=str(indexed_dir),
        collection_name="irs_documents"
    )
    
    print(f"Initial count: {vector_db1.count()}")
    
    # Add a test document
    vector_db1.add_documents(
        texts=["Test document about qualified research"],
        metadatas=[{"source": "test", "page": 1}],
        ids=["test_1"]
    )
    
    print(f"After adding: {vector_db1.count()}")
    
    # Clean up first instance
    del vector_db1
    gc.collect()
    time.sleep(0.5)
    
    # Step 2: Create new VectorDB instance and check count
    print("\n=== Step 2: Creating new VectorDB instance ===")
    vector_db2 = VectorDB(
        persist_directory=str(indexed_dir),
        collection_name="irs_documents"
    )
    
    print(f"New instance count: {vector_db2.count()}")
    
    # Try to query
    if vector_db2.count() > 0:
        results = vector_db2.query("qualified research", top_k=1)
        print(f"Query results: {len(results['documents'][0])} documents")
        print("✅ Persistence working!")
    else:
        print("❌ Persistence NOT working - count is 0")
    
    del vector_db2
    gc.collect()
    
finally:
    # Cleanup
    time.sleep(0.5)
    try:
        shutil.rmtree(temp_dir)
    except:
        pass
