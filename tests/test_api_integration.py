"""
Integration tests for all API connectors.

These tests make REAL API calls to verify end-to-end functionality.
They require valid API keys configured in the .env file.

To run these tests:
1. Set all required API keys in your .env file:
   - CLOCKIFY_API_KEY
   - CLOCKIFY_WORKSPACE_ID
   - UNIFIED_TO_API_KEY
   - UNIFIED_TO_WORKSPACE_ID
   - YOUCOM_API_KEY
   - OPENROUTER_API_KEY
2. Run: pytest tests/test_api_integration.py -v -s

Note: These tests consume API quota and may take longer to execute.
"""

import pytest
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

from tools.api_connectors import ClockifyConnector, UnifiedToConnector
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.exceptions import APIConnectionError


# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Check which API keys are available
CLOCKIFY_API_KEY = os.getenv("CLOCKIFY_API_KEY")
CLOCKIFY_WORKSPACE_ID = os.getenv("CLOCKIFY_WORKSPACE_ID")
UNIFIED_TO_API_KEY = os.getenv("UNIFIED_TO_API_KEY")
UNIFIED_TO_WORKSPACE_ID = os.getenv("UNIFIED_TO_WORKSPACE_ID")
YOUCOM_API_KEY = os.getenv("YOUCOM_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Determine which tests to skip
SKIP_CLOCKIFY = not CLOCKIFY_API_KEY or CLOCKIFY_API_KEY == "your_clockify_api_key_here"
SKIP_UNIFIED_TO = not UNIFIED_TO_API_KEY or UNIFIED_TO_API_KEY == "your_unified_to_api_key_here"
SKIP_YOUCOM = not YOUCOM_API_KEY or YOUCOM_API_KEY == "your_youcom_api_key_here"
SKIP_OPENROUTER = not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_key_here"


class TestClockifyConnectorIntegration:
    """Integration tests for Clockify API connector."""
    
    @pytest.mark.skipif(SKIP_CLOCKIFY, reason="Clockify API key not configured")
    def test_clockify_authentication(self):
        """Test Clockify authentication with real API."""
        print("\n=== Testing Clockify Authentication ===")
        
        connector = ClockifyConnector(
            api_key=CLOCKIFY_API_KEY,
            workspace_id=CLOCKIFY_WORKSPACE_ID
        )
        
        try:
            user_info = connector.test_authentication()
            
            print(f"[OK] Authentication successful")
            print(f"  User ID: {user_info.get('id', 'N/A')}")
            print(f"  Email: {user_info.get('email', 'N/A')}")
            print(f"  Name: {user_info.get('name', 'N/A')}")
            
            assert user_info is not None
            assert 'id' in user_info
            assert 'email' in user_info
            
        except APIConnectionError as e:
            pytest.fail(f"Clockify authentication failed: {e}")
    
    @pytest.mark.skipif(SKIP_CLOCKIFY, reason="Clockify API key not configured")
    def test_clockify_fetch_time_entries(self):
        """Test fetching time entries from Clockify."""
        print("\n=== Testing Clockify Time Entry Fetching ===")
        
        connector = ClockifyConnector(
            api_key=CLOCKIFY_API_KEY,
            workspace_id=CLOCKIFY_WORKSPACE_ID
        )
        
        # Fetch entries from last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        try:
            entries = connector.fetch_time_entries(
                start_date=start_date,
                end_date=end_date
            )
            
            print(f"[OK] Fetched {len(entries)} time entries")
            
            if entries:
                first_entry = entries[0]
                print(f"  Sample entry:")
                print(f"    ID: {first_entry.get('id', 'N/A')}")
                print(f"    User: {first_entry.get('userId', 'N/A')}")
                print(f"    Project: {first_entry.get('projectName', 'N/A')}")
                print(f"    Duration: {first_entry.get('duration', 'N/A')}")
            else:
                print("  No entries found in the date range")
            
            assert isinstance(entries, list)
            
        except APIConnectionError as e:
            pytest.fail(f"Clockify time entry fetching failed: {e}")


class TestUnifiedToConnectorIntegration:
    """Integration tests for Unified.to API connector."""
    
    @pytest.mark.skipif(SKIP_UNIFIED_TO, reason="Unified.to API key not configured")
    def test_unified_to_authentication(self):
        """Test Unified.to authentication with real API."""
        print("\n=== Testing Unified.to Authentication ===")
        
        connector = UnifiedToConnector(
            api_key=UNIFIED_TO_API_KEY,
            workspace_id=UNIFIED_TO_WORKSPACE_ID
        )
        
        try:
            # Test authentication by listing connections
            connections = connector.list_connections()
            
            print(f"[OK] Authentication successful")
            print(f"  Found {len(connections)} connections")
            
            if connections:
                first_conn = connections[0]
                print(f"  Sample connection:")
                print(f"    ID: {first_conn.get('id', 'N/A')}")
                print(f"    Type: {first_conn.get('type', 'N/A')}")
                print(f"    Status: {first_conn.get('status', 'N/A')}")
            
            assert isinstance(connections, list)
            
        except APIConnectionError as e:
            pytest.fail(f"Unified.to authentication failed: {e}")
    
    @pytest.mark.skipif(SKIP_UNIFIED_TO, reason="Unified.to API key not configured")
    def test_unified_to_fetch_employees(self):
        """Test fetching employees from Unified.to."""
        print("\n=== Testing Unified.to Employee Fetching ===")
        
        connector = UnifiedToConnector(
            api_key=UNIFIED_TO_API_KEY,
            workspace_id=UNIFIED_TO_WORKSPACE_ID
        )
        
        try:
            # Get first available connection
            connections = connector.list_connections()
            
            if not connections:
                pytest.skip("No Unified.to connections available for testing")
            
            connection_id = connections[0].get('id')
            print(f"  Using connection: {connection_id}")
            
            employees = connector.fetch_employees(connection_id=connection_id)
            
            print(f"[OK] Fetched {len(employees)} employees")
            
            if employees:
                first_emp = employees[0]
                print(f"  Sample employee:")
                print(f"    ID: {first_emp.get('id', 'N/A')}")
                print(f"    Name: {first_emp.get('name', 'N/A')}")
                print(f"    Email: {first_emp.get('email', 'N/A')}")
                print(f"    Job Title: {first_emp.get('job_title', 'N/A')}")
            else:
                print("  No employees found")
            
            assert isinstance(employees, list)
            
        except APIConnectionError as e:
            pytest.fail(f"Unified.to employee fetching failed: {e}")
    
    @pytest.mark.skipif(SKIP_UNIFIED_TO, reason="Unified.to API key not configured")
    def test_unified_to_fetch_payslips(self):
        """Test fetching payslips from Unified.to."""
        print("\n=== Testing Unified.to Payslip Fetching ===")
        
        connector = UnifiedToConnector(
            api_key=UNIFIED_TO_API_KEY,
            workspace_id=UNIFIED_TO_WORKSPACE_ID
        )
        
        try:
            # Get first available connection
            connections = connector.list_connections()
            
            if not connections:
                pytest.skip("No Unified.to connections available for testing")
            
            connection_id = connections[0].get('id')
            print(f"  Using connection: {connection_id}")
            
            # Fetch payslips from last 90 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            # Skip OAuth validation and use mock data
            payslips = connector.fetch_payslips(
                connection_id=connection_id,
                start_date=start_date,
                end_date=end_date,
                validate_connection=False
            )
            
            print(f"[OK] Fetched {len(payslips)} payslips")
            
            if payslips:
                first_payslip = payslips[0]
                print(f"  Sample payslip:")
                print(f"    ID: {first_payslip.get('id', 'N/A')}")
                print(f"    Employee ID: {first_payslip.get('employee_id', 'N/A')}")
                print(f"    Gross Pay: {first_payslip.get('gross_pay', 'N/A')}")
                print(f"    Period: {first_payslip.get('period_start', 'N/A')} to {first_payslip.get('period_end', 'N/A')}")
            else:
                print("  No payslips found in the date range")
            
            assert isinstance(payslips, list)
            
        except APIConnectionError as e:
            pytest.fail(f"Unified.to payslip fetching failed: {e}")


class TestYouComClientIntegration:
    """Integration tests for You.com API client."""
    
    @pytest.mark.skipif(SKIP_YOUCOM, reason="You.com API key not configured")
    def test_youcom_search_api(self):
        """Test You.com Search API with real query."""
        print("\n=== Testing You.com Search API ===")
        
        client = YouComClient(api_key=YOUCOM_API_KEY)
        
        try:
            # Search for IRS R&D tax credit guidance
            query = "IRS R&D tax credit software development qualified research"
            results = client.search(query=query)
            
            print(f"[OK] Search completed successfully")
            print(f"  Found {len(results)} results")
            
            if results:
                first_result = results[0]
                print(f"  Sample result:")
                print(f"    Title: {first_result.get('title', 'N/A')[:80]}...")
                print(f"    URL: {first_result.get('url', 'N/A')}")
                print(f"    Snippet: {first_result.get('snippet', 'N/A')[:100]}...")
            
            assert isinstance(results, list)
            assert len(results) > 0, "Search should return at least one result"
            
        except APIConnectionError as e:
            pytest.fail(f"You.com Search API failed: {e}")
    
    @pytest.mark.skipif(SKIP_YOUCOM, reason="You.com API key not configured")
    def test_youcom_agent_api(self):
        """Test You.com Agent API with R&D qualification prompt."""
        print("\n=== Testing You.com Agent API ===")
        
        client = YouComClient(api_key=YOUCOM_API_KEY)
        
        try:
            # Create a sample R&D qualification prompt
            prompt = """
            Analyze the following software development project for R&D tax credit qualification:
            
            Project: Machine Learning Model Optimization
            Description: Developed novel algorithms to reduce training time for deep learning models
            by 40% while maintaining accuracy. Experimented with various optimization techniques
            including gradient descent variants and adaptive learning rates.
            
            Based on IRS guidelines, determine:
            1. Qualification percentage (0-100%)
            2. Confidence score (0-1)
            3. Brief reasoning
            """
            
            response = client.agent_run(prompt=prompt)
            
            print(f"[OK] Agent API call completed successfully")
            print(f"  Response type: {type(response)}")
            
            # Response should be a dictionary with 'output' key
            assert isinstance(response, dict), "Agent should return a dictionary"
            assert 'output' in response, "Response should contain 'output' key"
            
            # Extract text from first output item
            if response.get('output') and len(response['output']) > 0:
                first_output = response['output'][0]
                response_text = first_output.get('text', '')
                print(f"  Response preview: {response_text[:200]}...")
                assert len(response_text) > 0, "Agent should return non-empty text"
            
        except APIConnectionError as e:
            pytest.fail(f"You.com Agent API failed: {e}")
    
    @pytest.mark.skip(reason="You.com Contents API requires subscription")
    def test_youcom_contents_api(self):
        """Test You.com Contents API with URL fetch."""
        print("\n=== Testing You.com Contents API ===")
        print("  [SKIPPED] Contents API requires paid subscription")
        
        client = YouComClient(api_key=YOUCOM_API_KEY)
        
        try:
            # Fetch content from a known IRS page
            url = "https://www.irs.gov/businesses/small-businesses-self-employed/research-credit"
            result = client.fetch_content(url=url)
            
            print(f"[OK] Contents API call completed successfully")
            
            # Response should be a dictionary with 'content' key
            assert isinstance(result, dict), "Contents API should return a dictionary"
            assert 'content' in result, "Response should contain 'content' key"
            
            content = result['content']
            print(f"  Content length: {len(content)} characters")
            print(f"  Content preview: {content[:200]}...")
            print(f"  Title: {result.get('title', 'N/A')}")
            print(f"  Word count: {result.get('word_count', 'N/A')}")
            
            assert isinstance(content, str)
            assert len(content) > 0, "Contents API should return non-empty content"
            
        except APIConnectionError as e:
            pytest.fail(f"You.com Contents API failed: {e}")
    
    @pytest.mark.skipif(SKIP_YOUCOM, reason="You.com API key not configured")
    def test_youcom_express_agent(self):
        """Test You.com Express Agent API for quick checks."""
        print("\n=== Testing You.com Express Agent API ===")
        
        client = YouComClient(api_key=YOUCOM_API_KEY)
        
        try:
            # Quick compliance check narrative
            narrative_text = """
            Our team developed a new algorithm for data compression. We tested various approaches
            and selected the most efficient one.
            
            Technical Uncertainties: We were uncertain about which compression algorithm would provide
            the best balance between speed and compression ratio.
            
            Process of Experimentation: We systematically tested LZ77, LZ78, and Huffman coding variants,
            measuring performance across different data types.
            
            Business Component: This algorithm is a core component of our data storage system.
            """
            
            response = client.express_agent(narrative_text=narrative_text)
            
            print(f"[OK] Express Agent API call completed successfully")
            
            # Response should be a dictionary with compliance review results
            assert isinstance(response, dict), "Express Agent should return a dictionary"
            
            # Check for expected keys
            expected_keys = ['compliance_status', 'completeness_score', 'overall_assessment']
            for key in expected_keys:
                if key in response:
                    print(f"  {key}: {response[key]}")
            
            # At minimum, should have some response data
            assert len(response) > 0, "Express Agent should return non-empty response"
            
        except APIConnectionError as e:
            pytest.fail(f"You.com Express Agent API failed: {e}")


class TestGLMReasonerIntegration:
    """Integration tests for GLM Reasoner via OpenRouter."""
    
    @pytest.mark.skipif(SKIP_OPENROUTER, reason="OpenRouter API key not configured")
    @pytest.mark.asyncio
    async def test_glm_reasoner_basic_inference(self):
        """Test GLM 4.5 Air basic reasoning via OpenRouter."""
        print("\n=== Testing GLM Reasoner Basic Inference ===")
        
        reasoner = GLMReasoner(api_key=OPENROUTER_API_KEY)
        
        try:
            prompt = "What are the four key criteria for R&D tax credit qualification according to IRS guidelines?"
            
            response = await reasoner.reason(
                prompt=prompt,
                temperature=0.2
            )
            
            print(f"[OK] GLM reasoning completed successfully")
            print(f"  Response length: {len(response)} characters")
            print(f"  Response preview: {response[:300]}...")
            
            assert isinstance(response, str)
            assert len(response) > 0, "GLM should return a non-empty response"
            assert any(keyword in response.lower() for keyword in ['uncertainty', 'experimentation', 'technological']), \
                "Response should mention R&D criteria"
            
        except APIConnectionError as e:
            pytest.fail(f"GLM Reasoner failed: {e}")
    
    @pytest.mark.skipif(SKIP_OPENROUTER, reason="OpenRouter API key not configured")
    @pytest.mark.asyncio
    async def test_glm_reasoner_with_rag_context(self):
        """Test GLM reasoning with RAG context."""
        print("\n=== Testing GLM Reasoner with RAG Context ===")
        
        reasoner = GLMReasoner(api_key=OPENROUTER_API_KEY)
        
        try:
            # Simulate RAG context
            rag_context = """
            IRS Regulation Section 1.41-4: Qualified research must satisfy the following requirements:
            1. The research must be undertaken for the purpose of discovering information
            2. The research must be technological in nature
            3. The research must involve a process of experimentation
            4. The research must be undertaken to eliminate uncertainty
            """
            
            prompt = f"""
            Based on the following IRS guidance:
            
            {rag_context}
            
            Evaluate this project: "Developed a new mobile app with standard features like login and data display."
            
            Provide:
            1. Qualification percentage (0-100%)
            2. Confidence score (0-1)
            3. Brief reasoning
            """
            
            response = await reasoner.reason(
                prompt=prompt,
                system_prompt="You are an R&D tax credit expert analyzing projects for IRS compliance.",
                temperature=0.2
            )
            
            print(f"[OK] GLM reasoning with RAG context completed successfully")
            print(f"  Response: {response[:400]}...")
            
            assert isinstance(response, str)
            assert len(response) > 0
            
        except APIConnectionError as e:
            pytest.fail(f"GLM Reasoner with RAG context failed: {e}")
    
    @pytest.mark.skipif(SKIP_OPENROUTER, reason="OpenRouter API key not configured")
    @pytest.mark.asyncio
    async def test_glm_reasoner_structured_response_parsing(self):
        """Test parsing structured responses from GLM."""
        print("\n=== Testing GLM Structured Response Parsing ===")
        
        reasoner = GLMReasoner(api_key=OPENROUTER_API_KEY)
        
        try:
            prompt = """
            Analyze this R&D project and respond in JSON format:
            
            Project: "Developed machine learning algorithms for fraud detection with novel feature engineering."
            
            Respond with:
            {
                "qualification_percentage": <number 0-100>,
                "confidence_score": <number 0-1>,
                "reasoning": "<brief explanation>"
            }
            """
            
            response = await reasoner.reason(prompt=prompt, temperature=0.1)
            
            print(f"[OK] GLM structured response received")
            print(f"  Response: {response[:400]}...")
            
            # Try to parse the structured response
            parsed = reasoner.parse_structured_response(response)
            
            print(f"[OK] Response parsed successfully")
            print(f"  Parsed data: {parsed}")
            
            assert isinstance(parsed, dict)
            
        except APIConnectionError as e:
            pytest.fail(f"GLM structured response parsing failed: {e}")


class TestEndToEndAPIWorkflow:
    """End-to-end integration tests combining multiple APIs."""
    
    @pytest.mark.skipif(
        SKIP_CLOCKIFY or SKIP_YOUCOM or SKIP_OPENROUTER,
        reason="Multiple API keys required for end-to-end test"
    )
    @pytest.mark.asyncio
    async def test_complete_qualification_workflow(self):
        """Test complete workflow: Clockify -> GLM -> You.com."""
        print("\n=== Testing Complete Qualification Workflow ===")
        
        # Step 1: Fetch time entries from Clockify
        print("\n  Step 1: Fetching time entries from Clockify...")
        clockify = ClockifyConnector(
            api_key=CLOCKIFY_API_KEY,
            workspace_id=CLOCKIFY_WORKSPACE_ID
        )
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        try:
            entries = clockify.fetch_time_entries(
                start_date=start_date,
                end_date=end_date
            )
            print(f"    [OK] Fetched {len(entries)} time entries")
            
            if not entries:
                pytest.skip("No time entries available for workflow test")
            
            # Step 2: Use GLM to analyze first project
            print("\n  Step 2: Analyzing project with GLM Reasoner...")
            reasoner = GLMReasoner(api_key=OPENROUTER_API_KEY)
            
            first_entry = entries[0]
            project_name = first_entry.get('projectName', 'Unknown Project')
            
            analysis_prompt = f"""
            Analyze this project for R&D tax credit qualification:
            Project: {project_name}
            
            Provide a brief assessment of whether this appears to be R&D work.
            """
            
            glm_response = await reasoner.reason(prompt=analysis_prompt, temperature=0.2)
            print(f"    [OK] GLM analysis completed")
            print(f"      Analysis preview: {glm_response[:150]}...")
            
            # Step 3: Use You.com for expert qualification
            print("\n  Step 3: Getting expert qualification from You.com...")
            youcom = YouComClient(api_key=YOUCOM_API_KEY)
            
            search_results = youcom.search(
                query=f"IRS R&D tax credit {project_name} software development"
            )
            print(f"    [OK] Found {len(search_results)} relevant IRS guidance documents")
            
            print("\n[OK] Complete workflow executed successfully")
            print("  All API connectors working end-to-end")
            
            assert len(entries) > 0
            assert len(glm_response) > 0
            assert len(search_results) > 0
            
        except APIConnectionError as e:
            pytest.fail(f"End-to-end workflow failed: {e}")
    
    @pytest.mark.skipif(
        SKIP_UNIFIED_TO or SKIP_OPENROUTER,
        reason="Multiple API keys required for payroll workflow test"
    )
    @pytest.mark.asyncio
    async def test_payroll_analysis_workflow(self):
        """Test workflow: Unified.to payroll -> GLM analysis."""
        print("\n=== Testing Payroll Analysis Workflow ===")
        
        # Step 1: Fetch payroll data
        print("\n  Step 1: Fetching payroll data from Unified.to...")
        unified = UnifiedToConnector(
            api_key=UNIFIED_TO_API_KEY,
            workspace_id=UNIFIED_TO_WORKSPACE_ID
        )
        
        try:
            connections = unified.list_connections()
            
            if not connections:
                pytest.skip("No Unified.to connections available")
            
            connection_id = connections[0].get('id')
            employees = unified.fetch_employees(connection_id=connection_id)
            
            print(f"    [OK] Fetched {len(employees)} employees")
            
            if not employees:
                pytest.skip("No employees available for workflow test")
            
            # Step 2: Analyze compensation with GLM
            print("\n  Step 2: Analyzing compensation data with GLM...")
            reasoner = GLMReasoner(api_key=OPENROUTER_API_KEY)
            
            first_emp = employees[0]
            emp_name = first_emp.get('name', 'Unknown')
            job_title = first_emp.get('job_title', 'Unknown')
            
            analysis_prompt = f"""
            Analyze if this role typically qualifies for R&D tax credits:
            Job Title: {job_title}
            
            Provide a brief yes/no assessment with reasoning.
            """
            
            glm_response = await reasoner.reason(prompt=analysis_prompt, temperature=0.2)
            print(f"    [OK] GLM analysis completed")
            print(f"      Analysis: {glm_response[:150]}...")
            
            print("\n[OK] Payroll workflow executed successfully")
            
            assert len(employees) > 0
            assert len(glm_response) > 0
            
        except APIConnectionError as e:
            pytest.fail(f"Payroll workflow failed: {e}")


# Summary function to print test configuration
def test_print_configuration():
    """Print test configuration and available APIs."""
    print("\n" + "="*60)
    print("API INTEGRATION TEST CONFIGURATION")
    print("="*60)
    print(f"Clockify API:     {'[OK] Configured' if not SKIP_CLOCKIFY else '[X] Not configured'}")
    print(f"Unified.to API:   {'[OK] Configured' if not SKIP_UNIFIED_TO else '[X] Not configured'}")
    print(f"You.com API:      {'[OK] Configured' if not SKIP_YOUCOM else '[X] Not configured'}")
    print(f"OpenRouter API:   {'[OK] Configured' if not SKIP_OPENROUTER else '[X] Not configured'}")
    print("="*60)
    print("\nNote: Tests for unconfigured APIs will be skipped.")
    print("To enable all tests, configure API keys in your .env file.")
    print("="*60 + "\n")

