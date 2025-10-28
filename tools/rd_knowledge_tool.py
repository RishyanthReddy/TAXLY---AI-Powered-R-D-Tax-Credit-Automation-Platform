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
from datetime import datetime
import logging
import sys
from pathlib import Path
import re

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
    
    Attributes:
        vector_db (VectorDB): The vector database instance
        knowledge_base_path (str): Path to the knowledge base directory
        default_top_k (int): Default number of chunks to retrieve
    
    Example:
        >>> tool = RD_Knowledge_Tool()
        >>> context = tool.query("What are qualified research expenses?", top_k=5)
        >>> print(f"Retrieved {context.chunk_count} chunks")
        >>> print(context.format_for_llm_prompt())
    """
    
    def __init__(
        self,
        knowledge_base_path: str = "./knowledge_base/indexed",
        collection_name: str = "irs_documents",
        default_top_k: int = 3
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
        
        Raises:
            RAGRetrievalError: If vector database initialization fails
        """
        self.knowledge_base_path = knowledge_base_path
        self.default_top_k = default_top_k
        
        try:
            logger.info(
                f"Initializing RD_Knowledge_Tool with knowledge base: {knowledge_base_path}"
            )
            
            # Initialize vector database
            self.vector_db = VectorDB(
                persist_directory=knowledge_base_path,
                collection_name=collection_name
            )
            
            # Get collection info
            collection_info = self.vector_db.get_collection_info()
            total_chunks = collection_info.get('count', 0)
            
            logger.info(
                f"RD_Knowledge_Tool initialized successfully. "
                f"Total chunks available: {total_chunks}"
            )
            
        except Exception as e:
            error_msg = f"Failed to initialize RD_Knowledge_Tool: {str(e)}"
            logger.error(error_msg)
            raise RAGRetrievalError(
                message=error_msg,
                knowledge_base_path=knowledge_base_path,
                error_type="initialization"
            )
    
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
            RAGRetrievalError: If query fails
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
        if not question or not isinstance(question, str):
            raise ValueError("Question must be a non-empty string")
        
        # Use default top_k if not specified
        k = top_k if top_k is not None else self.default_top_k
        
        if k < 1:
            raise ValueError("top_k must be at least 1")
        
        try:
            logger.info(f"Querying knowledge base: '{question[:100]}...', top_k={k}")
            
            # Get total chunks available
            total_chunks_available = self.vector_db.count()
            
            # Query vector database
            results = self.vector_db.query(
                query_text=question,
                top_k=k,
                where=metadata_filter
            )
            
            # Extract results
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            
            # Convert distances to relevance scores (1 - distance for cosine similarity)
            # ChromaDB returns distances where lower is more similar
            # For cosine similarity, distance is in [0, 2], so relevance = 1 - (distance / 2)
            relevance_scores = [max(0.0, min(1.0, 1.0 - (d / 2.0))) for d in distances]
            
            # Build chunks list with all required fields
            chunks = []
            for doc, metadata, relevance in zip(documents, metadatas, relevance_scores):
                chunk = {
                    'text': doc,
                    'source': metadata.get('source', 'Unknown'),
                    'page': metadata.get('page', 1),
                    'relevance_score': round(relevance, 4)
                }
                chunks.append(chunk)
            
            # Create RAGContext object
            context = RAGContext(
                query=question,
                chunks=chunks,
                retrieval_timestamp=datetime.now(),
                total_chunks_available=total_chunks_available,
                retrieval_method="semantic_search"
            )
            
            logger.info(
                f"Retrieved {context.chunk_count} chunks with average relevance "
                f"{context.average_relevance:.2f}"
            )
            
            if context.chunk_count == 0:
                logger.warning(f"No relevant chunks found for query: '{question[:100]}...'")
            
            return context
            
        except ValueError as e:
            # Re-raise validation errors
            raise
        except RAGRetrievalError as e:
            # Re-raise RAG errors
            raise
        except Exception as e:
            error_msg = f"Failed to query knowledge base: {str(e)}"
            logger.error(error_msg)
            raise RAGRetrievalError(
                message=error_msg,
                query=question,
                knowledge_base_path=self.knowledge_base_path,
                error_type="query",
                details={"top_k": k}
            )
    
    def get_total_chunks(self) -> int:
        """
        Get the total number of chunks in the knowledge base.
        
        Returns:
            int: Total number of indexed chunks
        
        Example:
            >>> tool = RD_Knowledge_Tool()
            >>> total = tool.get_total_chunks()
            >>> print(f"Knowledge base contains {total} chunks")
        """
        try:
            return self.vector_db.count()
        except Exception as e:
            logger.error(f"Failed to get total chunks: {str(e)}")
            return 0
    
    def get_knowledge_base_info(self) -> Dict[str, Any]:
        """
        Get information about the knowledge base.
        
        Returns:
            Dict[str, Any]: Information including path, chunk count, and collection details
        
        Example:
            >>> tool = RD_Knowledge_Tool()
            >>> info = tool.get_knowledge_base_info()
            >>> print(f"Knowledge base: {info['path']}")
            >>> print(f"Total chunks: {info['total_chunks']}")
        """
        try:
            collection_info = self.vector_db.get_collection_info()
            return {
                "path": self.knowledge_base_path,
                "total_chunks": collection_info.get('count', 0),
                "collection_name": collection_info.get('name', 'unknown'),
                "embedding_model": collection_info.get('embedding_model', 'unknown'),
                "default_top_k": self.default_top_k
            }
        except Exception as e:
            logger.error(f"Failed to get knowledge base info: {str(e)}")
            return {
                "path": self.knowledge_base_path,
                "error": str(e)
            }
