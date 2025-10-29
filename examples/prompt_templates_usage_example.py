"""
Prompt Templates Usage Examples

This script demonstrates how to use the prompt templates module for various
LLM interactions in the R&D Tax Credit Automation system.

Run this script to see example outputs for each prompt template.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.prompt_templates import (
    populate_rag_inference_prompt,
    populate_agent_decision_prompt,
    populate_thesys_data_ingestion_prompt,
    populate_thesys_qualification_dashboard_prompt,
    populate_thesys_report_confirmation_prompt,
    populate_narrative_generation_prompt,
    populate_compliance_review_prompt,
    create_batch_rag_prompts,
    create_batch_narrative_prompts
)


def example_rag_inference_prompt():
    """Example: RAG inference prompt for project qualification"""
    print("=" * 80)
    print("EXAMPLE 1: RAG Inference Prompt")
    print("=" * 80)
    
    # Sample RAG context (would come from RD_Knowledge_Tool)
    rag_context = """
    Source: CFR Title 26 § 1.41-4(a)(1)
    Page: 3
    
    Qualified research must meet the following four-part test:
    1. The research must be technological in nature
    2. The research must be undertaken to eliminate uncertainty
    3. The research must involve a process of experimentation
    4. The research must be undertaken for a qualified purpose
    
    ---
    
    Source: Form 6765 Instructions
    Page: 5
    
    Technological in nature means the process of experimentation must
    fundamentally rely on principles of physical or biological sciences,
    engineering, or computer science.
    """
    
    prompt = populate_rag_inference_prompt(
        rag_context=rag_context,
        project_name="API Performance Optimization",
        project_description="Improve API response times through algorithm optimization and caching strategies",
        technical_activities="""
        - Analyzed existing algorithm complexity (O(n²) to O(n log n))
        - Evaluated multiple caching strategies (LRU, LFU, ARC)
        - Conducted performance benchmarking with various data sizes
        - Implemented and tested prototype solutions
        """,
        total_hours=120.5,
        total_cost=15000.00
    )
    
    print(prompt)
    print("\n")


def example_agent_decision_prompt():
    """Example: Agent decision prompt for workflow decisions"""
    print("=" * 80)
    print("EXAMPLE 2: Agent Decision Prompt")
    print("=" * 80)
    
    prompt = populate_agent_decision_prompt(
        stage_name="Qualification",
        agent_state={
            "projects_analyzed": 10,
            "projects_qualified": 8,
            "low_confidence_count": 2,
            "total_qualified_hours": 850.0,
            "total_qualified_cost": 106250.00,
            "average_confidence": 0.82
        },
        available_actions=[
            "proceed_to_report_generation",
            "flag_low_confidence_projects_for_review",
            "request_additional_documentation",
            "abort_workflow"
        ],
        context_information="""
        Two projects have confidence scores below 0.7:
        - "Mobile App Refactoring" (confidence: 0.65)
        - "Database Migration" (confidence: 0.68)
        
        These projects represent $18,000 in potential qualified costs.
        """,
        decision_question="Should we proceed to report generation or flag these projects for manual review?"
    )
    
    print(prompt)
    print("\n")


def example_thesys_data_ingestion_prompt():
    """Example: Thesys C1 UI generation for data ingestion"""
    print("=" * 80)
    print("EXAMPLE 3: Thesys Data Ingestion UI Prompt")
    print("=" * 80)
    
    sample_data = [
        {
            "employee_name": "John Doe",
            "project_name": "API Optimization",
            "task_description": "Implemented caching layer for frequently accessed data",
            "hours_spent": 8.5,
            "date": "2024-01-15",
            "is_rd_classified": True
        },
        {
            "employee_name": "Jane Smith",
            "project_name": "Mobile App Development",
            "task_description": "Designed new user interface components",
            "hours_spent": 6.0,
            "date": "2024-01-15",
            "is_rd_classified": False
        },
        {
            "employee_name": "John Doe",
            "project_name": "API Optimization",
            "task_description": "Performance testing and benchmarking",
            "hours_spent": 4.5,
            "date": "2024-01-16",
            "is_rd_classified": True
        }
    ]
    
    prompt = populate_thesys_data_ingestion_prompt(
        data=sample_data,
        total_hours=19.0,
        classified_hours=13.0,
        project_count=2
    )
    
    print(prompt[:1000] + "...\n[Truncated for brevity]\n")


def example_thesys_qualification_dashboard_prompt():
    """Example: Thesys C1 UI generation for qualification dashboard"""
    print("=" * 80)
    print("EXAMPLE 4: Thesys Qualification Dashboard Prompt")
    print("=" * 80)
    
    qualified_projects = [
        {
            "project_name": "API Optimization",
            "qualified_hours": 102.0,
            "qualified_cost": 12750.00,
            "confidence_score": 0.88,
            "qualification_percentage": 85.0,
            "supporting_citation": "CFR Title 26 § 1.41-4(a)(1)",
            "reasoning": "Project meets all four-part test criteria with clear technical uncertainties...",
            "flagged_for_review": False
        },
        {
            "project_name": "Machine Learning Model",
            "qualified_hours": 156.0,
            "qualified_cost": 19500.00,
            "confidence_score": 0.92,
            "qualification_percentage": 90.0,
            "supporting_citation": "Form 6765 Instructions, Software Audit Guidelines",
            "reasoning": "Strong evidence of process of experimentation and technological uncertainty...",
            "flagged_for_review": False
        },
        {
            "project_name": "Database Migration",
            "qualified_hours": 45.0,
            "qualified_cost": 5625.00,
            "confidence_score": 0.68,
            "qualification_percentage": 60.0,
            "supporting_citation": "CFR Title 26 § 1.41-4",
            "reasoning": "Some uncertainty about qualification due to routine engineering aspects...",
            "flagged_for_review": True
        }
    ]
    
    prompt = populate_thesys_qualification_dashboard_prompt(
        qualified_projects=qualified_projects,
        total_qualified_hours=303.0,
        total_qualified_cost=37875.00,
        estimated_credit=7575.00,
        average_confidence=0.83
    )
    
    print(prompt[:1000] + "...\n[Truncated for brevity]\n")


def example_thesys_report_confirmation_prompt():
    """Example: Thesys C1 UI generation for report confirmation"""
    print("=" * 80)
    print("EXAMPLE 5: Thesys Report Confirmation Prompt")
    print("=" * 80)
    
    report_metadata = {
        "report_id": "RPT-2024-001",
        "generation_date": "2024-01-20T14:30:00",
        "tax_year": 2024,
        "file_size_mb": 2.5,
        "page_count": 45,
        "low_confidence_projects": 1
    }
    
    prompt = populate_thesys_report_confirmation_prompt(
        report_metadata=report_metadata,
        tax_year=2024,
        generation_date="January 20, 2024",
        total_qualified_cost=37875.00,
        estimated_credit=7575.00,
        project_count=3,
        report_id="RPT-2024-001"
    )
    
    print(prompt[:1000] + "...\n[Truncated for brevity]\n")


def example_narrative_generation_prompt():
    """Example: Narrative generation for audit report"""
    print("=" * 80)
    print("EXAMPLE 6: Narrative Generation Prompt")
    print("=" * 80)
    
    prompt = populate_narrative_generation_prompt(
        project_name="Machine Learning Model Optimization",
        qualification_percentage=90.0,
        qualified_hours=156.0,
        qualified_cost=19500.00,
        confidence_score=0.92,
        qualification_reasoning="""
        This project clearly meets all four parts of the qualified research test:
        
        1. Technological in Nature: The project relied on computer science principles,
           specifically machine learning algorithms and optimization techniques.
        
        2. Elimination of Uncertainty: There was genuine uncertainty about which
           model architecture and hyperparameters would achieve the required accuracy.
        
        3. Process of Experimentation: The team systematically evaluated multiple
           model architectures, conducted A/B testing, and iteratively refined
           the approach based on results.
        
        4. Qualified Purpose: The purpose was to create an improved business
           component (prediction model) with better accuracy and performance.
        """,
        irs_citations=[
            "CFR Title 26 § 1.41-4(a)(1)",
            "Form 6765 Instructions",
            "Software Development Audit Guidelines"
        ]
    )
    
    print(prompt)
    print("\n")


def example_compliance_review_prompt():
    """Example: Compliance review for generated narrative"""
    print("=" * 80)
    print("EXAMPLE 7: Compliance Review Prompt")
    print("=" * 80)
    
    sample_narrative = """
    Project Overview:
    The Machine Learning Model Optimization project was undertaken to develop
    a more accurate prediction model for customer behavior analysis. The project
    ran from January to March 2024.
    
    Technical Uncertainties:
    At the project's outset, it was uncertain which neural network architecture
    would provide the best balance of accuracy and inference speed. Existing
    models either lacked sufficient accuracy (< 85%) or were too slow for
    real-time predictions (> 500ms latency).
    
    Process of Experimentation:
    The team systematically evaluated five different architectures:
    1. Convolutional Neural Networks (CNN)
    2. Recurrent Neural Networks (RNN)
    3. Transformer-based models
    4. Ensemble methods
    5. Hybrid architectures
    
    Each architecture was tested with multiple hyperparameter configurations,
    and results were analyzed to determine optimal approaches.
    
    Technological Nature:
    The project fundamentally relied on computer science principles, specifically
    machine learning theory, optimization algorithms, and statistical analysis.
    
    Qualified Purpose:
    The purpose was to create an improved business component - a prediction
    model with 90%+ accuracy and < 200ms latency, representing a significant
    improvement over existing solutions.
    
    Outcomes:
    The project successfully developed a hybrid architecture achieving 92%
    accuracy with 150ms average latency, resolving the initial uncertainties.
    """
    
    prompt = populate_compliance_review_prompt(
        narrative_text=sample_narrative
    )
    
    print(prompt)
    print("\n")


def example_batch_processing():
    """Example: Batch processing for multiple projects"""
    print("=" * 80)
    print("EXAMPLE 8: Batch Processing")
    print("=" * 80)
    
    # Batch RAG prompts
    projects = [
        {
            "name": "Project A",
            "description": "API optimization",
            "technical_activities": "Algorithm analysis, caching",
            "total_hours": 100,
            "total_cost": 12000
        },
        {
            "name": "Project B",
            "description": "ML model development",
            "technical_activities": "Model training, evaluation",
            "total_hours": 150,
            "total_cost": 18000
        }
    ]
    
    rag_contexts = [
        "Context for Project A...",
        "Context for Project B..."
    ]
    
    rag_prompts = create_batch_rag_prompts(projects, rag_contexts)
    print(f"Created {len(rag_prompts)} RAG inference prompts for batch processing")
    
    # Batch narrative prompts
    qualified_projects = [
        {
            "project_name": "Project A",
            "qualification_percentage": 85.0,
            "qualified_hours": 85.0,
            "qualified_cost": 10200.00,
            "confidence_score": 0.88,
            "reasoning": "Meets all criteria...",
            "citations": ["CFR Title 26 § 1.41-4"]
        },
        {
            "project_name": "Project B",
            "qualification_percentage": 90.0,
            "qualified_hours": 135.0,
            "qualified_cost": 16200.00,
            "confidence_score": 0.92,
            "reasoning": "Strong qualification...",
            "citations": ["Form 6765"]
        }
    ]
    
    narrative_prompts = create_batch_narrative_prompts(qualified_projects)
    print(f"Created {len(narrative_prompts)} narrative generation prompts for batch processing")
    print("\n")


async def example_with_glm_reasoner():
    """Example: Using prompts with GLMReasoner (requires API key)"""
    print("=" * 80)
    print("EXAMPLE 9: Integration with GLMReasoner")
    print("=" * 80)
    
    try:
        from tools.glm_reasoner import GLMReasoner
        
        # Create a simple prompt
        prompt = populate_agent_decision_prompt(
            stage_name="Test",
            agent_state={"test": True},
            available_actions=["action1", "action2"],
            context_information="This is a test",
            decision_question="What should we do?"
        )
        
        print("Prompt created successfully")
        print("To use with GLMReasoner:")
        print("""
        reasoner = GLMReasoner()
        response = await reasoner.reason(prompt)
        result = reasoner.parse_structured_response(response)
        """)
        
    except Exception as e:
        print(f"Note: GLMReasoner requires OPENROUTER_API_KEY to be set")
        print(f"Error: {e}")
    
    print("\n")


def main():
    """Run all examples"""
    print("\n")
    print("=" * 80)
    print("PROMPT TEMPLATES USAGE EXAMPLES")
    print("=" * 80)
    print("\n")
    
    # Run synchronous examples
    example_rag_inference_prompt()
    example_agent_decision_prompt()
    example_thesys_data_ingestion_prompt()
    example_thesys_qualification_dashboard_prompt()
    example_thesys_report_confirmation_prompt()
    example_narrative_generation_prompt()
    example_compliance_review_prompt()
    example_batch_processing()
    
    # Run async example
    asyncio.run(example_with_glm_reasoner())
    
    print("=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
