"""
Qualification Enhancer for R&D Tax Credit Pipeline

This module enhances the qualification process by integrating You.com Search and News APIs
alongside the GLM reasoner to provide additional context and validation during qualification.

The enhancer orchestrates parallel API calls to:
- You.com News API: Recent IRS updates and tax law announcements
- You.com Search API: Specific IRS guidance and compliance information
- GLM Reasoner: AI-powered analysis of search and news results

All operations are non-blocking and include comprehensive error handling with timeouts.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime

from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.logger import get_tool_logger

logger = get_tool_logger("qualification_enhancer")


@dataclass
class EnhancementResult:
    """
    Structured result from qualification enhancement.
    
    Attributes:
        news_items: List of recent IRS news articles
        search_results: List of relevant IRS guidance documents
        glm_summary: AI-generated insights on how recent guidance affects qualification
        execution_time_ms: Total execution time in milliseconds
        errors: List of non-blocking errors encountered during enhancement
    """
    news_items: List[Dict[str, Any]] = field(default_factory=list)
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    glm_summary: str = ""
    execution_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "news_items": self.news_items,
            "search_results": self.search_results,
            "glm_summary": self.glm_summary,
            "execution_time_ms": self.execution_time_ms,
            "errors": self.errors
        }


class QualificationEnhancer:
    """
    Enhances R&D qualification with You.com APIs and GLM reasoner.
    
    This class orchestrates parallel API calls to You.com News and Search endpoints,
    then uses GLM reasoner to analyze the results and provide AI-powered insights
    on how recent guidance affects qualification decisions.
    
    All operations are non-blocking with comprehensive error handling and timeouts:
    - You.com News API: 5 second timeout
    - You.com Search API: 5 second timeout
    - GLM Reasoner: 30 second timeout
    - Total enhancement budget: 45 seconds maximum
    
    Example:
        >>> from utils.config import get_config
        >>> config = get_config()
        >>> youcom_client = YouComClient(api_key=config.youcom_api_key)
        >>> glm_reasoner = GLMReasoner(api_key=config.openrouter_api_key)
        >>> enhancer = QualificationEnhancer(youcom_client, glm_reasoner)
        >>> 
        >>> result = await enhancer.enhance_qualification(
        ...     project_name="API Optimization",
        ...     project_description="Improve API response times",
        ...     tax_year=2025
        ... )
        >>> print(f"Found {len(result.news_items)} news items")
        >>> print(f"Found {len(result.search_results)} search results")
        >>> print(f"GLM Summary: {result.glm_summary}")
    """
    
    def __init__(
        self,
        youcom_client: YouComClient,
        glm_reasoner: GLMReasoner,
        news_timeout: float = 5.0,
        search_timeout: float = 5.0,
        glm_timeout: float = 30.0
    ):
        """
        Initialize QualificationEnhancer.
        
        Args:
            youcom_client: Initialized You.com API client
            glm_reasoner: Initialized GLM reasoner
            news_timeout: Timeout for You.com News API in seconds (default: 5.0)
            search_timeout: Timeout for You.com Search API in seconds (default: 5.0)
            glm_timeout: Timeout for GLM reasoner in seconds (default: 30.0)
        """
        self.youcom_client = youcom_client
        self.glm_reasoner = glm_reasoner
        self.news_timeout = news_timeout
        self.search_timeout = search_timeout
        self.glm_timeout = glm_timeout
        
        logger.info(
            f"Initialized QualificationEnhancer "
            f"(news_timeout={news_timeout}s, search_timeout={search_timeout}s, "
            f"glm_timeout={glm_timeout}s)"
        )
    
    async def enhance_qualification(
        self,
        project_name: str,
        project_description: str,
        tax_year: int
    ) -> EnhancementResult:
        """
        Enhance qualification with search, news, and AI analysis.
        
        This method orchestrates the enhancement process:
        1. Parallel API calls to You.com News and Search (with timeouts)
        2. GLM reasoner analysis of the results (with timeout)
        3. Structured result compilation
        
        All operations are non-blocking. If any API fails, the enhancement
        continues with partial results and logs the error.
        
        Args:
            project_name: Name of the project being qualified
            project_description: Description of the project's technical activities
            tax_year: Tax year for qualification (e.g., 2025)
        
        Returns:
            EnhancementResult with news, search results, GLM insights, and any errors
        
        Example:
            >>> result = await enhancer.enhance_qualification(
            ...     project_name="API Optimization",
            ...     project_description="Improve API response times through algorithm optimization",
            ...     tax_year=2025
            ... )
            >>> if result.errors:
            ...     print(f"Encountered {len(result.errors)} non-blocking errors")
            >>> print(f"Execution time: {result.execution_time_ms:.2f}ms")
        """
        start_time = datetime.now()
        result = EnhancementResult()
        
        logger.info(
            f"Starting qualification enhancement for project: {project_name} "
            f"(tax_year={tax_year})"
        )
        
        # Step 1: Parallel API calls to You.com News and Search
        news_items, search_results = await self._fetch_youcom_data(
            project_name=project_name,
            project_description=project_description,
            tax_year=tax_year,
            result=result
        )
        
        result.news_items = news_items
        result.search_results = search_results
        
        # Step 2: GLM reasoner analysis (only if we have data to analyze)
        if news_items or search_results:
            glm_summary = await self._analyze_with_glm(
                project_name=project_name,
                project_description=project_description,
                news_items=news_items,
                search_results=search_results,
                result=result
            )
            result.glm_summary = glm_summary
        else:
            logger.warning("No news or search results to analyze with GLM")
            result.glm_summary = "No recent guidance or news found for analysis."
        
        # Calculate execution time
        end_time = datetime.now()
        result.execution_time_ms = (end_time - start_time).total_seconds() * 1000
        
        logger.info(
            f"Enhancement complete: {len(result.news_items)} news items, "
            f"{len(result.search_results)} search results, "
            f"{len(result.errors)} errors, "
            f"execution_time={result.execution_time_ms:.2f}ms"
        )
        
        return result
    
    async def _fetch_youcom_data(
        self,
        project_name: str,
        project_description: str,
        tax_year: int,
        result: EnhancementResult
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch data from You.com News and Search APIs in parallel.
        
        Args:
            project_name: Name of the project
            project_description: Description of the project
            tax_year: Tax year for qualification
            result: EnhancementResult to store errors
        
        Returns:
            Tuple of (news_items, search_results)
        """
        # Create search queries
        news_query = f"IRS R&D tax credit updates {tax_year}"
        search_query = f"IRS R&D tax credit software development guidance {tax_year}"
        
        logger.debug(f"News query: {news_query}")
        logger.debug(f"Search query: {search_query}")
        
        # Create tasks for parallel execution
        news_task = asyncio.create_task(
            self._fetch_news_with_timeout(news_query, result)
        )
        search_task = asyncio.create_task(
            self._fetch_search_with_timeout(search_query, result)
        )
        
        # Wait for both tasks to complete
        news_items, search_results = await asyncio.gather(
            news_task,
            search_task,
            return_exceptions=False  # Exceptions are handled within tasks
        )
        
        return news_items, search_results
    
    async def _fetch_news_with_timeout(
        self,
        query: str,
        result: EnhancementResult
    ) -> List[Dict[str, Any]]:
        """
        Fetch news from You.com with timeout handling.
        
        Args:
            query: Search query for news
            result: EnhancementResult to store errors
        
        Returns:
            List of news items (empty list on error)
        """
        try:
            logger.debug(f"Fetching news with {self.news_timeout}s timeout")
            
            # Wrap synchronous call in async executor with timeout
            news_items = await asyncio.wait_for(
                asyncio.to_thread(
                    self.youcom_client.news,
                    query=query,
                    count=5,
                    freshness="year"
                ),
                timeout=self.news_timeout
            )
            
            logger.info(f"Retrieved {len(news_items)} news items")
            return news_items
            
        except asyncio.TimeoutError:
            error_msg = f"You.com News API timeout after {self.news_timeout}s"
            logger.warning(error_msg)
            result.errors.append(error_msg)
            return []
            
        except Exception as e:
            error_msg = f"You.com News API error: {str(e)}"
            logger.warning(error_msg)
            result.errors.append(error_msg)
            return []
    
    async def _fetch_search_with_timeout(
        self,
        query: str,
        result: EnhancementResult
    ) -> List[Dict[str, Any]]:
        """
        Fetch search results from You.com with timeout handling.
        
        Args:
            query: Search query
            result: EnhancementResult to store errors
        
        Returns:
            List of search results (empty list on error)
        """
        try:
            logger.debug(f"Fetching search results with {self.search_timeout}s timeout")
            
            # Wrap synchronous call in async executor with timeout
            search_results = await asyncio.wait_for(
                asyncio.to_thread(
                    self.youcom_client.search,
                    query=query,
                    count=5,
                    freshness="year"
                ),
                timeout=self.search_timeout
            )
            
            logger.info(f"Retrieved {len(search_results)} search results")
            return search_results
            
        except asyncio.TimeoutError:
            error_msg = f"You.com Search API timeout after {self.search_timeout}s"
            logger.warning(error_msg)
            result.errors.append(error_msg)
            return []
            
        except Exception as e:
            error_msg = f"You.com Search API error: {str(e)}"
            logger.warning(error_msg)
            result.errors.append(error_msg)
            return []
    
    async def _analyze_with_glm(
        self,
        project_name: str,
        project_description: str,
        news_items: List[Dict[str, Any]],
        search_results: List[Dict[str, Any]],
        result: EnhancementResult
    ) -> str:
        """
        Analyze news and search results with GLM reasoner.
        
        Args:
            project_name: Name of the project
            project_description: Description of the project
            news_items: List of news items from You.com
            search_results: List of search results from You.com
            result: EnhancementResult to store errors
        
        Returns:
            GLM summary string (empty string on error)
        """
        try:
            logger.debug(f"Analyzing results with GLM (timeout={self.glm_timeout}s)")
            
            # Build prompt for GLM
            prompt = self._build_glm_prompt(
                project_name=project_name,
                project_description=project_description,
                news_items=news_items,
                search_results=search_results
            )
            
            # Call GLM with timeout
            summary = await asyncio.wait_for(
                self.glm_reasoner.reason(
                    prompt=prompt,
                    system_prompt=(
                        "You are an expert in R&D tax credit qualification. "
                        "Analyze recent IRS guidance and news to provide insights "
                        "on how they affect R&D qualification decisions. "
                        "Be concise and focus on actionable insights."
                    ),
                    temperature=0.2,
                    max_tokens=500
                ),
                timeout=self.glm_timeout
            )
            
            logger.info(f"GLM analysis complete (length: {len(summary)})")
            return summary
            
        except asyncio.TimeoutError:
            error_msg = f"GLM reasoner timeout after {self.glm_timeout}s"
            logger.warning(error_msg)
            result.errors.append(error_msg)
            return ""
            
        except Exception as e:
            error_msg = f"GLM reasoner error: {str(e)}"
            logger.warning(error_msg)
            result.errors.append(error_msg)
            return ""
    
    def _build_glm_prompt(
        self,
        project_name: str,
        project_description: str,
        news_items: List[Dict[str, Any]],
        search_results: List[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for GLM reasoner analysis.
        
        Args:
            project_name: Name of the project
            project_description: Description of the project
            news_items: List of news items
            search_results: List of search results
        
        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"Project: {project_name}",
            f"Description: {project_description}",
            "",
            "Recent IRS News:",
        ]
        
        # Add news items
        if news_items:
            for i, item in enumerate(news_items[:3], 1):  # Limit to top 3
                title = item.get('title', 'No title')
                description = item.get('description', 'No description')
                url = item.get('url', '')
                prompt_parts.append(f"{i}. {title}")
                prompt_parts.append(f"   {description}")
                if url:
                    prompt_parts.append(f"   URL: {url}")
        else:
            prompt_parts.append("No recent news found.")
        
        prompt_parts.append("")
        prompt_parts.append("Relevant IRS Guidance:")
        
        # Add search results
        if search_results:
            for i, item in enumerate(search_results[:3], 1):  # Limit to top 3
                title = item.get('title', 'No title')
                description = item.get('description', 'No description')
                url = item.get('url', '')
                prompt_parts.append(f"{i}. {title}")
                prompt_parts.append(f"   {description}")
                if url:
                    prompt_parts.append(f"   URL: {url}")
        else:
            prompt_parts.append("No relevant guidance found.")
        
        prompt_parts.append("")
        prompt_parts.append(
            "Based on the above news and guidance, provide a brief summary (2-3 sentences) "
            "of how recent IRS updates may affect R&D tax credit qualification for this project. "
            "Focus on actionable insights and any new compliance requirements."
        )
        
        return "\n".join(prompt_parts)
