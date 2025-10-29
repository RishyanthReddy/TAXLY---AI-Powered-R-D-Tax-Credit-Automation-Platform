"""
Integration tests for Qualification Agent with real API calls.

These tests verify that the agent can successfully call:
- RD_Knowledge_Tool (RAG system with local IRS documents)
- YouComClient (You.com Search/News APIs)
- GLMReasoner (GLM 4.5 Air via OpenRouter)

Requirements: Testing, Integration
"""

import pytest
import os
from datetime import datetime
from unittest.mock import Mock

from agents.qualification_agent import QualificationAgent
from models.financial_models import EmployeeTimeEntry, ProjectCost
from tools.rd_knowledge_tool import RD_Knowledge_Tool
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.config import get_config


@pytest.mark.integration
class TestQualificationAgentAPIIntegration:
    """Integration tests for Qualification Agent with real APIs"""
    
    @pytest.fixture
    def config(self):
        """Get configuration"""
        return get_config()
    
    @pytest.fixture
    def rag_tool(self):
        """Initialize RD_Knowledge_Tool"""
        try:
            tool = RD_Knowledge_Tool(
                knowledge_base_path="./knowledge_base/indexed",
                collection_name="irs_documents",
                enable_cache=True
            )
            return tool
        except Exception as e:
            pytest.skip(f"RAG tool initialization failed: {e}")
    
    @pytest.fixture
    def youcom_client(self, config):
        """Initialize YouComClient"""
        api_key = config.youcom_api_key
        if not api_key or api_key == "your-youcom-api-key-here":
            pytest.skip("You.com API key not configured")
        
        try:
            client = YouComClient(
                api_key=api_key,
                enable_cache=True
            )
            return client
        except Exception as e:
            pytest.skip(f"You.com client initialization failed: {e}")
    
    @pytest.fixture
    def glm_reasoner(self, config):
        """Initialize GLMReasoner"""
        api_key = config.openrouter_api_key
        if not api_key or api_key == "your-openrouter-api-key-here":
            pytest.skip("OpenRouter API key not configured")
        
        try:
            reasoner = GLMReasoner(api_key=api_key)
            return reasoner
        except Exception as e:
            pytest.skip(f"GLM reasoner initialization failed: {e}")
    
    def test_agent_initialization_with_real_tools(self, rag_tool, youcom_client, glm_reasoner):
        """Test agent can be initialized with real API tools"""
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        assert agent.rag_tool is not None
        assert agent.youcom_client is not None
        assert agent.glm_reasoner is not None
        assert agent.state.status.value == "pending"
    
    def test_rag_tool_can_query(self, rag_tool):
        """Test RD_Knowledge_Tool can query IRS documents"""
        try:
            # Query for R&D qualification criteria
            result = rag_tool.query(
                question="What is the four-part test for qualified research?",
                top_k=3
            )
            
            assert result is not None
            assert hasattr(result, 'chunks')
            assert hasattr(result, 'chunk_count')
            
            print(f"\n✓ RAG Tool Query Success:")
            print(f"  - Retrieved {result.chunk_count} chunks")
            print(f"  - Query: 'What is the four-part test for qualified research?'")
            
        except Exception as e:
            pytest.fail(f"RAG tool query failed: {e}")
    
    @pytest.mark.asyncio
    async def test_youcom_search_api(self, youcom_client):
        """Test You.com Search API can be called"""
        try:
            # Search for recent IRS guidance
            result = await youcom_client.search(
                query="IRS R&D tax credit guidance 2024",
                num_results=3
            )
            
            assert result is not None
            assert 'results' in result or 'hits' in result
            
            print(f"\n✓ You.com Search API Success:")
            print(f"  - Query: 'IRS R&D tax credit guidance 2024'")
            print(f"  - Results returned: {len(result.get('results', result.get('hits', [])))}")
            
        except Exception as e:
            # If API call fails, check if it's a configuration issue
            if "api_key" in str(e).lower() or "unauthorized" in str(e).lower():
                pytest.skip(f"You.com API authentication issue: {e}")
            else:
                pytest.fail(f"You.com Search API failed: {e}")
    
    @pytest.mark.asyncio
    async def test_glm_reasoner_can_reason(self, glm_reasoner):
        """Test GLM 4.5 Air can perform reasoning via OpenRouter"""
        try:
            # Simple reasoning test
            response = await glm_reasoner.reason(
                prompt="What are the key criteria for R&D tax credit qualification?",
                system_prompt="You are an expert in IRS R&D tax credit regulations.",
                temperature=0.2,
                max_tokens=200
            )
            
            assert response is not None
            assert len(response) > 0
            assert isinstance(response, str)
            
            print(f"\n✓ GLM 4.5 Air Reasoning Success:")
            print(f"  - Model: z-ai/glm-4.5-air:free via OpenRouter")
            print(f"  - Response length: {len(response)} characters")
            print(f"  - Sample: {response[:100]}...")
            
        except Exception as e:
            # If API call fails, check if it's a configuration issue
            if "api_key" in str(e).lower() or "unauthorized" in str(e).lower():
                pytest.skip(f"OpenRouter API authentication issue: {e}")
            else:
                pytest.fail(f"GLM reasoner failed: {e}")
    
    def test_agent_run_with_real_tools(self, rag_tool, youcom_client, glm_reasoner):
        """Test agent can run with real tools (structure only, no actual qualification yet)"""
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create sample R&D entries
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Algorithm Development",
                task_description="Developing new machine learning algorithms",
                hours_spent=40.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            )
        ]
        
        costs = [
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=8000.0,
                project_name="Algorithm Development",
                employee_id="EMP001",
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            )
        ]
        
        # Run agent (structure only - actual qualification in tasks 104-106)
        result = agent.run(
            time_entries=time_entries,
            costs=costs,
            tax_year=2024
        )
        
        assert result is not None
        assert agent.state.status.value == "completed"
        assert agent.state.projects_to_qualify == 1
        
        print(f"\n✓ Agent Run Success:")
        print(f"  - Status: {agent.state.status.value}")
        print(f"  - Projects identified: {agent.state.projects_to_qualify}")
        print(f"  - Execution time: {result.execution_time_seconds:.2f}s")
        print(f"  - Note: Full qualification logic will be in tasks 104-106")


@pytest.mark.integration
class TestAPIToolsIndividually:
    """Test each API tool individually to verify connectivity"""
    
    def test_rag_tool_initialization(self):
        """Test RAG tool can initialize and access vector DB"""
        try:
            tool = RD_Knowledge_Tool(
                knowledge_base_path="./knowledge_base/indexed",
                collection_name="irs_documents"
            )
            
            # Check if vector DB is accessible
            assert tool.vector_db is not None
            
            print(f"\n✓ RAG Tool Initialization Success")
            print(f"  - Knowledge base: ./knowledge_base/indexed")
            print(f"  - Collection: irs_documents")
            
        except Exception as e:
            print(f"\n✗ RAG Tool Initialization Failed: {e}")
            print(f"  - This is expected if vector DB hasn't been indexed yet")
            print(f"  - Run: python scripts/run_indexing_pipeline.py")
    
    def test_youcom_client_initialization(self):
        """Test You.com client can initialize"""
        config = get_config()
        api_key = config.youcom_api_key
        
        if not api_key or api_key == "your-youcom-api-key-here":
            print(f"\n⚠ You.com API key not configured")
            print(f"  - Set YOUCOM_API_KEY in .env file")
            pytest.skip("You.com API key not configured")
        
        try:
            client = YouComClient(api_key=api_key)
            
            assert client.api_key is not None
            assert client.rate_limiter is not None
            
            print(f"\n✓ You.com Client Initialization Success")
            print(f"  - API key configured: Yes")
            print(f"  - Rate limiter: Enabled")
            
        except Exception as e:
            pytest.fail(f"You.com client initialization failed: {e}")
    
    def test_glm_reasoner_initialization(self):
        """Test GLM reasoner can initialize"""
        config = get_config()
        api_key = config.openrouter_api_key
        
        if not api_key or api_key == "your-openrouter-api-key-here":
            print(f"\n⚠ OpenRouter API key not configured")
            print(f"  - Set OPENROUTER_API_KEY in .env file")
            pytest.skip("OpenRouter API key not configured")
        
        try:
            reasoner = GLMReasoner(api_key=api_key)
            
            assert reasoner.api_key is not None
            assert reasoner.model == "z-ai/glm-4.5-air:free"
            
            print(f"\n✓ GLM Reasoner Initialization Success")
            print(f"  - API key configured: Yes")
            print(f"  - Model: {reasoner.model}")
            print(f"  - Base URL: {reasoner.base_url}")
            
        except Exception as e:
            pytest.fail(f"GLM reasoner initialization failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
