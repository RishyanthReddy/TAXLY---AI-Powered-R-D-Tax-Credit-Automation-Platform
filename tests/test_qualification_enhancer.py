"""
Unit tests for QualificationEnhancer.

Tests the QualificationEnhancer class including:
- Successful enhancement flow with all APIs working
- Individual API failures (News, Search, GLM)
- Timeout scenarios
- Empty result handling
- Parallel execution

These tests use REAL APIs with API keys from .env file.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from tools.qualification_enhancer import QualificationEnhancer, EnhancementResult
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.config import get_config
from utils.exceptions import APIConnectionError


class TestEnhancementResult:
    """Test EnhancementResult dataclass"""
    
    def test_result_initialization(self):
        """Test result initializes with correct defaults"""
        result = EnhancementResult()
        
        assert result.news_items == []
        assert result.search_results == []
        assert result.glm_summary == ""
        assert result.execution_time_ms == 0.0
        assert result.errors == []
    
    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = EnhancementResult(
            news_items=[{"title": "IRS Update"}],
            search_results=[{"title": "Guidance"}],
            glm_summary="Test summary",
            execution_time_ms=1234.5,
            errors=["Error 1"]
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["news_items"] == [{"title": "IRS Update"}]
        assert result_dict["search_results"] == [{"title": "Guidance"}]
        assert result_dict["glm_summary"] == "Test summary"
        assert result_dict["execution_time_ms"] == 1234.5
        assert result_dict["errors"] == ["Error 1"]


class TestQualificationEnhancerInitialization:
    """Test QualificationEnhancer initialization"""
    
    def test_initialization_with_defaults(self):
        """Test initialization with default timeout values"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        assert enhancer.youcom_client == youcom_client
        assert enhancer.glm_reasoner == glm_reasoner
        assert enhancer.news_timeout == 5.0
        assert enhancer.search_timeout == 5.0
        assert enhancer.glm_timeout == 30.0
    
    def test_initialization_with_custom_timeouts(self):
        """Test initialization with custom timeout values"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            news_timeout=10.0,
            search_timeout=15.0,
            glm_timeout=60.0
        )
        
        assert enhancer.news_timeout == 10.0
        assert enhancer.search_timeout == 15.0
        assert enhancer.glm_timeout == 60.0


class TestQualificationEnhancerRealAPIs:
    """Test QualificationEnhancer with real APIs"""
    
    @pytest.mark.asyncio
    async def test_successful_enhancement_flow(self):
        """Test successful enhancement with all APIs working (REAL APIs)"""
        # Get real API keys from config
        config = get_config()
        
        # Initialize real clients
        youcom_client = YouComClient(api_key=config.youcom_api_key)
        glm_reasoner = GLMReasoner(api_key=config.openrouter_api_key)
        
        # Create enhancer with shorter timeouts for testing
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            news_timeout=10.0,
            search_timeout=10.0,
            glm_timeout=30.0
        )
        
        # Run enhancement
        result = await enhancer.enhance_qualification(
            project_name="API Performance Optimization",
            project_description="Developed new caching algorithms to reduce API response times",
            tax_year=2025
        )
        
        # Verify result structure
        assert isinstance(result, EnhancementResult)
        assert isinstance(result.news_items, list)
        assert isinstance(result.search_results, list)
        assert isinstance(result.glm_summary, str)
        assert result.execution_time_ms > 0
        assert isinstance(result.errors, list)
        
        # Verify we got some data (at least one API should return results)
        assert len(result.news_items) > 0 or len(result.search_results) > 0
        
        # If we got data, GLM should have generated a summary
        if result.news_items or result.search_results:
            assert len(result.glm_summary) > 0
        
        print(f"\n✓ Enhancement successful!")
        print(f"  - News items: {len(result.news_items)}")
        print(f"  - Search results: {len(result.search_results)}")
        print(f"  - GLM summary length: {len(result.glm_summary)}")
        print(f"  - Execution time: {result.execution_time_ms:.2f}ms")
        print(f"  - Errors: {len(result.errors)}")


class TestQualificationEnhancerAPIFailures:
    """Test QualificationEnhancer with individual API failures"""
    
    @pytest.mark.asyncio
    async def test_news_api_failure(self):
        """Test enhancement continues when News API fails"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock News API to fail
        youcom_client.news.side_effect = Exception("News API error")
        
        # Mock Search API to succeed
        youcom_client.search.return_value = [
            {
                "title": "IRS R&D Guidance",
                "url": "https://irs.gov/guidance",
                "description": "Official IRS guidance on R&D credits"
            }
        ]
        
        # Mock GLM to succeed
        async def mock_reason(*args, **kwargs):
            return "Based on the search results, this project may qualify for R&D credits."
        
        glm_reasoner.reason = AsyncMock(side_effect=mock_reason)
        
        # Create enhancer
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Run enhancement
        result = await enhancer.enhance_qualification(
            project_name="Test Project",
            project_description="Test description",
            tax_year=2025
        )
        
        # Verify News API failed but enhancement continued
        assert len(result.news_items) == 0
        assert len(result.search_results) > 0
        assert len(result.glm_summary) > 0
        assert len(result.errors) == 1
        assert "News API error" in result.errors[0]
        
        print(f"\n✓ News API failure handled correctly")
        print(f"  - News items: {len(result.news_items)} (expected 0)")
        print(f"  - Search results: {len(result.search_results)} (expected > 0)")
        print(f"  - Errors: {result.errors}")
    
    @pytest.mark.asyncio
    async def test_search_api_failure(self):
        """Test enhancement continues when Search API fails"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock News API to succeed
        youcom_client.news.return_value = [
            {
                "title": "IRS Announces R&D Updates",
                "url": "https://irs.gov/news",
                "description": "Recent updates to R&D tax credit rules"
            }
        ]
        
        # Mock Search API to fail
        youcom_client.search.side_effect = Exception("Search API error")
        
        # Mock GLM to succeed
        async def mock_reason(*args, **kwargs):
            return "Based on the news, this project may qualify for R&D credits."
        
        glm_reasoner.reason = AsyncMock(side_effect=mock_reason)
        
        # Create enhancer
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Run enhancement
        result = await enhancer.enhance_qualification(
            project_name="Test Project",
            project_description="Test description",
            tax_year=2025
        )
        
        # Verify Search API failed but enhancement continued
        assert len(result.news_items) > 0
        assert len(result.search_results) == 0
        assert len(result.glm_summary) > 0
        assert len(result.errors) == 1
        assert "Search API error" in result.errors[0]
        
        print(f"\n✓ Search API failure handled correctly")
        print(f"  - News items: {len(result.news_items)} (expected > 0)")
        print(f"  - Search results: {len(result.search_results)} (expected 0)")
        print(f"  - Errors: {result.errors}")
    
    @pytest.mark.asyncio
    async def test_glm_api_failure(self):
        """Test enhancement continues when GLM API fails"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock News API to succeed
        youcom_client.news.return_value = [
            {
                "title": "IRS News",
                "url": "https://irs.gov/news",
                "description": "News description"
            }
        ]
        
        # Mock Search API to succeed
        youcom_client.search.return_value = [
            {
                "title": "IRS Guidance",
                "url": "https://irs.gov/guidance",
                "description": "Guidance description"
            }
        ]
        
        # Mock GLM to fail
        async def mock_reason(*args, **kwargs):
            raise Exception("GLM API error")
        
        glm_reasoner.reason = AsyncMock(side_effect=mock_reason)
        
        # Create enhancer
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Run enhancement
        result = await enhancer.enhance_qualification(
            project_name="Test Project",
            project_description="Test description",
            tax_year=2025
        )
        
        # Verify GLM failed but enhancement continued
        assert len(result.news_items) > 0
        assert len(result.search_results) > 0
        assert result.glm_summary == ""
        assert len(result.errors) == 1
        assert "GLM reasoner error" in result.errors[0]
        
        print(f"\n✓ GLM API failure handled correctly")
        print(f"  - News items: {len(result.news_items)} (expected > 0)")
        print(f"  - Search results: {len(result.search_results)} (expected > 0)")
        print(f"  - GLM summary: '{result.glm_summary}' (expected empty)")
        print(f"  - Errors: {result.errors}")


class TestQualificationEnhancerTimeouts:
    """Test QualificationEnhancer timeout handling"""
    
    @pytest.mark.asyncio
    async def test_news_api_timeout(self):
        """Test News API timeout handling"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock News API to timeout (simulate slow response)
        def slow_news(*args, **kwargs):
            import time
            time.sleep(10)  # Sleep longer than timeout
            return []
        
        youcom_client.news = Mock(side_effect=slow_news)
        
        # Mock Search API to succeed quickly
        youcom_client.search.return_value = [{"title": "Result"}]
        
        # Mock GLM to succeed
        async def mock_reason(*args, **kwargs):
            return "Summary"
        
        glm_reasoner.reason = AsyncMock(side_effect=mock_reason)
        
        # Create enhancer with short timeout
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            news_timeout=0.5  # Very short timeout
        )
        
        # Run enhancement
        result = await enhancer.enhance_qualification(
            project_name="Test Project",
            project_description="Test description",
            tax_year=2025
        )
        
        # Verify timeout was handled
        assert len(result.news_items) == 0
        assert len(result.errors) == 1
        assert "timeout" in result.errors[0].lower()
        
        print(f"\n✓ News API timeout handled correctly")
        print(f"  - Errors: {result.errors}")
    
    @pytest.mark.asyncio
    async def test_search_api_timeout(self):
        """Test Search API timeout handling"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock News API to succeed quickly
        youcom_client.news.return_value = [{"title": "News"}]
        
        # Mock Search API to timeout
        def slow_search(*args, **kwargs):
            import time
            time.sleep(10)
            return []
        
        youcom_client.search = Mock(side_effect=slow_search)
        
        # Mock GLM to succeed
        async def mock_reason(*args, **kwargs):
            return "Summary"
        
        glm_reasoner.reason = AsyncMock(side_effect=mock_reason)
        
        # Create enhancer with short timeout
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            search_timeout=0.5
        )
        
        # Run enhancement
        result = await enhancer.enhance_qualification(
            project_name="Test Project",
            project_description="Test description",
            tax_year=2025
        )
        
        # Verify timeout was handled
        assert len(result.search_results) == 0
        assert len(result.errors) == 1
        assert "timeout" in result.errors[0].lower()
        
        print(f"\n✓ Search API timeout handled correctly")
        print(f"  - Errors: {result.errors}")
    
    @pytest.mark.asyncio
    async def test_glm_timeout(self):
        """Test GLM reasoner timeout handling"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock APIs to succeed
        youcom_client.news.return_value = [{"title": "News"}]
        youcom_client.search.return_value = [{"title": "Search"}]
        
        # Mock GLM to timeout
        async def slow_glm(*args, **kwargs):
            await asyncio.sleep(10)
            return "Summary"
        
        glm_reasoner.reason = AsyncMock(side_effect=slow_glm)
        
        # Create enhancer with short GLM timeout
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            glm_timeout=0.5
        )
        
        # Run enhancement
        result = await enhancer.enhance_qualification(
            project_name="Test Project",
            project_description="Test description",
            tax_year=2025
        )
        
        # Verify timeout was handled
        assert result.glm_summary == ""
        assert len(result.errors) == 1
        assert "timeout" in result.errors[0].lower()
        
        print(f"\n✓ GLM timeout handled correctly")
        print(f"  - Errors: {result.errors}")


class TestQualificationEnhancerEmptyResults:
    """Test QualificationEnhancer with empty results"""
    
    @pytest.mark.asyncio
    async def test_empty_news_and_search_results(self):
        """Test enhancement when both News and Search return empty results"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock APIs to return empty results
        youcom_client.news.return_value = []
        youcom_client.search.return_value = []
        
        # GLM should not be called when there's no data
        glm_reasoner.reason = AsyncMock()
        
        # Create enhancer
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Run enhancement
        result = await enhancer.enhance_qualification(
            project_name="Test Project",
            project_description="Test description",
            tax_year=2025
        )
        
        # Verify empty results handled correctly
        assert len(result.news_items) == 0
        assert len(result.search_results) == 0
        assert result.glm_summary == "No recent guidance or news found for analysis."
        assert len(result.errors) == 0
        
        # Verify GLM was not called
        glm_reasoner.reason.assert_not_called()
        
        print(f"\n✓ Empty results handled correctly")
        print(f"  - GLM summary: '{result.glm_summary}'")
    
    @pytest.mark.asyncio
    async def test_empty_news_with_search_results(self):
        """Test enhancement when News is empty but Search has results"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock News to return empty, Search to return results
        youcom_client.news.return_value = []
        youcom_client.search.return_value = [
            {
                "title": "IRS Guidance",
                "url": "https://irs.gov",
                "description": "Guidance"
            }
        ]
        
        # Mock GLM to succeed
        async def mock_reason(*args, **kwargs):
            return "Analysis based on search results"
        
        glm_reasoner.reason = AsyncMock(side_effect=mock_reason)
        
        # Create enhancer
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Run enhancement
        result = await enhancer.enhance_qualification(
            project_name="Test Project",
            project_description="Test description",
            tax_year=2025
        )
        
        # Verify results
        assert len(result.news_items) == 0
        assert len(result.search_results) > 0
        assert len(result.glm_summary) > 0
        assert len(result.errors) == 0
        
        # Verify GLM was called
        glm_reasoner.reason.assert_called_once()
        
        print(f"\n✓ Empty news with search results handled correctly")


class TestQualificationEnhancerParallelExecution:
    """Test QualificationEnhancer parallel execution"""
    
    @pytest.mark.asyncio
    async def test_parallel_api_calls(self):
        """Test that News and Search APIs are called in parallel"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Track call times
        call_times = []
        
        # Mock News API with delay
        def mock_news(*args, **kwargs):
            import time
            call_times.append(("news_start", time.time()))
            time.sleep(0.2)  # Simulate API delay
            call_times.append(("news_end", time.time()))
            return [{"title": "News"}]
        
        # Mock Search API with delay
        def mock_search(*args, **kwargs):
            import time
            call_times.append(("search_start", time.time()))
            time.sleep(0.2)  # Simulate API delay
            call_times.append(("search_end", time.time()))
            return [{"title": "Search"}]
        
        youcom_client.news = Mock(side_effect=mock_news)
        youcom_client.search = Mock(side_effect=mock_search)
        
        # Mock GLM
        async def mock_reason(*args, **kwargs):
            return "Summary"
        
        glm_reasoner.reason = AsyncMock(side_effect=mock_reason)
        
        # Create enhancer
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Run enhancement
        start_time = datetime.now()
        result = await enhancer.enhance_qualification(
            project_name="Test Project",
            project_description="Test description",
            tax_year=2025
        )
        end_time = datetime.now()
        
        # Calculate total execution time
        total_time = (end_time - start_time).total_seconds()
        
        # If calls were sequential, it would take ~0.4s (0.2 + 0.2)
        # If parallel, it should take ~0.2s (max of the two)
        # Allow some overhead, so check if < 0.35s
        assert total_time < 0.35, f"Execution took {total_time}s, expected < 0.35s for parallel execution"
        
        # Verify both APIs were called
        youcom_client.news.assert_called_once()
        youcom_client.search.assert_called_once()
        
        # Verify calls overlapped (started before the other finished)
        if len(call_times) >= 4:
            news_start = next(t for name, t in call_times if name == "news_start")
            search_start = next(t for name, t in call_times if name == "search_start")
            news_end = next(t for name, t in call_times if name == "news_end")
            search_end = next(t for name, t in call_times if name == "search_end")
            
            # Check that calls overlapped
            assert (search_start < news_end) or (news_start < search_end), "API calls should overlap"
        
        print(f"\n✓ Parallel execution verified")
        print(f"  - Total time: {total_time:.3f}s (expected < 0.35s)")
        print(f"  - Both APIs called: News={youcom_client.news.call_count}, Search={youcom_client.search.call_count}")


class TestQualificationEnhancerPromptBuilding:
    """Test QualificationEnhancer prompt building"""
    
    def test_build_glm_prompt_with_data(self):
        """Test building GLM prompt with news and search results"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        news_items = [
            {
                "title": "IRS Announces R&D Updates",
                "description": "New guidance on software development",
                "url": "https://irs.gov/news1"
            },
            {
                "title": "Tax Credit Changes",
                "description": "Recent changes to R&D credits",
                "url": "https://irs.gov/news2"
            }
        ]
        
        search_results = [
            {
                "title": "IRS Publication 542",
                "description": "Official guidance on R&D credits",
                "url": "https://irs.gov/pub542"
            }
        ]
        
        prompt = enhancer._build_glm_prompt(
            project_name="API Optimization",
            project_description="Improved API performance",
            news_items=news_items,
            search_results=search_results
        )
        
        # Verify prompt contains key elements
        assert "API Optimization" in prompt
        assert "Improved API performance" in prompt
        assert "IRS Announces R&D Updates" in prompt
        assert "IRS Publication 542" in prompt
        assert "Recent IRS News:" in prompt
        assert "Relevant IRS Guidance:" in prompt
        
        print(f"\n✓ GLM prompt built correctly")
        print(f"  - Prompt length: {len(prompt)} characters")
    
    def test_build_glm_prompt_empty_data(self):
        """Test building GLM prompt with no data"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        enhancer = QualificationEnhancer(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        prompt = enhancer._build_glm_prompt(
            project_name="Test Project",
            project_description="Test description",
            news_items=[],
            search_results=[]
        )
        
        # Verify prompt handles empty data
        assert "Test Project" in prompt
        assert "No recent news found" in prompt
        assert "No relevant guidance found" in prompt
        
        print(f"\n✓ GLM prompt with empty data built correctly")
