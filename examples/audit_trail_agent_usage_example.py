"""
Example usage of the Audit Trail Agent.

This script demonstrates how to initialize and use the AuditTrailAgent
for generating audit-ready documentation and PDF reports.

Requirements: 4.1, 8.1
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.audit_trail_agent import AuditTrailAgent, AuditTrailState, AuditTrailResult
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.pdf_generator import PDFGenerator
from models.tax_models import QualifiedProject
from models.websocket_models import StatusUpdateMessage
from datetime import datetime
from utils.config import get_config


def status_callback(message: StatusUpdateMessage):
    """
    Callback function for receiving status updates from the agent.
    
    Args:
        message: StatusUpdateMessage with current agent status
    """
    print(f"[{message.timestamp.strftime('%H:%M:%S')}] {message.stage.value}: {message.details}")


def main():
    """
    Demonstrate Audit Trail Agent initialization and basic usage.
    """
    print("=" * 80)
    print("Audit Trail Agent Usage Example")
    print("=" * 80)
    print()
    
    # Load configuration
    config = get_config()
    
    print("Step 1: Initialize required tools")
    print("-" * 80)
    
    # Initialize You.com client
    print("Initializing You.com client...")
    youcom_client = YouComClient(api_key=config.youcom_api_key)
    print("✓ You.com client initialized")
    
    # Initialize GLM reasoner
    print("Initializing GLM reasoner (GLM 4.5 Air via OpenRouter)...")
    glm_reasoner = GLMReasoner(api_key=config.openrouter_api_key)
    print("✓ GLM reasoner initialized")
    
    # Initialize PDF generator
    print("Initializing PDF generator...")
    pdf_generator = PDFGenerator()
    print("✓ PDF generator initialized")
    
    print()
    print("Step 2: Initialize Audit Trail Agent")
    print("-" * 80)
    
    # Initialize agent with status callback and PDF generator
    agent = AuditTrailAgent(
        youcom_client=youcom_client,
        glm_reasoner=glm_reasoner,
        pdf_generator=pdf_generator,
        status_callback=status_callback
    )
    
    print("✓ Audit Trail Agent initialized successfully")
    print()
    
    # Display agent state
    print("Step 3: Check initial agent state")
    print("-" * 80)
    print(f"Stage: {agent.state.stage}")
    print(f"Status: {agent.state.status.value}")
    print(f"Projects to process: {agent.state.projects_to_process}")
    print(f"Narratives generated: {agent.state.narratives_generated}")
    print(f"Report generated: {agent.state.report_generated}")
    print()
    
    # Create sample qualified projects for demonstration
    print("Step 4: Create sample qualified projects")
    print("-" * 80)
    
    sample_projects = [
        QualifiedProject(
            project_name="API Optimization",
            qualified_hours=120.5,
            qualified_cost=15000.00,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="CFR Title 26 § 1.41-4(a)(1)",
            reasoning="Project involves systematic experimentation to resolve technical uncertainty in API performance",
            irs_source="CFR Title 26 § 1.41-4",
            technical_details={
                "technological_uncertainty": "Uncertainty existed regarding optimal caching strategies for high-throughput APIs",
                "experimentation_process": "Team evaluated multiple caching algorithms and data structures",
                "business_component": "API Performance Optimization System"
            }
        ),
        QualifiedProject(
            project_name="Machine Learning Model",
            qualified_hours=200.0,
            qualified_cost=25000.00,
            confidence_score=0.92,
            qualification_percentage=90.0,
            supporting_citation="CFR Title 26 § 1.41-4(a)(2)",
            reasoning="Project involves development of new ML algorithms for predictive analytics",
            irs_source="CFR Title 26 § 1.41-4",
            technical_details={
                "technological_uncertainty": "Uncertainty existed regarding neural network architecture for time series data",
                "experimentation_process": "Developed and tested custom LSTM variants with attention mechanisms",
                "business_component": "Predictive Analytics Engine"
            }
        )
    ]
    
    print(f"Created {len(sample_projects)} sample qualified projects")
    for project in sample_projects:
        print(f"  - {project.project_name}: {project.qualified_hours}h, ${project.qualified_cost:,.2f}")
    print()
    
    # Run the complete audit trail generation workflow
    print("Step 5: Run audit trail generation workflow")
    print("-" * 80)
    print("This will:")
    print("  1. Generate narratives for all projects using You.com Agent API")
    print("  2. Review narratives for compliance using You.com Express Agent")
    print("  3. Aggregate all data using Pandas")
    print("  4. Generate PDF report using ReportLab")
    print()
    
    try:
        result = agent.run(
            qualified_projects=sample_projects,
            tax_year=2024,
            company_name="Example Corp"
        )
        
        print("✓ Agent run completed successfully")
        print()
        print("Result Summary:")
        print(f"  - Execution time: {result.execution_time_seconds:.2f}s")
        print(f"  - Narratives generated: {len(result.narratives)}")
        print(f"  - Compliance reviews: {len(result.compliance_reviews)}")
        print(f"  - PDF path: {result.pdf_path or 'Not generated'}")
        print()
        print(f"Summary: {result.summary}")
        print()
        
        # Display aggregated data
        if result.aggregated_data:
            print("Aggregated Data:")
            print(f"  - Total qualified hours: {result.aggregated_data['total_qualified_hours']:.2f}")
            print(f"  - Total qualified cost: ${result.aggregated_data['total_qualified_cost']:,.2f}")
            print(f"  - Estimated credit: ${result.aggregated_data['estimated_credit']:,.2f}")
            print(f"  - Average confidence: {result.aggregated_data['average_confidence']:.2%}")
            print(f"  - Projects flagged: {result.aggregated_data['flagged_count']}")
        
        # Display narrative samples
        if result.narratives:
            print()
            print("Narrative Samples:")
            for project_name, narrative in list(result.narratives.items())[:2]:
                preview = narrative[:150] + "..." if len(narrative) > 150 else narrative
                print(f"  - {project_name}: {preview}")
        
        # Display compliance review results
        if result.compliance_reviews:
            print()
            print("Compliance Review Results:")
            for project_name, review in result.compliance_reviews.items():
                status = review.get('compliance_status', 'Unknown')
                score = review.get('completeness_score', 0)
                flagged = review.get('flagged_for_review', False)
                flag_indicator = " [FLAGGED]" if flagged else ""
                print(f"  - {project_name}: {status} ({score}%){flag_indicator}")
        
    except Exception as e:
        print(f"✗ Error during agent run: {e}")
    
    print()
    print("=" * 80)
    print("Example complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
