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
    
    print()
    print("Step 2: Initialize Audit Trail Agent")
    print("-" * 80)
    
    # Initialize agent with status callback
    agent = AuditTrailAgent(
        youcom_client=youcom_client,
        glm_reasoner=glm_reasoner,
        pdf_generator=None,  # Will be implemented in task 118
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
    
    # Demonstrate agent run (placeholder - full implementation in tasks 114-121)
    print("Step 5: Run audit trail generation (placeholder)")
    print("-" * 80)
    print("Note: Full implementation will be completed in tasks 114-121")
    print("      - Task 114: Narrative generation with You.com Agent API")
    print("      - Task 116: Compliance review with You.com Express Agent")
    print("      - Task 117: Data aggregation with Pandas")
    print("      - Task 118-121: PDF generation with ReportLab")
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
        print(f"  - Summary: {result.summary}")
        print(f"  - Narratives generated: {len(result.narratives)}")
        print(f"  - PDF path: {result.pdf_path or 'Not generated (pending task 118)'}")
        
    except Exception as e:
        print(f"✗ Error during agent run: {e}")
    
    print()
    print("=" * 80)
    print("Example complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
