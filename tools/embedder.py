"""
Embedder Module

This module provides text embedding functionality using SentenceTransformer models.
It includes caching capabilities to avoid recomputing embeddings for repeated texts.

Classes:
    Embedder: Main class for generating text embeddings with caching support

Example:
    >>> from tools.embedder import Embedder
    >>> embedder = Embedder()
    >>> embedding = embedder.encode_text("Sample text for embedding")
    >>> print(f"Embedding dimension: {len(embedding)}")
    >>> 
    >>> # Batch encoding
    >>> texts = ["Text 1", "Text 2", "Text 3"]
    >>> embeddings = embedder.encode_batch(texts)
    >>> print(f"Generated {len(embeddings)} embeddings")
"""

from typing import List, Union, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import hashlib
import logging

# Configure logger
logger = logging.getLogger(__name__)


class Embedder:
    """
    Text embedding generator using SentenceTransformer models.
    
    This class provides methods to encode single texts or batches of texts into
    dense vector embeddings. It includes an in-memory cache to avoid recomputing
    embeddings for texts that have been processed before.
    
    Attributes:
        model_name (str): Name of the SentenceTransformer model to use
        model (SentenceTransformer): The loaded SentenceTransformer model
        cache (dict): In-memory cache mapping text hashes to embeddings
        embedding_dim (int): Dimension of the embedding vectors
    
    Example:
        >>> embedder = Embedder()
        >>> embedding = embedder.encode_text("Hello world")
        >>> print(embedding.shape)
        (384,)
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the Embedder with a specified model.
        
        Args:
            model_name (str): Name of the SentenceTransformer model to use.
                            Default is 'all-MiniLM-L6-v2' which produces 384-dimensional embeddings.
        
        Raises:
            Exception: If the model fails to load
        """
        self.model_name = model_name
        self.cache = {}
        
        try:
            logger.info(f"Loading SentenceTransformer model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise
    
    def _get_cache_key(self, text: str) -> str:
        """
        Generate a cache key for a given text.
        
        Uses SHA-256 hash of the text to create a unique cache key.
        
        Args:
            text (str): The text to generate a cache key for
        
        Returns:
            str: SHA-256 hash of the text
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def encode_text(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Encode a single text into an embedding vector.
        
        Args:
            text (str): The text to encode
            use_cache (bool): Whether to use cached embeddings if available. Default is True.
        
        Returns:
            np.ndarray: The embedding vector as a numpy array
        
        Raises:
            ValueError: If text is empty or None
            Exception: If encoding fails
        
        Example:
            >>> embedder = Embedder()
            >>> embedding = embedder.encode_text("Sample text")
            >>> print(type(embedding))
            <class 'numpy.ndarray'>
        """
        if not text or not isinstance(text, str):
            raise ValueError("Text must be a non-empty string")
        
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in self.cache:
                logger.debug(f"Cache hit for text: {text[:50]}...")
                return self.cache[cache_key]
        
        try:
            # Generate embedding
            logger.debug(f"Encoding text: {text[:50]}...")
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Store in cache
            if use_cache:
                cache_key = self._get_cache_key(text)
                self.cache[cache_key] = embedding
                logger.debug(f"Cached embedding for text: {text[:50]}...")
            
            return embedding
        
        except Exception as e:
            logger.error(f"Failed to encode text: {str(e)}")
            raise
    
    def encode_batch(
        self, 
        texts: List[str], 
        use_cache: bool = True,
        batch_size: int = 32,
        show_progress_bar: bool = False
    ) -> List[np.ndarray]:
        """
        Encode multiple texts into embedding vectors.
        
        This method efficiently processes multiple texts, using cached embeddings
        where available and batch-encoding the remaining texts.
        
        Args:
            texts (List[str]): List of texts to encode
            use_cache (bool): Whether to use cached embeddings if available. Default is True.
            batch_size (int): Batch size for encoding. Default is 32.
            show_progress_bar (bool): Whether to show a progress bar. Default is False.
        
        Returns:
            List[np.ndarray]: List of embedding vectors, one per input text
        
        Raises:
            ValueError: If texts is empty or contains invalid entries
            Exception: If encoding fails
        
        Example:
            >>> embedder = Embedder()
            >>> texts = ["Text 1", "Text 2", "Text 3"]
            >>> embeddings = embedder.encode_batch(texts)
            >>> print(len(embeddings))
            3
        """
        if not texts or not isinstance(texts, list):
            raise ValueError("Texts must be a non-empty list")
        
        if not all(isinstance(t, str) and t for t in texts):
            raise ValueError("All texts must be non-empty strings")
        
        embeddings = []
        texts_to_encode = []
        text_indices = []
        
        # Check cache for each text
        for idx, text in enumerate(texts):
            if use_cache:
                cache_key = self._get_cache_key(text)
                if cache_key in self.cache:
                    embeddings.append((idx, self.cache[cache_key]))
                    logger.debug(f"Cache hit for batch text {idx}")
                    continue
            
            # Text not in cache, needs encoding
            texts_to_encode.append(text)
            text_indices.append(idx)
        
        # Encode remaining texts in batch
        if texts_to_encode:
            try:
                logger.info(f"Batch encoding {len(texts_to_encode)} texts")
                new_embeddings = self.model.encode(
                    texts_to_encode,
                    convert_to_numpy=True,
                    batch_size=batch_size,
                    show_progress_bar=show_progress_bar
                )
                
                # Store new embeddings in cache and results
                for idx, text, embedding in zip(text_indices, texts_to_encode, new_embeddings):
                    embeddings.append((idx, embedding))
                    
                    if use_cache:
                        cache_key = self._get_cache_key(text)
                        self.cache[cache_key] = embedding
                        logger.debug(f"Cached embedding for batch text {idx}")
                
            except Exception as e:
                logger.error(f"Failed to encode batch: {str(e)}")
                raise
        
        # Sort by original index and return embeddings only
        embeddings.sort(key=lambda x: x[0])
        return [emb for _, emb in embeddings]
    
    def clear_cache(self) -> int:
        """
        Clear the embedding cache.
        
        Returns:
            int: Number of cached embeddings that were cleared
        
        Example:
            >>> embedder = Embedder()
            >>> embedder.encode_text("Test")
            >>> count = embedder.clear_cache()
            >>> print(f"Cleared {count} cached embeddings")
        """
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared {count} cached embeddings")
        return count
    
    def get_cache_size(self) -> int:
        """
        Get the number of embeddings currently in cache.
        
        Returns:
            int: Number of cached embeddings
        
        Example:
            >>> embedder = Embedder()
            >>> embedder.encode_text("Test")
            >>> print(f"Cache size: {embedder.get_cache_size()}")
        """
        return len(self.cache)
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.
        
        Returns:
            int: Dimension of embedding vectors (384 for all-MiniLM-L6-v2)
        
        Example:
            >>> embedder = Embedder()
            >>> print(f"Embedding dimension: {embedder.get_embedding_dimension()}")
        """
        return self.embedding_dim
