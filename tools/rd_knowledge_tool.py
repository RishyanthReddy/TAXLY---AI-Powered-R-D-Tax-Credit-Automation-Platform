"""
RD Knowledge Tool Module

This module provides the RAG (Retrieval-Augmented Generation) knowledge tool for
querying IRS documents stored in the vector database. It retrieves relevant context
for R&D tax credit qualification decisions.

Classes:
    RD_Knowledge_Tool: Main class for querying the IRS document knowledge base

Example:
    >>> from tools.rd_knowledge_tool import RD_Knowledge_Tool
    >>> tool = RD_Knowledge_Tool()
    >>> context = tool.query("What is the four-part test for qualified research?")
    >>> print(context.format_for_llm_prompt())
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import logging
import sys
from pathlib import Path
import re
import hashlib
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.vector_db import VectorDB
from models.tax_models import RAGContext
from utils.exceptions import RAGRetrievalError

# Configure logger
logger = logging.getLogger(__name__)


# Technical term synonyms for query expansion
TECHNICAL_SYNONYMS = {
    "r&d": ["research and development", "research", "development", "R&D"],
    "qre": ["qualified research expenditure", "qualified research expense", "QRE"],
    "four-part test": ["four part test", "4-part test", "qualification test", "research test"],
    "technological uncertainty": ["technical uncertainty", "technological challenge", "technical challenge"],
    "process of experimentation": ["experimentation process", "experimental process", "testing process"],
    "business component": ["product component", "business element", "product element"],
    "qualified purpose": ["permitted purpose", "qualified objective", "research purpose"],
    "wage cap": ["wage limitation", "compensation limit", "salary cap"],
    "contractor": ["independent contractor", "third-party contractor", "external contractor"],
    "supply cost": ["supply expense", "material cost", "materials"],
    "software development": ["software engineering", "application development", "programming"],
    "innovation": ["technological advancement", "technical improvement", "new development"],
    "prototype": ["proof of concept", "experimental model", "test version"],
    "algorithm": ["computational method", "calculation method", "processing logic"],
}


# Query rewriting patterns for better retrieval
QUERY_REWRITE_PATTERNS = [
    # Convert questions to declarative statements
    (r"^what is (the |a )?(.+)\?$", r"\2 definition"),
    (r"^what are (the )?(.+)\?$", r"\2 requirements"),
    (r"^how (do|does) (.+)\?$", r"\2 process"),
    (r"^when (is|are) (.+)\?$", r"\2 conditions"),
    (r"^why (.+)\?$", r"\1 rationale"),
    # Expand abbreviations
    (r"\bR&D\b", "research and development"),
    (r"\bQRE\b", "qualified research expenditure"),
    (r"\bIRS\b", "Internal Revenue Service"),
]


class RD_Knowledge_Tool:
    """
    RAG Knowledge Tool for querying IRS documents.
    
    This class provides a high-level interface for querying the vector database
    of IRS documents and returning structured RAGContext objects with relevant
    chunks, metadata, and relevance scores.
    
    Features:
    - Query caching for repeated questions
    - Batch query support for multiple projects
    - Configurable chunk retrieval parameters
    - Query optimization (expansion, rewriting, reranking)
    
    Attributes:
        vector_db (VectorDB): The vector database instance
        knowledge_base_path (str): Path to the knowledge base directory
        default_top_k (int): Default number of chunks to retrieve
        query_cache (Dict): Cache for query results
        cache_ttl (int): Time-to-live for cached queries in seconds
        enable_cache (bool): Whether caching is enabled
    
    Example:
        >>> tool = RD_Knowledge_Tool(enable_cache=True, cache_ttl=3600)
        >>> context = tool.query("What are qualified research expenses?", top_k=5)
        >>> print(f"Retrieved {context.chunk_count} chunks")
        >>> print(context.format_for_llm_prompt())
    """
    
    def __init__(
        self,
        knowledge_base_path: str = "./knowledge_base/indexed",
        collection_name: str = "irs_documents",
        default_top_k: int = 3,
        enable_cache: bool = True,
        cache_ttl: int = 3600
    ):
        """
        Initialize the RD_Knowledge_Tool with a vector database.
        
        Args:
            knowledge_base_path (str): Path to the indexed knowledge base directory.
                                      Default is "./knowledge_base/indexed"
            collection_name (str): Name of the ChromaDB collection to use.
                                  Default is "irs_documents"
            default_top_k (int): Default number of chunks to retrieve per query.
                                Default is 3
            enable_cache (bool): Enable query result caching. Default is True.
            cache_ttl (int): Time-to-live for cached queries in seconds. Default is 3600 (1 hour).
        
        Raises:
            RAGRetrievalError: If vector database initialization fails
        """
        self.knowledge_base_path = knowledge_base_path
        self.default_top_k = default_top_k
        self.collection_name = collection_name
        self.vector_db = None
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.query_cache: Dict[str, Dict[str, Any]] = {}
        
        try:
            logger.info(
                f"Initializing RD_Knowledge_Tool with knowledge base: {knowledge_base_path}, "
                f"cache_enabled={enable_cache}, cache_ttl={cache_ttl}s"
            )
            
            # Initialize vector database
            self.vector_db = VectorDB(
                persist_directory=knowledge_base_path,
                collection_name=collection_name
            )
            
            # Get collection info
            collection_info = self.vector_db.get_collection_info()
            total_chunks = collection_info.get('count', 0)
            
            if total_chunks == 0:
                logger.warning(
                    f"Knowledge base is empty (0 chunks). "
                    f"Queries will return no results until documents are indexed."
                )
            
            logger.info(
                f"RD_Knowledge_Tool initialized successfully. "
                f"Total chunks available: {total_chunks}"
            )
            
        except Exception as e:
            error_msg = f"Failed to initialize RD_Knowledge_Tool: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RAGRetrievalError(
                message=error_msg,
                knowledge_base_path=knowledge_base_path,
                error_type="initialization",
                details={"collection_name": collection_name}
            )
    
    def _generate_cache_key(
        self,
        query: str,
        top_k: int,
        metadata_filter: Optional[Dict[str, Any]],
        enable_query_expansion: bool,
        enable_query_rewriting: bool,
        enable_reranking: bool,
        source_preference: Optional[str]
    ) -> str:
        """
        Generate a unique cache key for a query with its parameters.
        
        Args:
            query: The query string
            top_k: Number of chunks to retrieve
            metadata_filter: Metadata filter dictionary
            enable_query_expansion: Whether query expansion is enabled
            enable_query_rewriting: Whether query rewriting is enabled
            enable_reranking: Whether reranking is enabled
            source_preference: Preferred source for reranking
        
        Returns:
            str: MD5 hash of the query parameters
        """
        # Create a dictionary of all parameters
        params = {
            'query': query.lower().strip(),
            'top_k': top_k,
            'metadata_filter': json.dumps(metadata_filter, sort_keys=True) if metadata_filter else None,
            'expansion': enable_query_expansion,
            'rewriting': enable_query_rewriting,
            'reranking': enable_reranking,
            'source_pref': source_preference
        }
        
        # Generate hash
        params_str = json.dumps(params, sort_keys=True)
        cache_key = hashlib.md5(params_str.encode()).hexdigest()
        
        return cache_key
    
    def _get_cached_result(self, cache_key: str) -> Optional[RAGContext]:
        """
        Retrieve a cached query result if available and not expired.
        
        Args:
            cache_key: The cache key for the query
        
        Returns:
            Optional[RAGContext]: Cached result if available and valid, None otherwise
        """
        if not self.enable_cache:
            return None
        
        if cache_key not in self.query_cache:
            return None
        
        cached_entry = self.query_cache[cache_key]
        cached_time = cached_entry['timestamp']
        cached_result = cached_entry['result']
        
        # Check if cache entry has expired
        age = (datetime.now() - cached_time).total_seconds()
        if age > self.cache_ttl:
            # Remove expired entry
            del self.query_cache[cache_key]
            logger.debug(f"Cache entry expired (age: {age:.1f}s)")
            return None
        
        logger.info(f"Cache hit! Retrieved result from cache (age: {age:.1f}s)")
        return cached_result
    
    def _cache_result(self, cache_key: str, result: RAGContext) -> None:
        """
        Cache a query result.
        
        Args:
            cache_key: The cache key for the query
            result: The RAGContext result to cache
        """
        if not self.enable_cache:
            return
        
        self.query_cache[cache_key] = {
            'timestamp': datetime.now(),
            'result': result
        }
        
        logger.debug(f"Cached query result (cache size: {len(self.query_cache)})")
    
    def clear_cache(self) -> int:
        """
        Clear all cached query results.
        
        Returns:
            int: Number of cache entries cleared
        """
        count = len(self.query_cache)
        self.query_cache.clear()
        logger.info(f"Cleared {count} cached query results")
        return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the query cache.
        
        Returns:
            Dict[str, Any]: Cache statistics including size, oldest entry age, etc.
        """
        if not self.query_cache:
            return {
                'enabled': self.enable_cache,
                'size': 0,
                'ttl_seconds': self.cache_ttl,
                'oldest_entry_age_seconds': None,
                'newest_entry_age_seconds': None
            }
        
        now = datetime.now()
        ages = [(now - entry['timestamp']).total_seconds() for entry in self.query_cache.values()]
        
        return {
            'enabled': self.enable_cache,
            'size': len(self.query_cache),
            'ttl_seconds': self.cache_ttl,
            'oldest_entry_age_seconds': max(ages),
            'newest_entry_age_seconds': min(ages),
            'average_age_seconds': sum(ages) / len(ages)
        }
    
    def _expand_query(self, query: str) -> List[str]:
        """
        Expand query with synonyms for technical terms.
        
        Args:
            query (str): Original query text
        
        Returns:
            List[str]: List of expanded query variations
        
        Example:
            >>> tool = RD_Knowledge_Tool()
            >>> expansions = tool._expand_query("What is QRE?")
            >>> # Returns variations with "qualified research expenditure", etc.
        """
        expanded_queries = [query]  # Always include original
        query_lower = query.lower()
        
        # Find matching technical terms and add synonym variations
        for term, synonyms in TECHNICAL_SYNONYMS.items():
            if term in query_lower:
                # Create variations by replacing the term with each synonym
                for synonym in synonyms:
                    if synonym.lower() != term:
                        # Case-insensitive replacement
                        pattern = re.compile(re.escape(term), re.IGNORECASE)
                        expanded = pattern.sub(synonym, query)
                        if expanded not in expanded_queries:
                            expanded_queries.append(expanded)
        
        logger.debug(f"Expanded query into {len(expanded_queries)} variations")
        return expanded_queries
    
    def _rewrite_query(self, query: str) -> str:
        """
        Rewrite query for better retrieval using pattern matching.
        
        Args:
            query (str): Original query text
        
        Returns:
            str: Rewritten query
        
        Example:
            >>> tool = RD_Knowledge_Tool()
            >>> rewritten = tool._rewrite_query("What is the four-part test?")
            >>> # Returns "four-part test definition"
        """
        rewritten = query.strip()
        
        # Apply rewrite patterns
        for pattern, replacement in QUERY_REWRITE_PATTERNS:
            rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)
        
        if rewritten != query:
            logger.debug(f"Rewrote query: '{query}' -> '{rewritten}'")
        
        return rewritten
    
    def _rerank_results(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        source_preference: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Re-rank results based on metadata and relevance.
        
        This method applies additional ranking logic beyond semantic similarity:
        - Boosts results from preferred sources
        - Prioritizes chunks with higher page numbers (often contain detailed guidance)
        - Adjusts scores based on text length (prefer substantial chunks)
        
        Args:
            chunks (List[Dict[str, Any]]): List of retrieved chunks with metadata
            query (str): Original query for context
            source_preference (Optional[str]): Preferred document source to boost
        
        Returns:
            List[Dict[str, Any]]: Re-ranked chunks
        
        Example:
            >>> chunks = [{"text": "...", "source": "Form 6765", "relevance_score": 0.8}]
            >>> reranked = tool._rerank_results(chunks, "wage cap", source_preference="Form 6765")
        """
        if not chunks:
            return chunks
        
        # Create a copy to avoid modifying original
        ranked_chunks = []
        
        for chunk in chunks:
            score = chunk['relevance_score']
            boost_factors = []
            
            # Source preference boost (20% increase)
            if source_preference and source_preference.lower() in chunk['source'].lower():
                score *= 1.2
                boost_factors.append(f"source_match:{source_preference}")
            
            # Boost Form 6765 and CFR documents (authoritative sources) by 10%
            if any(auth in chunk['source'] for auth in ['Form 6765', 'CFR', 'Title 26']):
                score *= 1.1
                boost_factors.append("authoritative_source")
            
            # Boost chunks with substantial content (> 200 chars) by 5%
            if len(chunk['text']) > 200:
                score *= 1.05
                boost_factors.append("substantial_content")
            
            # Penalize very short chunks (< 50 chars) by 10%
            if len(chunk['text']) < 50:
                score *= 0.9
                boost_factors.append("short_content_penalty")
            
            # Cap score at 1.0
            score = min(1.0, score)
            
            # Create new chunk with adjusted score
            reranked_chunk = chunk.copy()
            reranked_chunk['relevance_score'] = round(score, 4)
            reranked_chunk['original_score'] = chunk['relevance_score']
            if boost_factors:
                reranked_chunk['boost_factors'] = boost_factors
            
            ranked_chunks.append(reranked_chunk)
        
        # Sort by adjusted relevance score
        ranked_chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        logger.debug(f"Re-ranked {len(ranked_chunks)} chunks")
        
        return ranked_chunks
    
    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        enable_query_expansion: bool = True,
        enable_query_rewriting: bool = True,
        enable_reranking: bool = True,
        source_preference: Optional[str] = None
    ) -> RAGContext:
        """
        Query the knowledge base with a natural language question.
        
        This method retrieves the most relevant IRS document chunks for the given
        question and returns them as a structured RAGContext object with relevance
        scores and metadata. Includes query optimization features:
        - Query expansion with technical term synonyms
        - Query rewriting for better retrieval
        - Re-ranking based on metadata and source preference
        - Document source filtering
        
        Args:
            question (str): Natural language question to query the knowledge base
            top_k (Optional[int]): Number of chunks to retrieve. If None, uses default_top_k.
            metadata_filter (Optional[Dict[str, Any]]): Optional metadata filter to restrict
                                                        results to specific sources.
                                                        Example: {"source": "Form 6765"}
            enable_query_expansion (bool): Enable query expansion with synonyms. Default True.
            enable_query_rewriting (bool): Enable query rewriting for better retrieval. Default True.
            enable_reranking (bool): Enable re-ranking of results. Default True.
            source_preference (Optional[str]): Preferred document source for boosting in re-ranking.
                                              Example: "Form 6765"
        
        Returns:
            RAGContext: Structured context object containing retrieved chunks with metadata
        
        Raises:
            RAGRetrievalError: If query fails or vector database is unavailable
            ValueError: If question is empty or invalid
        
        Example:
            >>> tool = RD_Knowledge_Tool()
            >>> # Basic query
            >>> context = tool.query("What is the four-part test?", top_k=3)
            >>> 
            >>> # Query with source filtering
            >>> context = tool.query(
            ...     "wage limitations",
            ...     metadata_filter={"source": "Form 6765"},
            ...     source_preference="Form 6765"
            ... )
            >>> 
            >>> # Query without optimization (for comparison)
            >>> context = tool.query(
            ...     "QRE definition",
            ...     enable_query_expansion=False,
            ...     enable_query_rewriting=False,
            ...     enable_reranking=False
            ... )
        """
        # Validate inputs
        if not question or not isinstance(question, str):
            logger.error("Invalid query: question must be a non-empty string")
            raise ValueError("Question must be a non-empty string")
        
        # Use default top_k if not specified
        k = top_k if top_k is not None else self.default_top_k
        
        if k < 1:
            logger.error(f"Invalid top_k value: {k}")
            raise ValueError("top_k must be at least 1")
        
        # Check cache first
        cache_key = self._generate_cache_key(
            query=question,
            top_k=k,
            metadata_filter=metadata_filter,
            enable_query_expansion=enable_query_expansion,
            enable_query_rewriting=enable_query_rewriting,
            enable_reranking=enable_reranking,
            source_preference=source_preference
        )
        
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Check if vector database is available
        if self.vector_db is None:
            error_msg = (
                "Vector database is not initialized. Cannot perform query. "
                "Please ensure the knowledge base is properly initialized."
            )
            logger.error(error_msg)
            raise RAGRetrievalError(
                message=error_msg,
                query=question,
                knowledge_base_path=self.knowledge_base_path,
                error_type="connection_failure",
                details={"top_k": k, "collection_name": self.collection_name}
            )
        
        # Log retrieval attempt
        logger.info(
            f"RAG retrieval attempt - Query: '{question[:100]}...', top_k={k}, "
            f"expansion={enable_query_expansion}, rewriting={enable_query_rewriting}, "
            f"reranking={enable_reranking}, metadata_filter={metadata_filter}"
        )
        
        try:
            # Get total chunks available (with fallback)
            try:
                total_chunks_available = self.vector_db.count()
                logger.debug(f"Total chunks available in knowledge base: {total_chunks_available}")
                
                # Handle empty knowledge base
                if total_chunks_available == 0:
                    logger.warning(
                        f"Knowledge base is empty (0 chunks). "
                        f"Returning empty context for query: '{question[:100]}...'"
                    )
                    return RAGContext(
                        query=question,
                        chunks=[],
                        retrieval_timestamp=datetime.now(),
                        total_chunks_available=0,
                        retrieval_method="semantic_search"
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to get chunk count from vector database: {str(e)}. "
                    f"Continuing with query attempt."
                )
                total_chunks_available = -1  # Unknown
            
            # Step 1: Query rewriting (if enabled)
            processed_query = question
            if enable_query_rewriting:
                try:
                    processed_query = self._rewrite_query(question)
                    if processed_query != question:
                        logger.debug(f"Query rewritten: '{question}' -> '{processed_query}'")
                except Exception as e:
                    logger.warning(f"Query rewriting failed: {str(e)}. Using original query.")
                    processed_query = question
            
            # Step 2: Query expansion (if enabled)
            query_variations = [processed_query]
            if enable_query_expansion:
                try:
                    query_variations = self._expand_query(processed_query)
                    logger.debug(f"Query expanded into {len(query_variations)} variations")
                except Exception as e:
                    logger.warning(f"Query expansion failed: {str(e)}. Using single query.")
                    query_variations = [processed_query]
            
            # Step 3: Execute queries and collect results
            all_chunks = {}  # Use dict to deduplicate by text
            query_errors = []  # Track errors from individual query variations
            
            # Retrieve more results initially if we're doing expansion (to account for duplicates)
            retrieval_k = k * 2 if enable_query_expansion and len(query_variations) > 1 else k
            
            for i, query_var in enumerate(query_variations):
                try:
                    logger.debug(f"Executing query variation {i+1}/{len(query_variations)}: '{query_var[:50]}...'")
                    
                    # Query vector database
                    results = self.vector_db.query(
                        query_text=query_var,
                        top_k=retrieval_k,
                        where=metadata_filter
                    )
                    
                    # Extract results
                    documents = results.get('documents', [[]])[0]
                    metadatas = results.get('metadatas', [[]])[0]
                    distances = results.get('distances', [[]])[0]
                    
                    logger.debug(
                        f"Query variation {i+1} returned {len(documents)} documents "
                        f"with distances: {distances[:3] if distances else []}"
                    )
                    
                    # Convert distances to relevance scores
                    relevance_scores = [max(0.0, min(1.0, 1.0 - (d / 2.0))) for d in distances]
                    
                    # Collect chunks (deduplicate by text, keep highest score)
                    for doc, metadata, relevance in zip(documents, metadatas, relevance_scores):
                        if doc not in all_chunks or all_chunks[doc]['relevance_score'] < relevance:
                            all_chunks[doc] = {
                                'text': doc,
                                'source': metadata.get('source', 'Unknown'),
                                'page': metadata.get('page', 1),
                                'relevance_score': round(relevance, 4)
                            }
                
                except Exception as e:
                    error_msg = f"Query variation {i+1} failed: {query_var[:50]}... - {str(e)}"
                    logger.warning(error_msg)
                    query_errors.append(error_msg)
                    continue
            
            # Check if all query variations failed
            if not all_chunks and query_errors:
                error_msg = (
                    f"All query variations failed. "
                    f"Attempted {len(query_variations)} variations. "
                    f"Errors: {'; '.join(query_errors[:3])}"
                )
                logger.error(error_msg)
                raise RAGRetrievalError(
                    message=error_msg,
                    query=question,
                    knowledge_base_path=self.knowledge_base_path,
                    error_type="query_execution_failure",
                    details={
                        "top_k": k,
                        "query_variations_attempted": len(query_variations),
                        "errors": query_errors
                    }
                )
            
            # Convert to list
            chunks = list(all_chunks.values())
            logger.debug(f"Collected {len(chunks)} unique chunks after deduplication")
            
            # Step 4: Re-ranking (if enabled)
            if enable_reranking and chunks:
                try:
                    chunks = self._rerank_results(chunks, question, source_preference)
                    logger.debug(f"Re-ranked {len(chunks)} chunks")
                except Exception as e:
                    logger.warning(f"Re-ranking failed: {str(e)}. Using original ranking.")
                    # Just sort by relevance score as fallback
                    chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
            else:
                # Just sort by relevance score
                chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Step 5: Limit to top_k results
            chunks = chunks[:k]
            
            # Determine retrieval method based on optimizations used
            retrieval_methods = ["semantic_search"]
            if enable_query_expansion:
                retrieval_methods.append("query_expansion")
            if enable_query_rewriting:
                retrieval_methods.append("query_rewriting")
            if enable_reranking:
                retrieval_methods.append("metadata_reranking")
            
            retrieval_method = "+".join(retrieval_methods)
            
            # Create RAGContext object
            context = RAGContext(
                query=question,
                chunks=chunks,
                retrieval_timestamp=datetime.now(),
                total_chunks_available=total_chunks_available if total_chunks_available >= 0 else len(chunks),
                retrieval_method=retrieval_method
            )
            
            # Log retrieval results
            if context.chunk_count == 0:
                logger.warning(
                    f"RAG retrieval returned 0 chunks for query: '{question[:100]}...'. "
                    f"This may indicate: (1) no relevant documents in knowledge base, "
                    f"(2) query too specific, or (3) metadata filter too restrictive."
                )
            else:
                logger.info(
                    f"RAG retrieval successful - Retrieved {context.chunk_count} chunks "
                    f"with average relevance {context.average_relevance:.2f} "
                    f"using {retrieval_method}"
                )
                
                # Log top result for debugging
                if chunks:
                    top_chunk = chunks[0]
                    logger.debug(
                        f"Top result: source='{top_chunk['source']}', "
                        f"page={top_chunk['page']}, "
                        f"relevance={top_chunk['relevance_score']:.4f}, "
                        f"text_preview='{top_chunk['text'][:100]}...'"
                    )
            
            # Cache the result before returning
            self._cache_result(cache_key, context)
            
            return context
            
        except ValueError as e:
            # Re-raise validation errors (already logged)
            raise
        except RAGRetrievalError as e:
            # Re-raise RAG errors (already logged)
            raise
        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = (
                f"Unexpected error during RAG retrieval: {str(e)}. "
                f"Query: '{question[:100]}...'"
            )
            logger.error(error_msg, exc_info=True)
            raise RAGRetrievalError(
                message=error_msg,
                query=question,
                knowledge_base_path=self.knowledge_base_path,
                error_type="unexpected_error",
                details={
                    "top_k": k,
                    "metadata_filter": metadata_filter,
                    "exception_type": type(e).__name__
                }
            )
    
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
    ) -> Dict[str, Any]:
        """
        Query the knowledge base with multiple questions in batch.
        
        This method processes multiple queries efficiently, leveraging caching
        to avoid redundant retrievals for duplicate or similar questions.
        
        Args:
            questions (List[str]): List of natural language questions to query
            top_k (Optional[int]): Number of chunks to retrieve per query. If None, uses default_top_k.
            metadata_filter (Optional[Dict[str, Any]]): Optional metadata filter for all queries
            enable_query_expansion (bool): Enable query expansion with synonyms. Default True.
            enable_query_rewriting (bool): Enable query rewriting for better retrieval. Default True.
            enable_reranking (bool): Enable re-ranking of results. Default True.
            source_preference (Optional[str]): Preferred document source for boosting in re-ranking
            continue_on_error (bool): If True, continues processing even if some queries fail. Default True.
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - 'results': List of RAGContext objects (one per question)
                - 'questions': Original list of questions
                - 'total_queries': Total number of queries processed
                - 'successful_queries': Number of successful queries
                - 'failed_queries': Number of failed queries
                - 'cache_hits': Number of queries served from cache
                - 'errors': List of error information for failed queries
        
        Raises:
            ValueError: If questions list is empty or invalid
            RAGRetrievalError: If all queries fail and continue_on_error is False
        
        Example:
            >>> tool = RD_Knowledge_Tool()
            >>> questions = [
            ...     "What is the four-part test?",
            ...     "What are qualified research expenses?",
            ...     "What is a process of experimentation?"
            ... ]
            >>> batch_result = tool.batch_query(questions, top_k=3)
            >>> print(f"Processed {batch_result['successful_queries']} queries")
            >>> print(f"Cache hits: {batch_result['cache_hits']}")
            >>> 
            >>> # Access individual results
            >>> for question, context in zip(questions, batch_result['results']):
            ...     if context is not None:
            ...         print(f"{question}: {context.chunk_count} chunks")
        """
        # Validate inputs
        if not questions or not isinstance(questions, list):
            raise ValueError("questions must be a non-empty list")
        
        if not all(isinstance(q, str) and q.strip() for q in questions):
            raise ValueError("All questions must be non-empty strings")
        
        logger.info(
            f"Starting batch query: {len(questions)} questions, "
            f"top_k={top_k or self.default_top_k}, "
            f"continue_on_error={continue_on_error}"
        )
        
        results = []
        errors = []
        cache_hits = 0
        successful_queries = 0
        failed_queries = 0
        
        # Process each question
        for i, question in enumerate(questions, 1):
            try:
                logger.debug(f"Processing batch query {i}/{len(questions)}: '{question[:50]}...'")
                
                # Check if this will be a cache hit (before calling query)
                cache_key = self._generate_cache_key(
                    query=question,
                    top_k=top_k or self.default_top_k,
                    metadata_filter=metadata_filter,
                    enable_query_expansion=enable_query_expansion,
                    enable_query_rewriting=enable_query_rewriting,
                    enable_reranking=enable_reranking,
                    source_preference=source_preference
                )
                
                is_cache_hit = self._get_cached_result(cache_key) is not None
                
                # Execute query
                context = self.query(
                    question=question,
                    top_k=top_k,
                    metadata_filter=metadata_filter,
                    enable_query_expansion=enable_query_expansion,
                    enable_query_rewriting=enable_query_rewriting,
                    enable_reranking=enable_reranking,
                    source_preference=source_preference
                )
                
                results.append(context)
                successful_queries += 1
                
                if is_cache_hit:
                    cache_hits += 1
                
                logger.debug(
                    f"Batch query {i} successful: {context.chunk_count} chunks, "
                    f"cache_hit={is_cache_hit}"
                )
            
            except Exception as e:
                failed_queries += 1
                error_info = {
                    'question': question,
                    'question_index': i - 1,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                errors.append(error_info)
                
                logger.error(
                    f"Batch query {i} failed: '{question[:50]}...' - {str(e)}"
                )
                
                if continue_on_error:
                    # Add None as placeholder for failed query
                    results.append(None)
                else:
                    # Stop processing and raise error
                    raise RAGRetrievalError(
                        message=f"Batch query failed at question {i}: {str(e)}",
                        query=question,
                        knowledge_base_path=self.knowledge_base_path,
                        error_type="batch_query_failure",
                        details={
                            'question_index': i - 1,
                            'total_questions': len(questions),
                            'successful_so_far': successful_queries
                        }
                    )
        
        # Calculate statistics
        cache_hit_rate = (cache_hits / len(questions)) * 100 if questions else 0
        success_rate = (successful_queries / len(questions)) * 100 if questions else 0
        
        logger.info(
            f"Batch query complete: {successful_queries}/{len(questions)} successful "
            f"({success_rate:.1f}%), {cache_hits} cache hits ({cache_hit_rate:.1f}%)"
        )
        
        if errors:
            logger.warning(f"Batch query had {failed_queries} failures")
        
        return {
            'results': results,
            'questions': questions,
            'total_queries': len(questions),
            'successful_queries': successful_queries,
            'failed_queries': failed_queries,
            'cache_hits': cache_hits,
            'cache_hit_rate': cache_hit_rate,
            'success_rate': success_rate,
            'errors': errors
        }
    
    def get_total_chunks(self) -> int:
        """
        Get the total number of chunks in the knowledge base.
        
        Returns:
            int: Total number of indexed chunks, or 0 if unavailable
        
        Example:
            >>> tool = RD_Knowledge_Tool()
            >>> total = tool.get_total_chunks()
            >>> print(f"Knowledge base contains {total} chunks")
        """
        if self.vector_db is None:
            logger.error("Vector database is not initialized. Cannot get chunk count.")
            return 0
        
        try:
            count = self.vector_db.count()
            logger.debug(f"Retrieved chunk count: {count}")
            return count
        except Exception as e:
            logger.error(f"Failed to get total chunks: {str(e)}", exc_info=True)
            return 0
    
    def get_knowledge_base_info(self) -> Dict[str, Any]:
        """
        Get information about the knowledge base.
        
        Returns:
            Dict[str, Any]: Information including path, chunk count, and collection details.
                           Returns error information if retrieval fails.
        
        Example:
            >>> tool = RD_Knowledge_Tool()
            >>> info = tool.get_knowledge_base_info()
            >>> print(f"Knowledge base: {info['path']}")
            >>> print(f"Total chunks: {info['total_chunks']}")
        """
        base_info = {
            "path": self.knowledge_base_path,
            "collection_name": self.collection_name,
            "default_top_k": self.default_top_k
        }
        
        if self.vector_db is None:
            logger.error("Vector database is not initialized. Cannot get knowledge base info.")
            return {
                **base_info,
                "status": "error",
                "error": "Vector database not initialized",
                "total_chunks": 0
            }
        
        try:
            collection_info = self.vector_db.get_collection_info()
            logger.debug(f"Retrieved knowledge base info: {collection_info}")
            
            return {
                **base_info,
                "status": "available",
                "total_chunks": collection_info.get('count', 0),
                "embedding_model": collection_info.get('embedding_model', 'unknown')
            }
        except Exception as e:
            logger.error(f"Failed to get knowledge base info: {str(e)}", exc_info=True)
            return {
                **base_info,
                "status": "error",
                "error": str(e),
                "total_chunks": 0
            }
    
    def format_for_llm(
        self,
        context: RAGContext,
        include_relevance_scores: bool = True,
        include_metadata: bool = True,
        max_chunks: Optional[int] = None,
        prompt_template: Optional[str] = None
    ) -> str:
        """
        Format retrieved RAG context for LLM consumption with structured prompt template.
        
        This method creates a comprehensive, structured prompt that includes:
        - Retrieved IRS document chunks with source citations
        - Relevance scores to help LLM assess context quality
        - Metadata about the retrieval process
        - Optional custom prompt template
        
        The formatted output is optimized for LLM reasoning about R&D tax credit
        qualification decisions, providing clear context boundaries and citation
        information for audit trail purposes.
        
        Args:
            context (RAGContext): The RAG context object containing retrieved chunks
            include_relevance_scores (bool): Whether to include relevance scores for each chunk.
                                            Default True. Helps LLM assess context quality.
            include_metadata (bool): Whether to include retrieval metadata (timestamp, method, etc.).
                                    Default True.
            max_chunks (Optional[int]): Maximum number of chunks to include in the formatted output.
                                       If None, includes all chunks. Uses top-ranked chunks.
            prompt_template (Optional[str]): Custom prompt template with placeholders:
                                            {context} - replaced with formatted chunks
                                            {query} - replaced with original query
                                            {chunk_count} - replaced with number of chunks
                                            {citations} - replaced with citation list
                                            If None, uses default template.
        
        Returns:
            str: Formatted prompt string ready for LLM consumption
        
        Raises:
            ValueError: If context is invalid or empty
        
        Example:
            >>> tool = RD_Knowledge_Tool()
            >>> context = tool.query("What is the four-part test?", top_k=3)
            >>> 
            >>> # Basic formatting with all features
            >>> formatted = tool.format_for_llm(context)
            >>> print(formatted)
            >>> 
            >>> # Formatting without relevance scores
            >>> formatted = tool.format_for_llm(context, include_relevance_scores=False)
            >>> 
            >>> # Formatting with custom template
            >>> custom_template = '''
            ... Based on the following IRS guidance:
            ... {context}
            ... 
            ... Please analyze whether the project qualifies for R&D tax credit.
            ... '''
            >>> formatted = tool.format_for_llm(context, prompt_template=custom_template)
            >>> 
            >>> # Limit to top 2 chunks only
            >>> formatted = tool.format_for_llm(context, max_chunks=2)
        """
        if not isinstance(context, RAGContext):
            raise ValueError("context must be a RAGContext object")
        
        if context.chunk_count == 0:
            logger.warning("Formatting empty RAG context for LLM")
            return (
                "=== NO RELEVANT IRS GUIDANCE FOUND ===\n\n"
                f"Query: {context.query}\n\n"
                "No relevant IRS document excerpts were found for this query. "
                "The LLM should proceed with general R&D tax credit knowledge but "
                "flag the response as having lower confidence due to lack of specific guidance.\n\n"
                "=== END CONTEXT ==="
            )
        
        # Sort chunks by relevance score (highest first)
        sorted_chunks = sorted(
            context.chunks,
            key=lambda x: x['relevance_score'],
            reverse=True
        )
        
        # Limit chunks if specified
        if max_chunks and max_chunks > 0:
            sorted_chunks = sorted_chunks[:max_chunks]
            logger.debug(f"Limited context to top {max_chunks} chunks")
        
        # Build formatted context sections
        formatted_parts = []
        
        # Header
        formatted_parts.append("=" * 70)
        formatted_parts.append("IRS GUIDANCE CONTEXT FOR R&D TAX CREDIT QUALIFICATION")
        formatted_parts.append("=" * 70)
        formatted_parts.append("")
        
        # Query information
        formatted_parts.append(f"Query: {context.query}")
        formatted_parts.append(f"Retrieved: {len(sorted_chunks)} relevant document excerpt(s)")
        
        if include_metadata:
            formatted_parts.append(f"Retrieval Method: {context.retrieval_method}")
            formatted_parts.append(f"Average Relevance: {context.average_relevance:.2f}")
            formatted_parts.append(
                f"Retrieved At: {context.retrieval_timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        formatted_parts.append("")
        formatted_parts.append("-" * 70)
        formatted_parts.append("")
        
        # Format each chunk
        for i, chunk in enumerate(sorted_chunks, 1):
            formatted_parts.append(f"EXCERPT #{i}")
            formatted_parts.append(f"Source: {chunk['source']}")
            formatted_parts.append(f"Page: {chunk['page']}")
            
            if include_relevance_scores:
                # Format relevance score with quality indicator
                score = chunk['relevance_score']
                if score >= 0.9:
                    quality = "Very High"
                elif score >= 0.8:
                    quality = "High"
                elif score >= 0.7:
                    quality = "Medium"
                else:
                    quality = "Low"
                
                formatted_parts.append(f"Relevance Score: {score:.2f} ({quality} confidence)")
            
            formatted_parts.append("")
            formatted_parts.append(chunk['text'])
            formatted_parts.append("")
            
            # Add separator between chunks (except after last one)
            if i < len(sorted_chunks):
                formatted_parts.append("-" * 70)
                formatted_parts.append("")
        
        # Footer with citations
        formatted_parts.append("=" * 70)
        formatted_parts.append("CITATIONS")
        formatted_parts.append("=" * 70)
        formatted_parts.append("")
        
        citations = context.extract_citations()
        if max_chunks and max_chunks > 0:
            # Extract citations only from the chunks we included
            citations = []
            seen = set()
            for chunk in sorted_chunks:
                citation = f"{chunk['source']}, Page {chunk['page']}"
                if citation not in seen:
                    citations.append(citation)
                    seen.add(citation)
        
        for i, citation in enumerate(citations, 1):
            formatted_parts.append(f"{i}. {citation}")
        
        formatted_parts.append("")
        formatted_parts.append("=" * 70)
        formatted_parts.append("END IRS GUIDANCE CONTEXT")
        formatted_parts.append("=" * 70)
        
        # Join all parts
        formatted_context = "\n".join(formatted_parts)
        
        # Apply custom template if provided
        if prompt_template:
            try:
                formatted_output = prompt_template.format(
                    context=formatted_context,
                    query=context.query,
                    chunk_count=len(sorted_chunks),
                    citations="\n".join(f"{i}. {c}" for i, c in enumerate(citations, 1))
                )
                logger.debug("Applied custom prompt template")
                return formatted_output
            except KeyError as e:
                logger.warning(
                    f"Custom template missing placeholder {e}, using default format"
                )
                return formatted_context
        
        logger.info(
            f"Formatted RAG context for LLM: {len(sorted_chunks)} chunks, "
            f"{len(formatted_context)} characters"
        )
        
        return formatted_context
