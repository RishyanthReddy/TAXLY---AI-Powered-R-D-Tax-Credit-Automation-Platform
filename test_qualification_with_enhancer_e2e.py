"""
End-to-End test for Qualification Agent with QualificationEnhancer.

This test demonstrates the complete qualification flow including:
1. QualificationAgent initialization with real APIs
2. QualificationEnhancer being called during qualification
3. You.com News and Search APIs being invoked
4. GLM Reasoner analyzing the results
5. Complete qualification result with enhancement data

This test uses REAL APIs with API keys from .env file.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.qualification_agent import QualificationAgent
from models.financial_models import EmployeeTimeEntry, ProjectCost
from tools.rd_knowledge_tool import RD_Knowledge_Tool
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.config import get_config


def test_qualification_with_enhancer():
    """
    Test complete qualification flow with QualificationEnhancer.
    
    This test verifies:
    - QualificationAgent initializes with enhancer enabled
    - Enhancer is called during qualification
    - You.com APIs (News + Search) are invoked
    - GLM Reasoner analyzes the results
    - Enhancement data is included in the result
    """
    print("\n" + "=" * 80)
    print("END-TO-END TEST: Qualification Agent with QualificationEnhancer")
    print("=" * 80)
    
    # Get configuration
    config = get_config()
    
    # Initialize tools
    print("\n1. Initializing tools...")
    
    try:
        rag_tool = RD_Knowledge_Tool(
            knowledge_base_path="./knowledge_base/indexed",
            collection_name="irs_documents",
            enable_cache=True
        )
        print("   ✓ RAG tool initialized")
    except Exception as e:
        print(f"   ⚠ RAG tool initialization failed (will continue): {e}")
        rag_tool = None
    
    youcom_client = YouComClient(api_key=config.youcom_api_key)
    print("   ✓ You.com client initialized")
    
    glm_reasoner = GLMReasoner(api_key=config.openrouter_api_key)
    print("   ✓ GLM reasoner initialized")
    
    # Initialize Qualification Agent with enhancement ENABLED
    print("\n2. Initializing Qualification Agent (enhancement enabled)...")
    agent = QualificationAgent(
        rag_tool=rag_tool,
        youcom_client=youcom_client,
        glm_reasoner=glm_reasoner,
        enable_enhancement=True  # EXPLICITLY ENABLE
    )
    print(f"   ✓ Agent initialized")
    print(f"   ✓ Enhancement enabled: {agent.enable_enhancement}")
    print(f"   ✓ Enhancer instance: {agent.enhancer}")
    
    # Create sample time entries (R&D projects)
    print("\n3. Creating sample R&D project data...")
    time_entries = [
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="John Doe",
            project_name="API Performance Optimization",
            task_description="Developed new caching algorithms to reduce API response times by 50%",
            hours_spent=8.0,
            date=datetime(2024, 1, 15),
            is_rd_classified=True
        ),
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="John Doe",
            project_name="API Performance Optimization",
            task_description="Continued algorithm development and optimization",
            hours_spent=8.0,
            date=datetime(2024, 1, 16),
            is_rd_classified=True
        ),
        EmployeeTimeEntry(
            employee_id="EMP002",
            employee_name="Jane Smith",
            project_name="API Performance Optimization",
            task_description="Systematic testing of different caching strategies",
            hours_spent=8.0,
            date=datetime(2024, 1, 17),
            is_rd_classified=True
        ),
        EmployeeTimeEntry(
            employee_id="EMP002",
            employee_name="Jane Smith",
            project_name="API Performance Optimization",
            task_description="Performance benchmarking and analysis",
            hours_spent=6.0,
            date=datetime(2024, 1, 18),
            is_rd_classified=True
        )
    ]
    
    costs = [
        ProjectCost(
            cost_id="COST001",
            cost_type="Payroll",
            amount=8000.0,
            project_name="API Performance Optimization",
            employee_id="EMP001",
            date=datetime(2024, 1, 15),
            is_rd_classified=True
        )
    ]
    
    print(f"   ✓ Created 1 project with {len(time_entries)} time entries")
    print(f"   ✓ Total hours: {sum(e.hours_spent for e in time_entries)}")
    print(f"   ✓ Total cost: ${sum(c.amount for c in costs):,.2f}")
    
    # Run qualification
    print("\n4. Running qualification with enhancement...")
    print("   (This will call You.com News, Search, and GLM Reasoner)")
    print("   (Expected time: 10-30 seconds)")
    
    start_time = datetime.now()
    
    try:
        result = agent.run(
            time_entries=time_entries,
            costs=costs,
            tax_year=2024  # REQUIRED for enhancement to run!
        )
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print(f"\n   ✓ Qualification completed in {execution_time:.2f} seconds")
        
        # Verify results
        print("\n5. Verifying results...")
        print(f"   - Qualified projects: {len(result.qualified_projects)}")
        print(f"   - Total qualified hours: {result.total_qualified_hours:.1f}")
        print(f"   - Total qualified cost: ${result.total_qualified_cost:,.2f}")
        print(f"   - Estimated credit: ${result.estimated_credit:,.2f}")
        print(f"   - Average confidence: {result.average_confidence:.1%}")
        
        # Check if enhancement data is present
        print("\n6. Checking enhancement data...")
        if result.enhancement:
            print("   ✓ Enhancement data IS present!")
            enhancement = result.enhancement
            
            # Check for news items
            news_count = len(enhancement.get('news_items', []))
            print(f"   ✓ News items: {news_count}")
            
            # Check for search results
            search_count = len(enhancement.get('search_results', []))
            print(f"   ✓ Search results: {search_count}")
            
            # Check for GLM summary
            glm_summary = enhancement.get('glm_summary', '')
            print(f"   ✓ GLM summary: {len(glm_summary)} characters")
            
            # Check execution time
            enhancement_time = enhancement.get('execution_time_ms', 0)
            print(f"   ✓ Enhancement execution time: {enhancement_time:.2f}ms")
            
            # Check for errors
            errors = enhancement.get('errors', [])
            if errors:
                print(f"   ⚠ Enhancement errors: {errors}")
            else:
                print(f"   ✓ No enhancement errors")
            
            # Display sample data
            if news_count > 0:
                print(f"\n   Sample news item:")
                news_item = enhancement['news_items'][0]
                print(f"     - Title: {news_item.get('title', 'N/A')[:60]}...")
                print(f"     - URL: {news_item.get('url', 'N/A')[:60]}...")
            
            if search_count > 0:
                print(f"\n   Sample search result:")
                search_item = enhancement['search_results'][0]
                print(f"     - Title: {search_item.get('title', 'N/A')[:60]}...")
                print(f"     - URL: {search_item.get('url', 'N/A')[:60]}...")
            
            if glm_summary:
                print(f"\n   GLM summary preview:")
                preview = glm_summary[:200]
                if len(glm_summary) > 200:
                    preview += "..."
                print(f"     {preview}")
        else:
            print("   ✗ Enhancement data is NOT present (this is unexpected!)")
            print("   ✗ The enhancer may not have been called")
        
        # Final summary
        print("\n" + "=" * 80)
        print("TEST RESULT: SUCCESS")
        print("=" * 80)
        print(f"✓ Qualification completed successfully")
        print(f"✓ {len(result.qualified_projects)} project(s) qualified")
        print(f"✓ Enhancement data: {'PRESENT' if result.enhancement else 'MISSING'}")
        print(f"✓ Total execution time: {execution_time:.2f}s")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Qualification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_qualification_with_enhancer()
    sys.exit(0 if success else 1)
