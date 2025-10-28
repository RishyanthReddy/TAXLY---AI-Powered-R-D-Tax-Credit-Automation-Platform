"""
Unit tests for the VectorDB class.

Tests cover:
- Database initialization
- Document insertion
- Similarity search
- Metadata filtering
- Error handling
- Collection management
"""

import pytest
import os
import tempfile
import shutil
from typing import List, Dict

from tools.vector_db import VectorDB
from utils.exceptions import RAGRetrievalError


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for test database"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def vector_db(temp_db_dir):
    """Create a VectorDB instance for testing"""
    return VectorDB(persist_directory=temp_db_dir, collection_name="test_collection")


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


class TestVectorDBInitialization:
    """Test database initialization"""
    
    def test_initialization_success(self, temp_db_dir):
        """Test successful database initialization"""