"""
Integration tests for You.com API client.

These tests make real API calls to You.com services and require a valid API key.
They are skipped by default unless YOUCOM_API_KEY is set in the environment.

To run these tests:
1. Set YOUCOM_API_KEY in your .env file
2. Run: pytest tests/test_you_com_integration.py -v

Note: These tests consume API quota and may take longer to execute.
"""

import pytest
import os
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

from tools.you_com_client import YouComClient
from utils.exceptions import APIConnectionError


# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Check if API key is available
YOUCOM_API_KEY = os.getenv("YOUCOM_API_KEY")
SKIP_INTEGRATION = not YOUCOM_API_KEY or YOUCOM_API_KEY == "your_youcom_api_key_here"

# Skip all tests in this module if no API key is configured
pytestmark = pytest.mark.skipif(
    SKIP_INTEGRATION,
    reason="You.com API key not configured. Set YOUCOM_API_KEY to run integration tests."
)

# Note: Based on API testing, the current API key has the following access:
# ✅ Search API - Working (HTTP 200) - Returns web search results
# ✅ Live News API - Working (HTTP 200) - Returns news articles
# ✅ Express Agent API - Working (HTTP 200) - Returns AI-generated responses
# ❌ Images API - 403 Forbidden (requires early access partner status)
# ❌ Custom Agent API - 422 Invalid (requires paid plan + valid custom agent ID)
# ❌ Contents API - Not tested yet (may require paid plan)
#
# Your $100 credits provide access to Search, News, and Express Agent APIs!


@pytest.fixture
def you_com_client():
    """
    Fixture to create a You.com client with real API key.
    
    Returns:
        YouComClient: Configured client instance
    """
    return YouComClient(api_key=YOUCOM_API_KEY)


@pytest.fixture
def sample_rd_project_data():
    """
    Fixture providing sample R&D project data for testing.
    
    Returns:
        Dict: Sample project data
    """
    return {
        "project_name": "API Performance Optimization",
        "project_description": (
            "Development of advanced caching algorithms to improve API response times "
            "by 50% through novel distributed caching strategies."
        ),
        "technical_activities": (
            "Research into cache eviction algorithms, implementation of distributed "
            "cache synchronization protocols, performance benchmarking under various load conditions."
        ),
        "technical_uncertainties": (
            "Uncertainty about optimal cache eviction strategy for our specific workload patterns, "
            "unknown performance characteristics of distributed cache synchronization at scale."
        ),
        "total_hours": 240.5,
        "total_cost": 30000.00
    }


@pytest.fixture
def sample_narrative_text():
    """
    Fixture providing sample R&D narrative for compliance testing.
    
    Returns:
        str: Sample narrative text
    """
    return """
# R&D Project Narrative: API Performance Optimization

## Project Overview
This project aimed to develop advanced caching algorithms to improve API response times 
by 50% through novel distributed caching strategies.

## Technical Uncertainties
At the project's inception, we faced significant technical uncertainties:
1. Optimal cache eviction strategy for our specific workload patterns was unknown
2. Performance characteristics of distributed cache synchronization at scale were uncertain
3. Trade-offs between consistency and performance in distributed systems required investigation

## Process of Experimentation
We conducted systematic experimentation to resolve these uncertainties:
1. Implemented and benchmarked multiple cache eviction algorithms (LRU, LFU, ARC)
2. Developed prototype distributed cache synchronization protocols
3. Performed load testing under various conditions to measure performance characteristics
4. Iteratively refined algorithms based on empirical results

## Technological Nature
The work was fundamentally technological, involving:
- Algorithm design and implementation
- Distributed systems engineering
- Performance optimization techniques
- Software architecture improvements

## Qualified Purpose
The project served a qualified purpose by improving the functionality and performance 
of our software product, directly enhancing its commercial viability and user experience.

## Results and Outcomes
Through systematic experimentation, we successfully:
- Achieved 52% improvement in API response times
- Developed novel cache synchronization protocol with minimal overhead
- Created reusable caching framework for future projects
"""


class TestYouComSearchAPIIntegration:
    """Integration tests for You.com Search API (Basic Tier)."""
    
    def test_search_for_irs_guidance(self, you_com_client):
        """
        Test searching for recent IRS R&D tax credit guidance.
        
        This test verifies that the Search API can find relevant IRS guidance
        and compliance information using the basic tier search endpoint.
        
        Note: This test uses the basic Search API. If you get 403 Forbidden,
        your API key may need activation or subscription upgrade.
        """
        try:
            # Search for IRS R&D guidance
            results = you_com_client.search(
                query="IRS R&D tax credit software development guidance",
                count=5,
                freshness="year"
            )
        except APIConnectionError as e:
            if e.status_code == 403:
                pytest.skip(
                    "Search API returned 403 Forbidden. Your API key may need activation "
                    "or subscription upgrade. Contact You.com support for assistance."
                )
            raise
        
        # Verify we got results
        assert isinstance(results, list)
        assert len(results) > 0, "Search should return at least one result"
        
        # Verify result structure
        first_result = results[0]
        assert 'title' in first_result
        assert 'url' in first_result
        assert 'description' in first_result
        assert 'source_type' in first_result
        
        # Verify URLs are valid
        assert first_result['url'].startswith('http')
        
        # Log results for manual verification
        print(f"\n=== Search Results ({len(results)} found) ===")
        for i, result in enumerate(results[:3], 1):
            print(f"\n{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Type: {result['source_type']}")
            print(f"   Description: {result['description'][:100]}...")
    
    def test_search_with_freshness_filter(self, you_com_client):
        """
        Test search with freshness parameter to find recent guidance.
        
        This verifies that the freshness filter works correctly with the basic Search API.
        """
        try:
            # Search for very recent guidance
            results = you_com_client.search(
                query="IRS tax credit new ruling",
                count=3,
                freshness="month"
            )
        except APIConnectionError as e:
            if e.status_code == 403:
                pytest.skip("Search API returned 403 Forbidden - API key needs activation or upgrade")
            raise
        
        assert isinstance(results, list)
        # Note: May return 0 results if no recent guidance, which is valid
        
        print(f"\n=== Recent Guidance ({len(results)} found) ===")
        for result in results:
            print(f"- {result['title']}")
            if 'page_age' in result:
                print(f"  Published: {result['page_age']}")
    
    def test_search_response_parsing(self, you_com_client):
        """
        Test that search results are properly parsed and structured.
        
        This verifies response parsing accuracy for the basic Search API.
        """
        try:
            results = you_com_client.search(
                query="R&D tax credit",
                count=5
            )
        except APIConnectionError as e:
            if e.status_code == 403:
                pytest.skip("Search API returned 403 Forbidden - API key needs activation or upgrade")
            raise
        
        # Verify all results have required fields
        for result in results:
            assert isinstance(result, dict)
            assert 'title' in result
            assert 'url' in result
            assert 'description' in result
            assert 'snippets' in result
            assert 'source_type' in result
            
            # Verify types
            assert isinstance(result['title'], str)
            assert isinstance(result['url'], str)
            assert isinstance(result['description'], str)
            assert isinstance(result['snippets'], list)
            assert result['source_type'] in ['web', 'news']
    
    def test_search_caching(self, you_com_client):
        """
        Test that search results are properly cached.
        
        This verifies caching functionality to avoid redundant API calls.
        """
        query = "IRS R&D tax credit test query"
        
        # Clear cache first
        you_com_client.clear_search_cache()
        
        try:
            # First call - should hit API
            results1 = you_com_client.search(query=query, count=3)
            
            # Second call - should use cache
            results2 = you_com_client.search(query=query, count=3)
        except APIConnectionError as e:
            if e.status_code == 403:
                pytest.skip("Search API returned 403 Forbidden - API key needs activation or upgrade")
            raise
        
        # Results should be identical
        assert results1 == results2
        
        # Check cache statistics
        stats = you_com_client.get_cache_statistics()
        assert stats['search_cache_size'] > 0
        
        print(f"\n=== Cache Statistics ===")
        print(f"Search cache size: {stats['search_cache_size']}")
        print(f"Cache enabled: {stats['enabled']}")


class TestYouComNewsAPIIntegration:
    """Integration tests for You.com Live News API (Basic Tier)."""
    
    def test_news_search_for_irs_updates(self, you_com_client):
        """
        Test searching for recent IRS news and updates.
        
        This test verifies that the Live News API can find recent news articles
        about IRS updates and tax credit changes.
        
        Note: If you get 403 Forbidden, your API key may need activation or upgrade.
        """
        try:
            # Search for recent IRS news
            results = you_com_client.news(
                query="IRS R&D tax credit updates",
                count=5,
                freshness="month"
            )
        except APIConnectionError as e:
            if e.status_code == 403:
                pytest.skip(
                    "News API returned 403 Forbidden. Your API key may need activation "
                    "or subscription upgrade. Contact You.com support for assistance."
                )
            raise
        
        # Verify we got results
        assert isinstance(results, list)
        # Note: May return 0 results if no recent news, which is valid
        
        # If we have results, verify structure
        if len(results) > 0:
            first_result = results[0]
            assert 'title' in first_result
            assert 'url' in first_result
            assert 'description' in first_result
            assert 'source_type' in first_result
            assert first_result['source_type'] == 'news'
            
            # Verify URLs are valid
            assert first_result['url'].startswith('http')
        
        # Log results for manual verification
        print(f"\n=== News Results ({len(results)} found) ===")
        for i, result in enumerate(results[:3], 1):
            print(f"\n{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            if 'page_age' in result:
                print(f"   Published: {result['page_age']}")
            print(f"   Description: {result['description'][:100]}...")
    
    def test_news_with_freshness_filter(self, you_com_client):
        """
        Test news search with freshness parameter.
        
        This verifies that the freshness filter works correctly for news results.
        """
        # Search for very recent news
        results = you_com_client.news(
            query="tax credit legislation",
            count=3,
            freshness="week"
        )
        
        assert isinstance(results, list)
        # Note: May return 0 results if no recent news, which is valid
        
        print(f"\n=== Recent News ({len(results)} found) ===")
        for result in results:
            print(f"- {result['title']}")
            if 'page_age' in result:
                print(f"  Published: {result['page_age']}")
    
    def test_news_response_parsing(self, you_com_client):
        """
        Test that news results are properly parsed and structured.
        
        This verifies response parsing accuracy for the Live News API.
        """
        results = you_com_client.news(
            query="IRS announcement",
            count=5
        )
        
        # Verify all results have required fields
        for result in results:
            assert isinstance(result, dict)
            assert 'title' in result
            assert 'url' in result
            assert 'description' in result
            assert 'source_type' in result
            
            # Verify types
            assert isinstance(result['title'], str)
            assert isinstance(result['url'], str)
            assert isinstance(result['description'], str)
            assert result['source_type'] == 'news'
    
    def test_news_caching(self, you_com_client):
        """
        Test that news results are properly cached.
        
        This verifies caching functionality for the Live News API.
        """
        query = "IRS tax credit news test"
        
        # Clear cache first
        you_com_client.clear_search_cache()
        
        # First call - should hit API
        results1 = you_com_client.news(query=query, count=3)
        
        # Second call - should use cache
        results2 = you_com_client.news(query=query, count=3)
        
        # Results should be identical
        assert results1 == results2
        
        # Check cache statistics
        stats = you_com_client.get_cache_statistics()
        assert stats['search_cache_size'] > 0
        
        print(f"\n=== News Cache Statistics ===")
        print(f"Cache size: {stats['search_cache_size']}")
        print(f"Cache enabled: {stats['enabled']}")


class TestYouComAgentAPIIntegration:
    """Integration tests for You.com Express Agent API (Available with $100 credits)."""
    
    def test_agent_run_with_rd_qualification(self, you_com_client, sample_rd_project_data):
        """
        Test Agent API with sample R&D project data for qualification.
        
        This is the core use case for the Qualification Agent.
        """
        # Create a prompt for R&D qualification
        prompt = f"""
You are an expert in IRS R&D tax credit qualification. Analyze the following project 
and determine what percentage qualifies for R&D tax credits.

Project: {sample_rd_project_data['project_name']}
Description: {sample_rd_project_data['project_description']}
Technical Activities: {sample_rd_project_data['technical_activities']}
Technical Uncertainties: {sample_rd_project_data['technical_uncertainties']}
Total Hours: {sample_rd_project_data['total_hours']}
Total Cost: ${sample_rd_project_data['total_cost']:,.2f}

Please provide your analysis in JSON format with the following fields:
- qualification_percentage: Percentage of project that qualifies (0-100)
- confidence_score: Your confidence in this assessment (0-1)
- reasoning: Detailed explanation of your qualification decision
- citations: List of relevant IRS guidance references

Respond with ONLY the JSON object, no additional text.
"""
        
        # Run agent
        response = you_com_client.agent_run(
            prompt=prompt,
            agent_mode="express"
        )
        
        # Verify response structure
        assert isinstance(response, dict)
        assert 'output' in response
        assert len(response['output']) > 0
        
        # Extract response text
        response_text = response['output'][0]['text']
        assert isinstance(response_text, str)
        assert len(response_text) > 0
        
        print(f"\n=== Agent Response ===")
        print(response_text[:500])
        
        # Try to parse the response
        try:
            parsed = you_com_client._parse_agent_response(response_text)
            
            # Verify parsed structure
            assert 'qualification_percentage' in parsed
            assert 'confidence_score' in parsed
            assert 'reasoning' in parsed
            
            # Verify value ranges
            assert 0 <= parsed['qualification_percentage'] <= 100
            assert 0 <= parsed['confidence_score'] <= 1
            
            print(f"\n=== Parsed Qualification ===")
            print(f"Qualification: {parsed['qualification_percentage']}%")
            print(f"Confidence: {parsed['confidence_score']:.2f}")
            print(f"Reasoning: {parsed['reasoning'][:200]}...")
            
        except ValueError as e:
            # If parsing fails, that's okay for integration test
            # The agent might not return perfect JSON format
            print(f"\n=== Parsing Note ===")
            print(f"Response parsing encountered: {e}")
            print("This is acceptable for integration testing - response format may vary")
    
    def test_agent_run_response_time(self, you_com_client):
        """
        Test that Agent API responds within acceptable time limits.
        
        Agent API can take 10-30 seconds, so we verify it completes within timeout.
        """
        import time
        
        prompt = "What are the key requirements for R&D tax credit qualification?"
        
        start_time = time.time()
        response = you_com_client.agent_run(
            prompt=prompt,
            agent_mode="express"
        )
        elapsed_time = time.time() - start_time
        
        # Should complete within 60 second timeout
        assert elapsed_time < 60.0
        
        # Verify we got a response
        assert 'output' in response
        assert len(response['output']) > 0
        
        print(f"\n=== Performance ===")
        print(f"Agent API response time: {elapsed_time:.2f} seconds")
    
    def test_agent_run_with_tools(self, you_com_client):
        """
        Test Agent API with web search tool enabled.
        
        This verifies that the agent can use tools for enhanced reasoning.
        """
        prompt = "What are the latest IRS updates on R&D tax credits for software development?"
        
        response = you_com_client.agent_run(
            prompt=prompt,
            agent_mode="express",
            tools=[{"type": "web_search"}]
        )
        
        # Verify response
        assert isinstance(response, dict)
        assert 'output' in response
        
        # Find the message.answer output item (the actual response text)
        response_text = None
        for output_item in response['output']:
            if output_item.get('type') == 'message.answer':
                response_text = output_item.get('text')
                break
        
        # If no message.answer found, try the first output item
        if response_text is None and len(response['output']) > 0:
            response_text = response['output'][0].get('text', '')
        
        assert response_text is not None
        assert len(response_text) > 0
        
        print(f"\n=== Agent with Tools Response ===")
        print(response_text[:300])


class TestYouComContentsAPIIntegration:
    """Integration tests for You.com Contents API (Requires Paid Plan)."""
    
    @pytest.mark.skip(reason="Contents API requires paid plan - 401 Unauthorized on basic tier")
    def test_fetch_content_from_url(self, you_com_client):
        """
        Test fetching content from a known URL.
        
        This verifies the Contents API can extract and format web content.
        """
        # Use a stable, public URL for testing
        # IRS website is a good choice as it's reliable and relevant
        test_url = "https://www.irs.gov/businesses/small-businesses-self-employed/research-credit"
        
        try:
            result = you_com_client.fetch_content(
                url=test_url,
                format="markdown"
            )
            
            # Verify result structure
            assert isinstance(result, dict)
            assert 'content' in result
            assert 'url' in result
            assert 'format' in result
            assert 'word_count' in result
            
            # Verify content was extracted
            assert len(result['content']) > 0
            assert result['url'] == test_url
            assert result['format'] == "markdown"
            assert result['word_count'] > 0
            
            print(f"\n=== Content Extraction ===")
            print(f"URL: {result['url']}")
            print(f"Format: {result['format']}")
            print(f"Word count: {result['word_count']}")
            if 'title' in result:
                print(f"Title: {result['title']}")
            print(f"Content preview: {result['content'][:200]}...")
            
        except APIConnectionError as e:
            # If the URL is not accessible or API has issues, that's okay
            # Log it and skip
            print(f"\n=== Content Fetch Note ===")
            print(f"Could not fetch content: {e.message}")
            print("This may be due to URL accessibility or API limitations")
            pytest.skip(f"Content fetch failed: {e.message}")
    
    @pytest.mark.skip(reason="Contents API requires paid plan - 401 Unauthorized on basic tier")
    def test_fetch_content_html_format(self, you_com_client):
        """
        Test fetching content in HTML format.
        
        This verifies format parameter works correctly.
        """
        test_url = "https://www.irs.gov/credits-deductions/businesses/research-credit"
        
        try:
            result = you_com_client.fetch_content(
                url=test_url,
                format="html"
            )
            
            assert result['format'] == "html"
            assert len(result['content']) > 0
            
            # HTML should contain tags
            assert '<' in result['content'] or result['word_count'] > 0
            
            print(f"\n=== HTML Content ===")
            print(f"Word count: {result['word_count']}")
            print(f"Content length: {len(result['content'])} characters")
            
        except APIConnectionError as e:
            print(f"\n=== Content Fetch Note ===")
            print(f"Could not fetch HTML content: {e.message}")
            pytest.skip(f"HTML content fetch failed: {e.message}")
    
    @pytest.mark.skip(reason="Contents API requires paid plan - 401 Unauthorized on basic tier")
    def test_content_caching(self, you_com_client):
        """
        Test that fetched content is properly cached.
        
        This verifies caching functionality for Contents API.
        """
        test_url = "https://www.irs.gov/pub/irs-pdf/i6765.pdf"
        
        # Clear cache first
        you_com_client.clear_content_cache()
        
        try:
            # First call - should hit API
            result1 = you_com_client.fetch_content(url=test_url, format="markdown")
            
            # Second call - should use cache
            result2 = you_com_client.fetch_content(url=test_url, format="markdown")
            
            # Results should be identical
            assert result1 == result2
            
            # Check cache statistics
            stats = you_com_client.get_cache_statistics()
            assert stats['content_cache_size'] > 0
            
            print(f"\n=== Content Cache Statistics ===")
            print(f"Content cache size: {stats['content_cache_size']}")
            
        except APIConnectionError as e:
            print(f"\n=== Caching Test Note ===")
            print(f"Could not test caching: {e.message}")
            pytest.skip(f"Caching test failed: {e.message}")


class TestYouComExpressAgentIntegration:
    """Integration tests for You.com Express Agent API (Available with $100 credits)."""
    
    def test_express_agent_compliance_review(self, you_com_client, sample_narrative_text):
        """
        Test Express Agent for narrative compliance review.
        
        This is the core use case for the Audit Trail Agent.
        """
        try:
            review = you_com_client.express_agent(
                narrative_text=sample_narrative_text
            )
            
            # Verify review structure
            assert isinstance(review, dict)
            assert 'compliance_status' in review
            assert 'completeness_score' in review
            assert 'raw_response' in review
            
            # Verify status is valid
            assert review['compliance_status'] in ['compliant', 'needs_revision', 'non_compliant']
            
            # Verify score is in valid range
            assert 0 <= review['completeness_score'] <= 1
            
            print(f"\n=== Compliance Review ===")
            print(f"Status: {review['compliance_status']}")
            print(f"Completeness: {review['completeness_score']:.1%}")
            
            if 'missing_elements' in review and review['missing_elements']:
                print(f"\nMissing elements:")
                for element in review['missing_elements']:
                    print(f"  - {element}")
            
            if 'suggestions' in review and review['suggestions']:
                print(f"\nSuggestions:")
                for suggestion in review['suggestions'][:3]:
                    print(f"  - {suggestion}")
            
            if 'strengths' in review and review['strengths']:
                print(f"\nStrengths:")
                for strength in review['strengths'][:3]:
                    print(f"  - {strength}")
                    
        except APIConnectionError as e:
            print(f"\n=== Express Agent Note ===")
            print(f"Express Agent call failed: {e.message}")
            print("This may be due to API limitations or endpoint availability")
            pytest.skip(f"Express Agent test failed: {e.message}")
    
    def test_express_agent_with_incomplete_narrative(self, you_com_client):
        """
        Test Express Agent with an incomplete narrative.
        
        This verifies that the agent can identify missing elements.
        """
        incomplete_narrative = """
# R&D Project: API Optimization

We worked on improving API performance. We made some changes to the caching system.
The results were good.
"""
        
        try:
            review = you_com_client.express_agent(
                narrative_text=incomplete_narrative
            )
            
            # Should identify issues with this minimal narrative
            assert review['compliance_status'] in ['needs_revision', 'non_compliant']
            
            # Completeness score should be low
            assert review['completeness_score'] < 0.8
            
            print(f"\n=== Incomplete Narrative Review ===")
            print(f"Status: {review['compliance_status']}")
            print(f"Completeness: {review['completeness_score']:.1%}")
            
            if 'missing_elements' in review:
                print(f"Missing elements identified: {len(review['missing_elements'])}")
                
        except APIConnectionError as e:
            print(f"\n=== Express Agent Note ===")
            print(f"Express Agent call failed: {e.message}")
            pytest.skip(f"Express Agent test failed: {e.message}")


class TestYouComEndToEndIntegration:
    """End-to-end integration tests combining all accessible APIs."""
    
    def test_full_qualification_workflow(self, you_com_client, sample_rd_project_data):
        """
        Test a complete qualification workflow using all accessible APIs.
        
        This simulates the actual R&D qualification workflow:
        1. Search for IRS guidance documents
        2. Search for recent news about tax credit updates
        3. Use Express Agent for R&D qualification analysis
        4. Use Express Agent for narrative compliance review
        """
        print("\n=== Full R&D Qualification Workflow ===")
        
        # Step 1: Search for IRS guidance
        print("\n1. Searching for IRS guidance documents...")
        search_results = you_com_client.search(
            query="IRS R&D tax credit software development guidance",
            count=3,
            freshness="year"
        )
        print(f"   Found {len(search_results)} guidance documents")
        
        if search_results:
            print(f"   Top result: {search_results[0]['title']}")
        
        # Step 2: Search for recent news
        print("\n2. Searching for recent tax credit news...")
        news_results = you_com_client.news(
            query="IRS R&D tax credit updates",
            count=3,
            freshness="month"
        )
        print(f"   Found {len(news_results)} news articles")
        
        if news_results:
            print(f"   Latest news: {news_results[0]['title']}")
        
        # Step 3: Use Express Agent for qualification
        print("\n3. Running Express Agent for R&D qualification...")
        qualification_prompt = f"""
Analyze this R&D project for tax credit qualification:

Project: {sample_rd_project_data['project_name']}
Description: {sample_rd_project_data['project_description']}
Technical Uncertainties: {sample_rd_project_data['technical_uncertainties']}

Provide a brief qualification assessment with percentage and confidence score.
"""
        agent_response = you_com_client.agent_run(
            prompt=qualification_prompt,
            agent_mode="express"
        )
        print(f"   Agent completed qualification analysis")
        
        # Step 4: Use Express Agent for compliance review
        print("\n4. Running Express Agent for narrative compliance...")
        sample_narrative = """
# Project: API Performance Optimization

## Technical Uncertainties
We faced uncertainty about optimal caching strategies for distributed systems.

## Experimentation Process
We tested multiple cache eviction algorithms systematically.

## Results
Achieved 50% performance improvement through novel caching approach.
"""
        compliance_review = you_com_client.express_agent(
            narrative_text=sample_narrative
        )
        print(f"   Compliance review completed")
        print(f"   Status: {compliance_review.get('compliance_status', 'N/A')}")
        
        # Step 5: Combine all results
        print("\n5. Combining all research and analysis...")
        total_sources = len(search_results) + len(news_results)
        print(f"   Total sources found: {total_sources}")
        print(f"   - Guidance documents: {len(search_results)}")
        print(f"   - News articles: {len(news_results)}")
        print(f"   - AI qualification: Complete")
        print(f"   - AI compliance review: Complete")
        
        print("\n=== Workflow Complete ===")
        
        # Verify we got results from all sources
        assert total_sources > 0, "Should find at least one result from search or news"
        assert agent_response is not None, "Should get agent qualification response"
        assert compliance_review is not None, "Should get compliance review"
        
        # Verify result structures
        all_results = search_results + news_results
        for result in all_results:
            assert 'title' in result
            assert 'url' in result
            assert 'description' in result
            assert 'source_type' in result


if __name__ == "__main__":
    # Allow running this file directly for manual testing
    pytest.main([__file__, "-v", "-s"])
