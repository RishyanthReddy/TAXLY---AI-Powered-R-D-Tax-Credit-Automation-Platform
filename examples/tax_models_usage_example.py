"""
Usage examples for tax-related data models.

This script demonstrates how to use the QualifiedProject model for R&D tax credit
qualification results, including validation, auto-flagging, and computed fields.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.tax_models import QualifiedProject
import json


def example_basic_qualified_project():
    """Example: Create a basic qualified project."""
    print("=" * 80)
    print("Example 1: Basic Qualified Project")
    print("=" * 80)
    
    project = QualifiedProject(
        project_name="Alpha Development",
        qualified_hours=14.5,
        qualified_cost=1045.74,
        confidence_score=0.92,
        qualification_percentage=95.0,
        supporting_citation="The project involves developing a new authentication algorithm with encryption, which constitutes qualified research under IRC Section 41.",
        reasoning="This project clearly meets the four-part test: (1) Technological in nature - involves computer science and cryptography; (2) Qualified purpose - developing new functionality; (3) Technological uncertainty - uncertainty about optimal encryption approach; (4) Process of experimentation - systematic evaluation of different authentication methods.",
        irs_source="CFR Title 26 § 1.41-4(a)(1) - Four-Part Test for Qualified Research"
    )
    
    print(f"Project Name: {project.project_name}")
    print(f"Qualified Hours: {project.qualified_hours}")
    print(f"Qualified Cost: ${project.qualified_cost:.2f}")
    print(f"Confidence Score: {project.confidence_score}")
    print(f"Qualification Percentage: {project.qualification_percentage}%")
    print(f"Estimated Credit: ${project.estimated_credit}")
    print(f"Flagged for Review: {project.flagged_for_review}")
    print(f"\nString representation: {project}")
    print()


def example_auto_flagging_low_confidence():
    """Example: Auto-flagging for low confidence projects."""
    print("=" * 80)
    print("Example 2: Auto-Flagging for Low Confidence")
    print("=" * 80)
    
    # Project with low confidence (< 0.7) is automatically flagged
    low_confidence_project = QualifiedProject(
        project_name="Uncertain Project",
        qualified_hours=5.0,
        qualified_cost=500.0,
        confidence_score=0.65,
        qualification_percentage=70.0,
        supporting_citation="Limited evidence of qualified research activities.",
        reasoning="Some aspects meet the four-part test, but documentation is incomplete.",
        irs_source="CFR Title 26 § 1.41-4"
    )
    
    print(f"Project: {low_confidence_project.project_name}")
    print(f"Confidence Score: {low_confidence_project.confidence_score}")
    print(f"Flagged for Review: {low_confidence_project.flagged_for_review}")
    print(f"  -> Automatically flagged because confidence < 0.7")
    print()
    
    # Project with high confidence is not flagged
    high_confidence_project = QualifiedProject(
        project_name="Strong Project",
        qualified_hours=15.0,
        qualified_cost=1500.0,
        confidence_score=0.95,
        qualification_percentage=98.0,
        supporting_citation="Comprehensive evidence of qualified research.",
        reasoning="Clearly meets all aspects of the four-part test with strong documentation.",
        irs_source="CFR Title 26 § 1.41-4(a)(1)"
    )
    
    print(f"Project: {high_confidence_project.project_name}")
    print(f"Confidence Score: {high_confidence_project.confidence_score}")
    print(f"Flagged for Review: {high_confidence_project.flagged_for_review}")
    print(f"  -> Not flagged because confidence >= 0.7")
    print()


def example_estimated_credit_calculation():
    """Example: Estimated credit calculation."""
    print("=" * 80)
    print("Example 3: Estimated Credit Calculation")
    print("=" * 80)
    
    projects = [
        QualifiedProject(
            project_name="Small Project",
            qualified_hours=5.0,
            qualified_cost=500.0,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test",
            reasoning="Test",
            irs_source="Test"
        ),
        QualifiedProject(
            project_name="Medium Project",
            qualified_hours=20.0,
            qualified_cost=2500.0,
            confidence_score=0.90,
            qualification_percentage=90.0,
            supporting_citation="Test",
            reasoning="Test",
            irs_source="Test"
        ),
        QualifiedProject(
            project_name="Large Project",
            qualified_hours=50.0,
            qualified_cost=10000.0,
            confidence_score=0.95,
            qualification_percentage=95.0,
            supporting_citation="Test",
            reasoning="Test",
            irs_source="Test"
        )
    ]
    
    total_cost = sum(p.qualified_cost for p in projects)
    total_credit = sum(p.estimated_credit for p in projects)
    
    print("Project Summary:")
    print("-" * 80)
    for project in projects:
        print(f"{project.project_name:20} | Cost: ${project.qualified_cost:10,.2f} | Credit: ${project.estimated_credit:8,.2f}")
    
    print("-" * 80)
    print(f"{'TOTAL':20} | Cost: ${total_cost:10,.2f} | Credit: ${total_credit:8,.2f}")
    print(f"\nNote: Estimated credit is 20% of qualified research expenditures (QREs)")
    print()


def example_technical_details():
    """Example: Using technical_details for additional information."""
    print("=" * 80)
    print("Example 4: Technical Details")
    print("=" * 80)
    
    project = QualifiedProject(
        project_name="Delta Security",
        qualified_hours=15.0,
        qualified_cost=1370.25,
        confidence_score=0.94,
        qualification_percentage=98.0,
        supporting_citation="Research into quantum-resistant cryptography and development of new encryption protocols constitutes highly qualified research.",
        reasoning="Strongly meets four-part test with advanced cryptography research.",
        irs_source="CFR Title 26 § 1.41-4(a)(1) - Qualified Research Definition",
        technical_details={
            "technological_uncertainty": "Significant uncertainty regarding which post-quantum cryptographic algorithms would provide adequate security while maintaining acceptable performance for production systems.",
            "experimentation_process": "Systematic research and prototyping of NIST post-quantum cryptography candidates (CRYSTALS-Kyber, CRYSTALS-Dilithium, SPHINCS+) with performance benchmarking and security analysis.",
            "business_component": "Quantum-Resistant Security Layer",
            "qualified_activities": [
                "Post-quantum cryptography research",
                "Algorithm implementation and testing",
                "Performance optimization",
                "Security vulnerability assessment",
                "Protocol design and validation"
            ]
        }
    )
    
    print(f"Project: {project.project_name}")
    print(f"Qualified Cost: ${project.qualified_cost:.2f}")
    print(f"Estimated Credit: ${project.estimated_credit}")
    print(f"\nTechnical Details:")
    print(f"  Technological Uncertainty: {project.technical_details['technological_uncertainty'][:100]}...")
    print(f"  Business Component: {project.technical_details['business_component']}")
    print(f"  Qualified Activities:")
    for activity in project.technical_details['qualified_activities']:
        print(f"    - {activity}")
    print()


def example_json_serialization():
    """Example: JSON serialization and deserialization."""
    print("=" * 80)
    print("Example 5: JSON Serialization")
    print("=" * 80)
    
    # Create a project
    original_project = QualifiedProject(
        project_name="Epsilon AI",
        qualified_hours=16.5,
        qualified_cost=1586.48,
        confidence_score=0.91,
        qualification_percentage=93.0,
        supporting_citation="Development of custom neural network architectures represents qualified research.",
        reasoning="Meets four-part test with machine learning and AI research.",
        irs_source="CFR Title 26 § 1.41-4(a)(4) - Process of Experimentation"
    )
    
    # Serialize to JSON
    json_str = original_project.model_dump_json(indent=2)
    print("Serialized to JSON:")
    print(json_str[:300] + "...")
    print()
    
    # Deserialize from JSON
    json_data = json.loads(json_str)
    restored_project = QualifiedProject(**json_data)
    
    print("Deserialized from JSON:")
    print(f"  Project Name: {restored_project.project_name}")
    print(f"  Qualified Cost: ${restored_project.qualified_cost:.2f}")
    print(f"  Estimated Credit: ${restored_project.estimated_credit}")
    print(f"  Confidence: {restored_project.confidence_score}")
    print()


def example_validation_errors():
    """Example: Validation error handling."""
    print("=" * 80)
    print("Example 6: Validation Errors")
    print("=" * 80)
    
    # Try to create project with invalid confidence score
    try:
        invalid_project = QualifiedProject(
            project_name="Invalid Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=1.5,  # Invalid: > 1.0
            qualification_percentage=80.0,
            supporting_citation="Test",
            reasoning="Test",
            irs_source="Test"
        )
    except Exception as e:
        print(f"Validation Error (confidence_score > 1.0):")
        print(f"  {str(e)[:150]}...")
        print()
    
    # Try to create project with invalid qualification percentage
    try:
        invalid_project = QualifiedProject(
            project_name="Invalid Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.85,
            qualification_percentage=105.0,  # Invalid: > 100
            supporting_citation="Test",
            reasoning="Test",
            irs_source="Test"
        )
    except Exception as e:
        print(f"Validation Error (qualification_percentage > 100):")
        print(f"  {str(e)[:150]}...")
        print()


def example_loading_from_fixture():
    """Example: Load projects from Phase 1 fixture."""
    print("=" * 80)
    print("Example 7: Loading from Fixture")
    print("=" * 80)
    
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_qualified_projects.json"
    
    with open(fixture_path, 'r') as f:
        projects_data = json.load(f)
    
    projects = [QualifiedProject(**p) for p in projects_data]
    
    print(f"Loaded {len(projects)} projects from fixture")
    print("\nProject Summary:")
    print("-" * 80)
    
    total_hours = 0
    total_cost = 0
    total_credit = 0
    flagged_count = 0
    
    for project in projects:
        flag_indicator = " [FLAGGED]" if project.flagged_for_review else ""
        print(f"{project.project_name:25} | {project.qualified_hours:5.1f} hrs | ${project.qualified_cost:8,.2f} | Credit: ${project.estimated_credit:7,.2f} | Conf: {project.confidence_score:.2f}{flag_indicator}")
        
        total_hours += project.qualified_hours
        total_cost += project.qualified_cost
        total_credit += project.estimated_credit
        if project.flagged_for_review:
            flagged_count += 1
    
    print("-" * 80)
    print(f"{'TOTALS':25} | {total_hours:5.1f} hrs | ${total_cost:8,.2f} | Credit: ${total_credit:7,.2f}")
    print(f"\nProjects flagged for review: {flagged_count}/{len(projects)}")
    print()


if __name__ == "__main__":
    example_basic_qualified_project()
    example_auto_flagging_low_confidence()
    example_estimated_credit_calculation()
    example_technical_details()
    example_json_serialization()
    example_validation_errors()
    example_loading_from_fixture()
    
    print("=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)
