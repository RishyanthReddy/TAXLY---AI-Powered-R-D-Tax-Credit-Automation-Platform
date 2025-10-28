"""
Vector Database Module

This module provides ChromaDB vector database functionality for storing and
retrieving IRS document embeddings. It supports persistent storage, metadata
filtering, and similarity search for the RAG (Retrieval-Augmented Generation) system.

Classes:
    VectorDB: Main class for managing the ChromaDB vector database

Example:
    >>> from tools.vector_db import VectorDB
    >>> vector_db = VectorDB(persist_directory="./knowledge_base/indexed")
    >>> vector_db.add_documents(
    ...     texts=["Sample IRS text"],
    ...     metadatas=[{"source": "Form 6765", "page": 1}],
    ...     ids=["doc_1"]
    ... )
    >>> results = vector_db.query("R&D tax credit", top_k=3)
"""

from typing import List, Dict, Optional, Any
import logging
import os
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from utils.exceptions import RAGRetrievalError

# Configure logger
logger = logging.getLogger(__name__)


class VectorDB:
    """
    ChromaDB vector database manager for IRS document storage and retrieval.
    
    This class provides a high-level interface to ChromaDB for storing document
    embeddings with metadata and performing similarity searches. It uses cosine
    similarity as the distance metric and supports persistent storage.
    
    Attributes:
        persist_directory (str): Path to the persistent storage directory
        collection_name (str): Name of the ChromaDB collection
        client (chromadb.Client): ChromaDB client instance
        collection (chromadb.Collection): ChromaDB collection instance
        embedding_function: Embedding function for the collection
    
    Example:
        >>> vector_db = VectorDB()
        >>> vector_db.add_documents(
        ...     texts=["IRS guidance text"],
        ...     metadatas=[{"source": "CFR Title 26", "page": 5}],
        ...     ids=["chunk_1"]
        ... )
        >>> results = vector_db.query("qualified research", top_k=3)
    """
    
    def __init__(
        self,
        persist_directory: str = "./knowledge_base/indexed",
        collection_name: str = "irs_documents",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize the VectorDB with persistent storage.
        
        Args:
            persist_directory (str): Path to store the ChromaDB database.
                                    Default is "./knowledge_base/indexed"
            collection_name (str): Name of the collection to create/use.
                                  Default is "irs_documents"
            embedding_model (str): Name of the SentenceTransformer model to use.
                                  Default is "all-MiniLM-L6-v2"
        
        Raises:
            RAGRetrievalError: If database initialization fails
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        try:
            # Create persist directory if it doesn't exist
            os.makedirs(persist_directory, exist_ok=True)
            logger.info(f"Persist directory: {persist_directory}")
            
            # Initialize ChromaDB client with persistent storage
            logger.info("Initializing ChromaDB client with persistent storage")
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize embedding function
            logger.info(f"Initializing embedding function: {embedding_model}")
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=embedding_model
            )
            
            # Create or get collection with cosine similarity
            logger.info(f"Creating/getting collection: {collection_name}")
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={
                    "hnsw:space": "cosine",  # Use cosine similarity
                    "description": "IRS documents for R&D tax credit qualification"
                }
            )
            
            logger.info(
                f"VectorDB initialized successfully. "
                f"Collection: {collection_name}, "
                f"Document count: {self.collection.count()}"
            )
            
        except Exception as e:
            error_msg = f"Failed to initialize ChromaDB: {str(e)}"
            logger.error(error_msg)
            raise RAGRetrievalError(
                message=error_msg,
                knowledge_base_path=persist_directory,
                error_type="initialization"
            )
    
    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Add documents to the vector database.
        
        Args:
            texts (List[str]): List of document texts to add
            metadatas (List[Dict[str, Any]]): List of metadata dictionaries,
                                              one per document. Should include
                                              'source', 'page', 'chunk_index', etc.
            ids (List[str]): List of unique document IDs
        
        Raises:
            RAGRetrievalError: If document addition fails
            ValueError: If input lists have different lengths
        
        Example:
            >>> vector_db.add_documents(
            ...     texts=["Text 1", "Text 2"],
            ...     metadatas=[
            ...         {"source": "Form 6765", "page": 1, "chunk_index": 0},
            ...         {"source": "Form 6765", "page": 1, "chunk_index": 1}
            ...     ],
            ...     ids=["doc_1", "doc_2"]
            ... )
        """
        if not (len(texts) == len(metadatas) == len(ids)):
            raise ValueError(
                f"Length mismatch: texts={len(texts)}, "
                f"metadatas={len(metadatas)}, ids={len(ids)}"
            )
        
        if not texts:
            logger.warning("No documents to add")
            return
        
        try:
            logger.info(f"Adding {len(texts)} documents to collection")
            
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(
                f"Successfully added {len(texts)} documents. "
                f"Total documents: {self.collection.count()}"
            )
            
        except Exception as e:
            error_msg = f"Failed to add documents to ChromaDB: {str(e)}"
            logger.error(error_msg)
            raise RAGRetrievalError(
                message=error_msg,
                knowledge_base_path=self.persist_directory,
                error_type="indexing",
                details={"document_count": len(texts)}
            )
    
    def query(
        self,
        query_text: str,
        top_k: int = 3,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the vector database for similar documents.
        
        Args:
            query_text (str): The query text to search for
            top_k (int): Number of results to return. Default is 3.
            where (Optional[Dict[str, Any]]): Metadata filter conditions.
                                             Example: {"source": "Form 6765"}
            where_document (Optional[Dict[str, Any]]): Document content filter.
                                                       Example: {"$contains": "qualified"}
        
        Returns:
            Dict[str, Any]: Query results containing:
                - documents: List of document texts
                - metadatas: List of metadata dictionaries
                - distances: List of distance scores (lower is more similar)
                - ids: List of document IDs
        
        Raises:
            RAGRetrievalError: If query fails
            ValueError: If query_text is empty
        
        Example:
            >>> results = vector_db.query("R&D tax credit", top_k=3)
            >>> for doc, metadata, distance in zip(
            ...     results['documents'][0],
            ...     results['metadatas'][0],
            ...     results['distances'][0]
            ... ):
            ...     print(f"Source: {metadata['source']}, Distance: {distance}")
            ...     print(f"Text: {doc[:100]}...")
        """
        if not query_text or not isinstance(query_text, str):
            raise ValueError("query_text must be a non-empty string")
        
        try:
            logger.info(
                f"Querying collection with: '{query_text[:50]}...', top_k={top_k}"
            )
            
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=where,
                where_document=where_document
            )
            
            num_results = len(results['documents'][0]) if results['documents'] else 0
            logger.info(f"Query returned {num_results} results")
            
            if num_results == 0:
                logger.warning(f"No results found for query: '{query_text[:50]}...'")
            
            return results
            
        except Exception as e:
            error_msg = f"Failed to query ChromaDB: {str(e)}"
            logger.error(error_msg)
            raise RAGRetrievalError(
                message=error_msg,
                query=query_text,
                knowledge_base_path=self.persist_directory,
                error_type="query",
                details={"top_k": top_k}
            )
    
    def get_by_ids(self, ids: List[str]) -> Dict[str, Any]:
        """
        Retrieve documents by their IDs.
        
        Args:
            ids (List[str]): List of document IDs to retrieve
        
        Returns:
            Dict[str, Any]: Retrieved documents with their metadata
        
        Raises:
            RAGRetrievalError: If retrieval fails
        
        Example:
            >>> results = vector_db.get_by_ids(["doc_1", "doc_2"])
            >>> print(results['documents'])
        """
        if not ids:
            raise ValueError("ids list cannot be empty")
        
        try:
            logger.info(f"Retrieving {len(ids)} documents by ID")
            results = self.collection.get(ids=ids)
            logger.info(f"Retrieved {len(results['documents'])} documents")
            return results
            
        except Exception as e:
            error_msg = f"Failed to retrieve documents by ID: {str(e)}"
            logger.error(error_msg)
            raise RAGRetrievalError(
                message=error_msg,
                knowledge_base_path=self.persist_directory,
                error_type="retrieval",
                details={"ids": ids}
            )
    
    def delete_by_ids(self, ids: List[str]) -> None:
        """
        Delete documents by their IDs.
        
        Args:
            ids (List[str]): List of document IDs to delete
        
        Raises:
            RAGRetrievalError: If deletion fails
        
        Example:
            >>> vector_db.delete_by_ids(["doc_1", "doc_2"])
        """
        if not ids:
            raise ValueError("ids list cannot be empty")
        
        try:
            logger.info(f"Deleting {len(ids)} documents")
            self.collection.delete(ids=ids)
            logger.info(f"Successfully deleted {len(ids)} documents")
            
        except Exception as e:
            error_msg = f"Failed to delete documents: {str(e)}"
            logger.error(error_msg)
            raise RAGRetrievalError(
                message=error_msg,
                knowledge_base_path=self.persist_directory,
                error_type="deletion",
                details={"ids": ids}
            )
    
    def count(self) -> int:
        """
        Get the total number of documents in the collection.
        
        Returns:
            int: Number of documents in the collection
        
        Example:
            >>> count = vector_db.count()
            >>> print(f"Total documents: {count}")
        """
        try:
            count = self.collection.count()
            logger.debug(f"Collection contains {count} documents")
            return count
        except Exception as e:
            logger.error(f"Failed to get document count: {str(e)}")
            return 0
    
    def reset(self) -> None:
        """
        Delete all documents from the collection.
        
        WARNING: This operation cannot be undone!
        
        Raises:
            RAGRetrievalError: If reset fails
        
        Example:
            >>> vector_db.reset()  # Deletes all documents
        """
        try:
            logger.warning(f"Resetting collection: {self.collection_name}")
            
            # Delete the collection
            self.client.delete_collection(name=self.collection_name)
            
            # Recreate the collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={
                    "hnsw:space": "cosine",
                    "description": "IRS documents for R&D tax credit qualification"
                }
            )
            
            logger.info(f"Collection {self.collection_name} reset successfully")
            
        except Exception as e:
            error_msg = f"Failed to reset collection: {str(e)}"
            logger.error(error_msg)
            raise RAGRetrievalError(
                message=error_msg,
                knowledge_base_path=self.persist_directory,
                error_type="reset"
            )
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.
        
        Returns:
            Dict[str, Any]: Collection information including name, count, and metadata
        
        Example:
            >>> info = vector_db.get_collection_info()
            >>> print(f"Collection: {info['name']}, Documents: {info['count']}")
        """
        try:
            return {
                "name": self.collection_name,
                "count": self.collection.count(),
                "metadata": self.collection.metadata,
                "persist_directory": self.persist_directory,
                "embedding_model": self.embedding_model
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {str(e)}")
            return {
                "name": self.collection_name,
                "error": str(e)
            }
