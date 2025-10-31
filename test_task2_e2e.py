"""
End-to-end test for Task 2: Qualification Enhancement Integration

This test verifies that the enhancement feature works correctly in the
complete qualification workflow, including:
- Enhancement is called during qualification
- Enhancement results are included in the response
- Enhancement failures are non-blocking
- Backward compatibility is maintained
"""

import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from agents.qualification_agent import QualificationAgent, QualificationResult
from tools.qualification_enhancer import QualificationEnhancer, EnhancementResult
from models.financial_models import EmployeeTimeEntry, ProjectCost
from models.tax_models import QualifiedProject


def create_sample_time_entries():
    """Create sample time entries for testing."""
    return [
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="John Doe",
            project_name="API Optimization",
            task_description="Implemented caching layer",
            hours_spent=8.5,
            date=datetime(2024, 1, 15),
            is_rd_classified=True
        ),
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="John Doe",
            project_name="API Optimization",
            task_description="Optimized database queries",
            hours_spent=6.0,
            date=datetime(2024, 1, 16),
            is_rd_classified=True
        )
    ]


def create_sample_costs():
    """Create sample costs for testing."""
    return [
        ProjectCost(
            cost_id="COST001",
            cost_type="Payroll",
            amount=1500.00,
            project_name="API Optimization",
            employee_id="EMP001",
            date=datetime(2024, 1, 15),
            is_rd_classified=True
        )
    ]


def create_mock_qualified_project():
    """Create a mock qualified project."""
    return QualifiedProject(
        project_name="API Optimization",
        qualified_hours=14.5,
        qualified_cost=1500.00,
        confidence_score=0.85,
        qualification_percentage=100.0,
        supporting_citation="IRS guidance supports this qualification",
        reasoning="Project involves systematic experimentation",
        irs_source="CFR Title 26 § 1.41-4",
        flagged_for_review=False
    )


def create_mock_enhancement_result():
    """Create a mock enhancement result."""
    return EnhancementResult(
        news_items=[
            {
                "title": "IRS Updates R&D Tax Credit Guidance",
                "url": "https://irs.gov/news/rd-update",
                "description": "New guidance on software development",
                "published_date": "2024-01-01",
                "source": "IRS"
            }
        ],
        search_results=[
            {
                "title": "R&D Tax Credit for Software",
                "url": "https://irs.gov/guidance/software",
                "description": "Guidance on qualifying software activities",
                "snippets": ["Software development qualifies..."]
            }
        ],
        glm_summary="Recent IRS guidance supports software R&D qualification",
        execution_time_ms=1234.56,
        errors=[]
    )


def test_enhancement_called_during_qualification():
    """Test that enhancement is called during qualification when enabled."""
    print("Testing enhancement is called during qualification...")
    
    # Create mock tools
    mock_rag_tool = Mock()
    mock_youcom_client = Mock()
    mock_glm_reasoner = Mock()
    
    # Mock RAG query response
    mock_rag_context = Mock()
    mock_rag_context.chunk_count = 3
    mock_rag_context.average_relevance = 0.85
    mock_rag_context.format_for_llm_prompt.return_value = "RAG context"
    mock_rag_context.chunks = [
        {'source': 'IRS Doc', 'page': 1, 'text': 'IRS guidance text'}
    ]
    mock_rag_tool.query.return_value = mock_rag_context
    
    # Mock You.com agent response
    mock_youcom_client.agent_run.return_value = {
        'output': [
            {
                'text': '''
                QUALIFICATION_PERCENTAGE: 100
                CONFIDENCE_SCORE: 0.85
                REASONING: Project involves systematic experimentation
                CITATIONS: CFR Title 26 § 1.41-4
                '''
            }
        ]
    }
    
    # Mock response parsing
    mock_youcom_client._parse_agent_response.return_value = {
        'qualification_percentage': 100.0,
        'confidence_score': 0.85,
        'reasoning': 'Project involves systematic experimentation',
        'citations': ['CFR Title 26 § 1.41-4'],
        'technical_details': None
    }
    
    # Mock You.com search and news for enhancement
    mock_youcom_client.search.return_value = [
        {
            "title": "R&D Tax Credit for Software",
            "url": "https://irs.gov/guidance/software",
            "description": "Guidance on qualifying software activities",
            "snippets": ["Software development qualifies..."]
        }
    ]
    
    mock_youcom_client.news.return_value = [
        {
            "title": "IRS Updates R&D Tax Credit Guidance",
            "url": "https://irs.gov/news/rd-update",
            "description": "New guidance on software development",
            "published_date": "2024-01-01",
            "source": "IRS"
        }
    ]
    
    # Mock GLM reasoner for enhancement
    async def mock_reason(*args, **kwargs):
        return "Recent IRS guidance supports software R&D qualification"
    
    mock_glm_reasoner.reason = mock_reason
    
    # Initialize agent with enhancement enabled
    agent = QualificationAgent(
        rag_tool=mock_rag_tool,
        youcom_client=mock_youcom_client,
        glm_reasoner=mock_glm_reasoner,
        enable_enhancement=True
    )
    
    # Run qualification
    time_entries = create_sample_time_entries()
    costs = create_sample_costs()
    
    result = agent.run(
        time_entries=time_entries,
        costs=costs,
        tax_year=2024
    )
    
    # Verify result includes enhancement
    assert result.enhancement is not None, "Result should include enhancement"
    assert 'news_items' in result.enhancement, "Enhancement should have news_items"
    assert 'search_results' in result.enhancement, "Enhancement should have search_results"
    assert 'glm_summary' in result.enhancement, "Enhancement should have glm_summary"
    assert len(result.enhancement['news_items']) > 0, "Should have news items"
    assert len(result.enhancement['search_results']) > 0, "Should have search results"
    
    print("✓ Enhancement called during qualification test passed")


def test_enhancement_not_called_when_disabled():
    """Test that enhancement is not called when disabled."""
    print("Testing enhancement not called when disabled...")
    
    # Create mock tools
    mock_rag_tool = Mock()
    mock_youcom_client = Mock()
    mock_glm_reasoner = Mock()
    
    # Mock RAG query response
    mock_rag_context = Mock()
    mock_rag_context.chunk_count = 3
    mock_rag_context.average_relevance = 0.85
    mock_rag_context.format_for_llm_prompt.return_value = "RAG context"
    mock_rag_context.chunks = [
        {'source': 'IRS Doc', 'page': 1, 'text': 'IRS guidance text'}
    ]
    mock_rag_tool.query.return_value = mock_rag_context
    
    # Mock You.com agent response
    mock_youcom_client.agent_run.return_value = {
        'output': [
            {
                'text': '''
                QUALIFICATION_PERCENTAGE: 100
                CONFIDENCE_SCORE: 0.85
                REASONING: Project involves systematic experimentation
                CITATIONS: CFR Title 26 § 1.41-4
                '''
            }
        ]
    }
    
    # Mock response parsing
    mock_youcom_client._parse_agent_response.return_value = {
        'qualification_percentage': 100.0,
        'confidence_score': 0.85,
        'reasoning': 'Project involves systematic experimentation',
        'citations': ['CFR Title 26 § 1.41-4'],
        'technical_details': None
    }
    
    # Initialize agent with enhancement disabled
    agent = QualificationAgent(
        rag_tool=mock_rag_tool,
        youcom_client=mock_youcom_client,
        glm_reasoner=mock_glm_reasoner,
        enable_enhancement=False
    )
    
    # Run qualification
    time_entries = create_sample_time_entries()
    costs = create_sample_costs()
    
    result = agent.run(
        time_entries=time_entries,
        costs=costs,
        tax_year=2024
    )
    
    # Verify result does not include enhancement
    assert result.enhancement is None, "Result should not include enhancement when disabled"
    
    print("✓ Enhancement not called when disabled test passed")


def test_enhancement_failure_is_non_blocking():
    """Test that enhancement failures don't stop the qualification pipeline."""
    print("Testing enhancement failure is non-blocking...")
    
    # Create mock tools
    mock_rag_tool = Mock()
    mock_youcom_client = Mock()
    mock_glm_reasoner = Mock()
    
    # Mock RAG query response
    mock_rag_context = Mock()
    mock_rag_context.chunk_count = 3
    mock_rag_context.average_relevance = 0.85
    mock_rag_context.format_for_llm_prompt.return_value = "RAG context"
    mock_rag_context.chunks = [
        {'source': 'IRS Doc', 'page': 1, 'text': 'IRS guidance text'}
    ]
    mock_rag_tool.query.return_value = mock_rag_context
    
    # Mock You.com agent response
    mock_youcom_client.agent_run.return_value = {
        'output': [
            {
                'text': '''
                QUALIFICATION_PERCENTAGE: 100
                CONFIDENCE_SCORE: 0.85
                REASONING: Project involves systematic experimentation
                CITATIONS: CFR Title 26 § 1.41-4
                '''
            }
        ]
    }
    
    # Mock response parsing
    mock_youcom_client._parse_agent_response.return_value = {
        'qualification_percentage': 100.0,
        'confidence_score': 0.85,
        'reasoning': 'Project involves systematic experimentation',
        'citations': ['CFR Title 26 § 1.41-4'],
        'technical_details': None
    }
    
    # Mock You.com search and news to raise exceptions
    mock_youcom_client.search.side_effect = Exception("Search API failed")
    mock_youcom_client.news.side_effect = Exception("News API failed")
    
    # Initialize agent with enhancement enabled
    agent = QualificationAgent(
        rag_tool=mock_rag_tool,
        youcom_client=mock_youcom_client,
        glm_reasoner=mock_glm_reasoner,
        enable_enhancement=True
    )
    
    # Run qualification - should not raise exception
    time_entries = create_sample_time_entries()
    costs = create_sample_costs()
    
    try:
        result = agent.run(
            time_entries=time_entries,
            costs=costs,
            tax_year=2024
        )
        
        # Verify qualification completed successfully
        assert result is not None, "Result should not be None"
        assert len(result.qualified_projects) > 0, "Should have qualified projects"
        
        # Enhancement may be None or have errors - both are acceptable
        # The key is that qualification didn't fail
        
        print("✓ Enhancement failure is non-blocking test passed")
        
    except Exception as e:
        raise AssertionError(f"Qualification should not fail when enhancement fails: {e}")


def test_enhancement_result_structure():
    """Test that enhancement result has the correct structure."""
    print("Testing enhancement result structure...")
    
    enhancement = create_mock_enhancement_result()
    enhancement_dict = enhancement.to_dict()
    
    # Verify structure
    assert 'news_items' in enhancement_dict, "Should have news_items"
    assert 'search_results' in enhancement_dict, "Should have search_results"
    assert 'glm_summary' in enhancement_dict, "Should have glm_summary"
    assert 'execution_time_ms' in enhancement_dict, "Should have execution_time_ms"
    assert 'errors' in enhancement_dict, "Should have errors"
    
    # Verify types
    assert isinstance(enhancement_dict['news_items'], list), "news_items should be list"
    assert isinstance(enhancement_dict['search_results'], list), "search_results should be list"
    assert isinstance(enhancement_dict['glm_summary'], str), "glm_summary should be string"
    assert isinstance(enhancement_dict['execution_time_ms'], float), "execution_time_ms should be float"
    assert isinstance(enhancement_dict['errors'], list), "errors should be list"
    
    print("✓ Enhancement result structure test passed")


if __name__ == "__main__":
    print("Running Task 2 end-to-end tests...\n")
    
    try:
        test_enhancement_called_during_qualification()
        test_enhancement_not_called_when_disabled()
        test_enhancement_failure_is_non_blocking()
        test_enhancement_result_structure()
        
        print("\n✓ All end-to-end tests passed!")
        print("\nTask 2 verification complete:")
        print("- Enhancement is properly integrated into qualification workflow")
        print("- Enhancement can be enabled/disabled")
        print("- Enhancement failures are non-blocking")
        print("- Enhancement results have correct structure")
        print("- Backward compatibility is maintained")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
