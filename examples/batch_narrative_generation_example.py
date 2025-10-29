"""
Example: Batch Narrative Generation with Audit Trail Agent

This example demonstrates how to use the Audit Trail Agent to generate
narratives for multiple qualified projects concurrently.

The batch generation feature:
- Processes multiple projects in parallel
- Respects rate limits with configurable concurrency
- Provides real-time progress updates
- Handles errors gracefully without stopping the entire batch
- Logs all You.com API calls for tracking

Requirements: 4.1
"""

import asyncio
from datetime import datetime
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from agents.audit_trail_agent import AuditTrailAgent
from models.tax_models import QualifiedProject
from models.websocket_models import StatusUpdateMessage
from utils.config import get_config


def status_callback(message: StatusUpdateMessage):
    """
    Callback function to receive real-time status updates.
    
    In a real application, this would broadcast to WebSocket clients.
    """
    print(f"[{message.timestamp.strftime('%H:%M:%S')}] {message.stage.value}: {message.details}")


async def main():
    """
    Main example demonstrating batch narrative generation.
    """
    print("=" * 80)
    print("Batch Narrative Generation Example")
    print("=" * 80)
    print()
    
    # Load configuration
    config = get_config()
    
    # Initialize tools
    print("Initializing tools...")
    youcom_client = YouComClient(api_key=config.youcom_api_key)
    glm_reasoner = GLMReasoner(api_key=config.openrouter_api_key)
    
    # Initialize Audit Trail Agent with status callback
    agent = AuditTrailAgent(
        youcom_client=youcom_client,
        glm_reasoner=glm_reasoner,
        status_callback=status_callback
    )
    
    print("✓ Audit Trail Agent initialized")
    print()
    
    # Create sample qualified projects
    print("Creating sample qualified projects...")
    qualified_projects = [
        QualifiedProject(
            project_name="API Performance Optimization",
            qualified_hours=150.5,
            qualified_cost=18750.00,
            confidence_score=0.92,
            qualification_percentage=85.0,
            supporting_citation=(
                "The project involved developing novel algorithms to reduce API latency "
                "by 40%. Technical uncertainty existed regarding the optimal caching strategy "
                "and database query optimization approach."
            ),
            reasoning=(
                "This project meets the four-part test: (1) Technical uncertainty existed "
                "regarding achieving the 40% latency reduction target, (2) A systematic "
                "process of experimentation was used to evaluate multiple approaches, "
                "(3) The work relied on principles of computer science and software engineering, "
                "(4) The purpose was to develop a new or improved business component."
            ),
            irs_source="CFR Title 26 § 1.41-4(a)(1)",
            technical_details={
                'technological_uncertainty': 'Uncertainty about achieving 40% latency reduction',
                'experimentation_process': 'Evaluated 5 different caching strategies',
                'business_component': 'High-Performance API Gateway'
            }
        ),
        QualifiedProject(
            project_name="Machine Learning Model Development",
            qualified_hours=280.0,
            qualified_cost=35000.00,
            confidence_score=0.95,
            qualification_percentage=95.0,
            supporting_citation=(
                "The project involved developing a novel machine learning model for "
                "predictive analytics. Significant technical uncertainty existed regarding "
                "model accuracy and training efficiency."
            ),
            reasoning=(
                "This project clearly qualifies under the four-part test with high confidence. "
                "The team conducted extensive experimentation with multiple ML architectures "
                "and training approaches to achieve the required accuracy threshold."
            ),
            irs_source="CFR Title 26 § 1.41-4(a)(2)",
            technical_details={
                'technological_uncertainty': 'Achieving 95% accuracy with limited training data',
                'experimentation_process': 'Tested 8 different model architectures',
                'business_component': 'Predictive Analytics Engine'
            }
        ),
        QualifiedProject(
            project_name="Database Migration System",
            qualified_hours=200.0,
            qualified_cost=25000.00,
            confidence_score=0.88,
            qualification_percentage=80.0,
            supporting_citation=(
                "The project involved developing an automated database migration system "
                "with zero-downtime capabilities. Technical challenges included maintaining "
                "data consistency during live migration."
            ),
            reasoning=(
                "This project qualifies as R&D due to the technical uncertainties involved "
                "in achieving zero-downtime migration while ensuring data consistency. "
                "Multiple approaches were evaluated through systematic experimentation."
            ),
            irs_source="CFR Title 26 § 1.41-4(a)(3)"
        ),
        QualifiedProject(
            project_name="Real-Time Analytics Dashboard",
            qualified_hours=175.0,
            qualified_cost=21875.00,
            confidence_score=0.85,
            qualification_percentage=82.0,
            supporting_citation=(
                "The project involved developing a real-time analytics dashboard capable "
                "of processing 1M+ events per second. Technical uncertainty existed regarding "
                "the streaming architecture and data aggregation approach."
            ),
            reasoning=(
                "This project meets R&D criteria through the systematic evaluation of "
                "multiple streaming architectures and aggregation strategies to achieve "
                "the required performance targets."
            ),
            irs_source="CFR Title 26 § 1.41-4(a)(1)"
        ),
        QualifiedProject(
            project_name="Security Framework Enhancement",
            qualified_hours=120.0,
            qualified_cost=15000.00,
            confidence_score=0.78,
            qualification_percentage=75.0,
            supporting_citation=(
                "The project involved enhancing the security framework to meet new "
                "compliance requirements. Technical challenges included implementing "
                "advanced encryption without impacting performance."
            ),
            reasoning=(
                "This project qualifies due to technical uncertainties in balancing "
                "security requirements with performance constraints. Multiple encryption "
                "approaches were evaluated."
            ),
            irs_source="CFR Title 26 § 1.41-4(a)(4)"
        )
    ]
    
    print(f"✓ Created {len(qualified_projects)} qualified projects")
    print()
    
    # Generate narratives in batch
    print("Starting batch narrative generation...")
    print("(This will process projects concurrently with max_concurrent=5)")
    print()
    
    # Set up agent state
    agent.state.projects_to_process = len(qualified_projects)
    
    # Run batch generation
    narratives = await agent._generate_narratives_batch(
        qualified_projects=qualified_projects,
        template_url=None,  # Can optionally provide a template URL
        max_concurrent=5  # Process up to 5 projects concurrently
    )
    
    print()
    print("=" * 80)
    print("Batch Generation Complete!")
    print("=" * 80)
    print()
    
    # Display results
    print(f"Successfully generated {len(narratives)} narratives")
    print()
    
    for project_name, narrative in narratives.items():
        print(f"Project: {project_name}")
        print(f"Narrative length: {len(narrative)} characters")
        print(f"Preview: {narrative[:150]}...")
        print("-" * 80)
        print()
    
    # Display statistics
    print("Statistics:")
    print(f"  Total projects: {len(qualified_projects)}")
    print(f"  Narratives generated: {len(narratives)}")
    print(f"  Success rate: {len(narratives)/len(qualified_projects)*100:.1f}%")
    print(f"  Total API calls: {len(narratives)}")
    print()
    
    # Example: Using batch generation in the full run() method
    print("=" * 80)
    print("Full Audit Trail Agent Run Example")
    print("=" * 80)
    print()
    
    print("Running full audit trail generation workflow...")
    result = agent.run(
        qualified_projects=qualified_projects,
        tax_year=2024,
        company_name="Example Corp"
    )
    
    print()
    print("Workflow complete!")
    print(f"Execution time: {result.execution_time_seconds:.2f} seconds")
    print(f"Narratives generated: {len(result.narratives)}")
    print()
    print("Summary:")
    print(result.summary)


if __name__ == "__main__":
    # Run the async example
    asyncio.run(main())
