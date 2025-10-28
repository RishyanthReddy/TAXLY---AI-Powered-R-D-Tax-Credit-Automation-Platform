"""
Unit tests for the VectorDB class.
"""

import pytest
import os
import tempfile
import shutil
import gc
import time

from tools.vector_db import VectorDB
from utils.exceptions import RAGRetrievalError


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for test database"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Give ChromaDB time to release file handles
    gc.collect()
    time.sleep(0.1)
    # Try to cleanup, ignore errors on Windows
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except PermissionError:
        # Windows file locking - ChromaDB still has handles open
        # This is expected and doesn't affect test validity
        pass


@pytest.fixture
def vector_db(temp_db_dir):
    """Create a VectorDB instance for testing"""
    db = VectorDB(persist_directory=temp_db_dir, collection_name="test_collection")
    yield db
    # Cleanup: try to close the client
    try:
        if hasattr(db, 'client') and db.client:
            # ChromaDB doesn't have an explicit close method, but we can clear references
            del db.client
            del db.collection
    except:
        pass
    gc.collect()


@pytest.fixture
def sample_documents():
    """Sample documents for testing"""
    return {
        "texts": [
            "The R&D tax credit applies to qualified research expenditures.",
            "Software development can qualify under the four-part test.",
            "Wages paid to employees for qualified research are eligible."
        ],
        "metadatas": [
            {"source": "Form 6765", "page": 1, "chunk_index": 0},
            {"source": "CFR Title 26", "page": 5, "chunk_index": 0},
            {"source": "Publication 542", "page": 10, "chunk_index": 0}
        ],
        "ids": ["doc_1", "doc_2", "doc_3"]
    }


def test_initialization_success(temp_db_dir):
    """Test successful database initialization"""
    db = VectorDB(persist_directory=temp_db_dir)
    try:
        assert db.persist_directory == temp_db_dir
        assert db.collection_name == "irs_documents"
        assert db.embedding_model == "all-MiniLM-L6-v2"
        assert db.client is not None
        assert db.collection is not None
    finally:
        # Cleanup
        del db
        gc.collect()


def test_initialization_creates_directory():
    """Test that initialization creates persist directory if it doesn't exist"""
    temp_dir = tempfile.mkdtemp()
    new_dir = os.path.join(temp_dir, "new_db_dir")
    
    try:
        db = VectorDB(persist_directory=new_dir)
        assert os.path.exists(new_dir)
        del db
        gc.collect()
        time.sleep(0.1)
    finally:
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except PermissionError:
            pass


def test_collection_uses_cosine_similarity(vector_db):
    """Test that collection is configured with cosine similarity"""
    metadata = vector_db.collection.metadata
    assert metadata.get("hnsw:space") == "cosine"


def test_add_documents_success(vector_db, sample_documents):
    """Test successful document addition"""
    vector_db.add_documents(
        texts=sample_documents["texts"],
        metadatas=sample_documents["metadatas"],
        ids=sample_documents["ids"]
    )
    
    assert vector_db.count() == 3


def test_add_documents_length_mismatch(vector_db):
    """Test that length mismatch raises ValueError"""
    with pytest.raises(ValueError, match="Length mismatch"):
        vector_db.add_documents(
            texts=["text1", "text2"],
            metadatas=[{"source": "test"}],
            ids=["id1", "id2"]
        )


def test_query_success(vector_db, sample_documents):
    """Test successful query"""
    vector_db.add_documents(
        texts=sample_documents["texts"],
        metadatas=sample_documents["metadatas"],
        ids=sample_documents["ids"]
    )
    
    results = vector_db.query("R&D tax credit", top_k=2)
    
    assert len(results["documents"][0]) == 2
    assert len(results["metadatas"][0]) == 2
    assert len(results["distances"][0]) == 2


def test_query_with_metadata_filter(vector_db, sample_documents):
    """Test query with metadata filter"""
    vector_db.add_documents(
        texts=sample_documents["texts"],
        metadatas=sample_documents["metadatas"],
        ids=sample_documents["ids"]
    )
    
    results = vector_db.query(
        "research",
        top_k=3,
        where={"source": "Form 6765"}
    )
    
    assert len(results["documents"][0]) == 1
    assert results["metadatas"][0][0]["source"] == "Form 6765"


def test_get_by_ids_success(vector_db, sample_documents):
    """Test successful retrieval by IDs"""
    vector_db.add_documents(
        texts=sample_documents["texts"],
        metadatas=sample_documents["metadatas"],
        ids=sample_documents["ids"]
    )
    
    results = vector_db.get_by_ids(["doc_1", "doc_3"])
    
    assert len(results["documents"]) == 2
    assert "doc_1" in results["ids"]
    assert "doc_3" in results["ids"]


def test_delete_by_ids_success(vector_db, sample_documents):
    """Test successful deletion by IDs"""
    vector_db.add_documents(
        texts=sample_documents["texts"],
        metadatas=sample_documents["metadatas"],
        ids=sample_documents["ids"]
    )
    
    initial_count = vector_db.count()
    vector_db.delete_by_ids(["doc_1"])
    
    assert vector_db.count() == initial_count - 1


def test_reset(vector_db, sample_documents):
    """Test collection reset"""
    vector_db.add_documents(
        texts=sample_documents["texts"],
        metadatas=sample_documents["metadatas"],
        ids=sample_documents["ids"]
    )
    
    assert vector_db.count() == 3
    
    vector_db.reset()
    
    assert vector_db.count() == 0


def test_persistence_across_instances(temp_db_dir, sample_documents):
    """Test that data persists across VectorDB instances"""
    db1 = VectorDB(persist_directory=temp_db_dir, collection_name="persist_test")
    db1.add_documents(
        texts=sample_documents["texts"],
        metadatas=sample_documents["metadatas"],
        ids=sample_documents["ids"]
    )
    count1 = db1.count()
    
    # Cleanup first instance
    del db1
    gc.collect()
    time.sleep(0.1)
    
    db2 = VectorDB(persist_directory=temp_db_dir, collection_name="persist_test")
    count2 = db2.count()
    
    assert count1 == count2 == 3
    
    results = db2.query("research", top_k=3)
    assert len(results["documents"][0]) == 3
    
    # Cleanup second instance
    del db2
    gc.collect()
