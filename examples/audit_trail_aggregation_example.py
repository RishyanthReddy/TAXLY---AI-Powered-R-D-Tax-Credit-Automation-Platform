"""
Example demonstrating the data aggregation functionality in Audit Trail Agent.

This example shows how the _aggregate_report_data method processes qualified
projects and generates comprehensive summary statistics for PDF report generation.

Requirements: 3.3, 4.4
"""

from datetime import datetime
from agents.audit_trail_agent import AuditTrailAgent
from models.tax_models import QualifiedProject
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner


def main():
    """Demonstrate data aggregation functionality"""
    
    print("=" * 80)
    print("Audit Trail Agent - Data Aggregation Example")
    print("=" * 80)
    print()
    
    # Create mock clients (in real usage, these would be properly initialized)
    # For this example, we'll use None since we're only testing aggregation
    from unittest.mock import Mock
    youcom_client = Mock(spec=YouComClient)
    glm_reasoner = Mock(spec=GLMReasoner)
    
    # Initialize agent
    agent = AuditTrailAgent(
        youcom_client=youcom_client,
        glm_reasoner=glm_reasoner
    )
    
    print("✓ Initialized Audit Trail Agent")
    print()
    
    # Create sample qualified projects with varying characteristics
    qualified_projects = [
        QualifiedProject(
            project_name="API Performance Optimization",
            qualified_hours=120.5,
            qualified_cost=15000.00,
            confidence_score=0.92,
            qualification_percentage=85.0,
            supporting_citation=(
                "The project involved developing novel algorithms to reduce API "
                "response times by 60%, which required extensive experimentation "
                "with caching strategies and database query optimization."
            ),
            reasoning=(
                "This project clearly meets the four-part test for qualified research. "
                "Technical uncertainty existed regarding the optimal caching strategy "
                "for our specific use case. The team conducted systematic experiments "
                "comparing Redis, Memcached, and custom in-memory solutions."
            ),
            irs_source="CFR Title 26 § 1.41-4(a)(1) - Four-Part Test for Qualified Research"
        ),
        QualifiedProject(
            project_name="Machine Learning Model Development",
            qualified_hours=200.0,
            qualified_cost=25000.00,
            confidence_score=0.88,
            qualification_percentage=90.0,
            supporting_citation=(
                "Development of a custom neural network architecture for fraud detection "
                "that achieved 95% accuracy, significantly exceeding industry standards."
            ),
            reasoning=(
                "The project involved substantial experimentation with different neural "
                "network architectures, activation functions, and training strategies. "
                "Technical uncertainty existed regarding the optimal model architecture."
            ),
            irs_source="CFR Title 26 § 1.41-4(a)(3) - Substantially All Requirement"
        ),
        QualifiedProject(
            project_name="Database Migration Tool",
            qualified_hours=80.0,
            qualified_cost=10000.00,
            confidence_score=0.75,
            qualification_percentage=70.0,
            supporting_citation=(
                "Created an automated tool for migrating legacy database schemas "
                "while preserving data integrity and minimizing downtime."
            ),
            reasoning=(
                "The project required developing novel algorithms for schema mapping "
                "and data transformation. Some uncertainty exists regarding the "
                "qualification percentage due to routine migration tasks."
            ),
            irs_source="Form 6765 Instructions - Software Development Activities"
        ),
        QualifiedProject(
            project_name="Security Enhancement Framework",
            qualified_hours=150.0,
            qualified_cost=18000.00,
            confidence_score=0.95,
            qualification_percentage=95.0,
            supporting_citation=(
                "Developed a comprehensive security framework implementing zero-trust "
                "architecture with novel authentication mechanisms."
            ),
            reasoning=(
                "This project involved significant R&D in cryptographic protocols and "
                "authentication mechanisms. The team experimented with multiple approaches "
                "to achieve both security and performance requirements."
            ),
            irs_source="CFR Title 26 § 1.41-4(a)(2) - Process of Experimentation"
        ),
        QualifiedProject(
            project_name="Real-time Analytics Engine",
            qualified_hours=100.0,
            qualified_cost=12000.00,
            confidence_score=0.68,
            qualification_percentage=65.0,
            supporting_citation=(
                "Built a real-time analytics engine capable of processing 1M events/second "
                "with sub-second latency."
            ),
            reasoning=(
                "The project involved experimentation with stream processing architectures. "
                "However, some components used standard industry practices, resulting in "
                "lower qualification percentage."
            ),
            irs_source="Publication 542 - Software Development",
            flagged_for_review=True  # Low confidence, flagged for manual review
        )
    ]
    
    print(f"Created {len(qualified_projects)} sample qualified projects")
    print()
    
    # Aggregate the data
    print("Aggregating project data...")
    print()
    
    aggregated_data = agent._aggregate_report_data(
        qualified_projects=qualified_projects,
        tax_year=2024
    )
    
    # Display aggregation results
    print("=" * 80)
    print("AGGREGATION RESULTS")
    print("=" * 80)
    print()
    
    print("📊 CORE TOTALS")
    print("-" * 80)
    print(f"  Total Qualified Hours:    {aggregated_data['total_qualified_hours']:>12,.2f}")
    print(f"  Total Qualified Cost:     ${aggregated_data['total_qualified_cost']:>12,.2f}")
    print(f"  Estimated Credit (20%):   ${aggregated_data['estimated_credit']:>12,.2f}")
    print()
    
    print("🎯 CONFIDENCE METRICS")
    print("-" * 80)
    print(f"  Average Confidence:       {aggregated_data['average_confidence']:>12.2%}")
    print(f"  High Confidence (≥0.8):   {aggregated_data['high_confidence_count']:>12} projects")
    print(f"  Medium Confidence (0.7-0.8): {aggregated_data['medium_confidence_count']:>9} projects")
    print(f"  Low Confidence (<0.7):    {aggregated_data['low_confidence_count']:>12} projects")
    print()
    
    print("📋 PROJECT COUNTS")
    print("-" * 80)
    print(f"  Total Projects:           {aggregated_data['project_count']:>12}")
    print(f"  Flagged for Review:       {aggregated_data['flagged_count']:>12}")
    print(f"  Top Projects (80% cost):  {aggregated_data['top_projects_80_count']:>12}")
    print()
    
    print("📈 SUMMARY STATISTICS")
    print("-" * 80)
    stats = aggregated_data['summary_stats']
    print(f"  Confidence Range:         {stats['min_confidence']:.2%} - {stats['max_confidence']:.2%}")
    print(f"  Median Confidence:        {stats['median_confidence']:>12.2%}")
    print(f"  Hours Range:              {stats['min_qualified_hours']:,.2f} - {stats['max_qualified_hours']:,.2f}")
    print(f"  Cost Range:               ${stats['min_qualified_cost']:,.2f} - ${stats['max_qualified_cost']:,.2f}")
    print(f"  Avg Qualification %:      {stats['avg_qualification_percentage']:>12.1f}%")
    print()
    
    print("🏆 TOP PROJECTS BY COST")
    print("-" * 80)
    projects_df = aggregated_data['projects_df']
    for idx, row in projects_df.head(3).iterrows():
        print(f"  {idx + 1}. {row['project_name']}")
        print(f"     Cost: ${row['qualified_cost']:,.2f} | "
              f"Hours: {row['qualified_hours']:.1f} | "
              f"Confidence: {row['confidence_score']:.2%}")
        print(f"     Cumulative: {row['cumulative_percentage']:.1f}% of total cost")
        print()
    
    print("=" * 80)
    print("✓ Data aggregation complete!")
    print()
    print("This aggregated data is now ready for PDF report generation (Task 121)")
    print("=" * 80)


if __name__ == "__main__":
    main()
