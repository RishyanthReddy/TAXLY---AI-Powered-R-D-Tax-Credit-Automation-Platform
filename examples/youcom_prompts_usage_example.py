"""
Usage Examples for You.com Prompt Templates

This script demonstrates how to use the You.com-specific prompt templates
for R&D tax credit qualification, narrative generation, compliance review,
and IRS guidance searches.

Requirements: 2.3, 4.1, 4.3, 6.1
"""

from tools.prompt_templates import (
    populate_youcom_qualification_prompt,
    populate_youcom_narrative_template_fetch,
    populate_youcom_compliance_review_prompt,
    populate_youcom_search_query_template,
    create_youcom_search_query,
    create_batch_youcom_qualification_prompts
)


def example_qualification_prompt():
    """Example: Create a You.com qualification prompt"""
    print("=" * 80)
    print("EXAMPLE 1: You.com Qualification Prompt")
    print("=" * 80)
    
    # Sample RAG context from IRS documents
    rag_context = """
    From CFR Title 26 § 1.41-4:
    
    Qualified research must meet the four-part test:
    1. The research must be technological in nature
    2. It must be undertaken to eliminate uncertainty
    3. It must involve a process of experimentation
    4. It must be undertaken for a qualified purpose
    
    Software development can qualify if it involves developing new or
    significantly improved functionality, performance, reliability, or quality.
    """
    
    # Create qualification prompt
    prompt = populate_youcom_qualification_prompt(
        rag_context=rag_context,
        project_name="API Performance Optimization",
        project_description="Redesign API architecture to reduce response times from 2s to 200ms",
        technical_activities="""
        - Algorithm optimization for database queries
        - Implementation of multi-level caching strategy
        - Development of custom connection pooling
        - Load balancing algorithm design
        """,
        total_hours=150.5,
        total_cost=18750.00,
        employee_roles="Senior Software Engineers, Database Architects"
    )
    
    print(prompt[:500] + "...\n")
    print(f"Prompt length: {len(prompt)} characters")
    print()


def example_narrative_template_fetch():
    """Example: Get You.com narrative template fetch prompt"""
    print("=" * 80)
    print("EXAMPLE 2: You.com Narrative Template Fetch")
    print("=" * 80)
    
    prompt = populate_youcom_narrative_template_fetch()
    
    print(prompt[:500] + "...\n")
    print("Use this prompt with You.com Contents API to retrieve narrative templates")
    print()


def example_compliance_review():
    """Example: Create a You.com compliance review prompt"""
    print("=" * 80)
    print("EXAMPLE 3: You.com Compliance Review Prompt")
    print("=" * 80)
    
    # Sample narrative to review
    narrative = """
    Project Overview:
    This project aimed to develop a new machine learning model for fraud detection
    in real-time payment processing systems.
    
    Technical Uncertainties:
    At the project's outset, it was uncertain whether we could achieve sub-100ms
    inference times while maintaining 95%+ accuracy on our fraud detection model.
    Existing solutions either had high latency or poor accuracy.
    
    Process of Experimentation:
    We systematically evaluated multiple approaches:
    1. Traditional rule-based systems (baseline)
    2. Random Forest models with feature engineering
    3. Neural network architectures (LSTM, Transformer)
    4. Hybrid approaches combining rules and ML
    
    Each approach was tested with production-like data volumes and latency requirements.
    """
    
    prompt = populate_youcom_compliance_review_prompt(narrative)
    
    print(prompt[:500] + "...\n")
    print("Use this prompt with You.com Express Agent for compliance review")
    print()


def example_search_query():
    """Example: Create a You.com search query for IRS guidance"""
    print("=" * 80)
    print("EXAMPLE 4: You.com Search Query Template")
    print("=" * 80)
    
    # Create search query template
    prompt = populate_youcom_search_query_template(
        tax_year=2024,
        industry="Software Development",
        topic="Process of Experimentation",
        search_query="IRS Section 41 software development experimentation requirements 2024"
    )
    
    print(prompt[:500] + "...\n")
    
    # Also demonstrate the helper function
    search_query = create_youcom_search_query(
        tax_year=2024,
        industry="Software Development",
        keywords=["Section 41", "qualified research", "four-part test"]
    )
    
    print(f"Generated search query: {search_query}")
    print()


def example_batch_qualification():
    """Example: Create batch You.com qualification prompts"""
    print("=" * 80)
    print("EXAMPLE 5: Batch You.com Qualification Prompts")
    print("=" * 80)
    
    # Sample projects
    projects = [
        {
            "name": "API Optimization",
            "description": "Improve API response times",
            "technical_activities": "Algorithm optimization, caching",
            "total_hours": 120.0,
            "total_cost": 15000.00,
            "employee_roles": "Software Engineers"
        },
        {
            "name": "ML Model Development",
            "description": "Develop fraud detection model",
            "technical_activities": "Model training, feature engineering",
            "total_hours": 200.0,
            "total_cost": 25000.00,
            "employee_roles": "Data Scientists, ML Engineers"
        }
    ]
    
    # Sample RAG contexts (one per project)
    rag_contexts = [
        "IRS guidance on software development qualification...",
        "IRS guidance on machine learning and AI research..."
    ]
    
    # Create batch prompts
    prompts = create_batch_youcom_qualification_prompts(projects, rag_contexts)
    
    print(f"Created {len(prompts)} qualification prompts")
    print(f"\nFirst prompt preview:")
    print(prompts[0][:300] + "...\n")
    print(f"\nSecond prompt preview:")
    print(prompts[1][:300] + "...")
    print()


def example_integration_workflow():
    """Example: Complete workflow using You.com prompts"""
    print("=" * 80)
    print("EXAMPLE 6: Complete You.com Integration Workflow")
    print("=" * 80)
    
    print("""
    Step 1: Search for recent IRS guidance
    ----------------------------------------
    Use populate_youcom_search_query_template() to search for:
    - Recent rulings on software development
    - Updates to Section 41 regulations
    - Industry-specific guidance
    
    Step 2: Qualify projects with You.com Agent API
    ------------------------------------------------
    Use populate_youcom_qualification_prompt() with:
    - RAG context from local IRS documents
    - Project details and activities
    - Employee roles and costs
    
    Step 3: Fetch narrative templates
    ----------------------------------
    Use populate_youcom_narrative_template_fetch() to:
    - Get standardized narrative templates
    - Retrieve best practices for documentation
    
    Step 4: Review narratives for compliance
    -----------------------------------------
    Use populate_youcom_compliance_review_prompt() to:
    - Check narratives against IRS requirements
    - Identify missing elements
    - Get suggestions for improvement
    
    This workflow ensures comprehensive, compliant R&D tax credit documentation.
    """)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("YOU.COM PROMPT TEMPLATES - USAGE EXAMPLES")
    print("=" * 80 + "\n")
    
    example_qualification_prompt()
    example_narrative_template_fetch()
    example_compliance_review()
    example_search_query()
    example_batch_qualification()
    example_integration_workflow()
    
    print("\n" + "=" * 80)
    print("All examples completed successfully!")
    print("=" * 80 + "\n")
