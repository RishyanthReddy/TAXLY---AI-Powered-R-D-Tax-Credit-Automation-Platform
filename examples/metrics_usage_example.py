"""
Example usage of the performance monitoring and metrics tracking utilities.

This script demonstrates how to use the metrics module to track performance
of functions, agents, and code blocks in the R&D Tax Credit Automation Agent.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.metrics import (
    timing_decorator,
    track_execution_time,
    MemoryTracker,
    AgentMetrics,
    get_metrics_collector,
    log_performance_summary
)
from utils.logger import AgentLogger


# Initialize logging
AgentLogger.initialize(log_level="INFO")
logger = AgentLogger.get_logger("examples.metrics")


# Example 1: Using timing_decorator for simple functions
@timing_decorator()
def fetch_api_data():
    """Simulate fetching data from an API."""
    logger.info("Fetching API data...")
    time.sleep(0.5)  # Simulate API call
    return {"records": 100, "status": "success"}


# Example 2: Using timing_decorator with memory tracking
@timing_decorator(track_memory=True)
def process_large_dataset():
    """Simulate processing a large dataset."""
    logger.info("Processing large dataset...")
    
    # Allocate some memory
    data = [i for i in range(1000000)]
    
    # Simulate processing
    time.sleep(0.3)
    
    result = sum(data)
    return result


# Example 3: Using timing_decorator with metadata
@timing_decorator(metadata={'stage': 'ingestion', 'source': 'clockify'})
def ingest_time_entries():
    """Simulate ingesting time entries."""
    logger.info("Ingesting time entries...")
    time.sleep(0.4)
    return {"entries": 500, "status": "completed"}


# Example 4: Using track_execution_time context manager
def correlate_costs():
    """Simulate cost correlation with tracked execution time."""
    logger.info("Correlating costs...")
    
    with track_execution_time('cost_correlation', track_memory=True):
        # Simulate data processing
        time.sleep(0.6)
        
        # Simulate pandas operations
        data = [{"cost": i * 100} for i in range(10000)]
        total = sum(item["cost"] for item in data)
    
    return total


# Example 5: Using AgentMetrics for agent execution tracking
@AgentMetrics.track_agent_execution('data_ingestion', track_memory=True)
def run_data_ingestion_agent():
    """Simulate Data Ingestion Agent execution."""
    logger.info("Running Data Ingestion Agent...")
    
    # Simulate multiple steps
    time.sleep(0.3)
    fetch_api_data()
    
    time.sleep(0.2)
    ingest_time_entries()
    
    return {"status": "completed", "records": 600}


@AgentMetrics.track_agent_execution('qualification', track_memory=True)
def run_qualification_agent():
    """Simulate Qualification Agent execution."""
    logger.info("Running Qualification Agent...")
    
    # Simulate RAG query
    time.sleep(0.4)
    
    # Simulate LLM reasoning
    time.sleep(0.5)
    
    return {"qualified_projects": 5, "confidence": 0.85}


@AgentMetrics.track_agent_execution('audit_trail', track_memory=True)
def run_audit_trail_agent():
    """Simulate Audit Trail Agent execution."""
    logger.info("Running Audit Trail Agent...")
    
    # Simulate narrative generation
    time.sleep(0.6)
    
    # Simulate PDF generation
    time.sleep(0.4)
    
    return {"report_id": "RPT-001", "status": "generated"}


# Example 6: Manual memory tracking
def manual_memory_tracking_example():
    """Example of manual memory tracking."""
    logger.info("Starting manual memory tracking...")
    
    MemoryTracker.start_tracking()
    
    # Allocate memory in stages
    logger.info("Allocating memory - Stage 1")
    data1 = [0] * 100000
    MemoryTracker.log_memory_usage("After Stage 1")
    
    logger.info("Allocating memory - Stage 2")
    data2 = [0] * 200000
    MemoryTracker.log_memory_usage("After Stage 2")
    
    logger.info("Allocating memory - Stage 3")
    data3 = [0] * 300000
    MemoryTracker.log_memory_usage("After Stage 3")
    
    # Get final snapshot
    snapshot = MemoryTracker.get_memory_snapshot()
    logger.info(f"Final memory snapshot: {snapshot}")
    
    MemoryTracker.stop_tracking()


# Example 7: Simulating a complete workflow
def simulate_complete_workflow():
    """Simulate a complete R&D tax credit workflow with metrics."""
    logger.info("=" * 60)
    logger.info("Starting Complete Workflow Simulation")
    logger.info("=" * 60)
    
    # Stage 1: Data Ingestion
    logger.info("\n--- Stage 1: Data Ingestion ---")
    ingestion_result = run_data_ingestion_agent()
    logger.info(f"Ingestion result: {ingestion_result}")
    
    # Stage 2: Qualification
    logger.info("\n--- Stage 2: Qualification ---")
    qualification_result = run_qualification_agent()
    logger.info(f"Qualification result: {qualification_result}")
    
    # Stage 3: Audit Trail
    logger.info("\n--- Stage 3: Audit Trail ---")
    audit_result = run_audit_trail_agent()
    logger.info(f"Audit result: {audit_result}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Workflow Complete")
    logger.info("=" * 60)


# Example 8: Analyzing metrics
def analyze_metrics():
    """Analyze collected metrics and display statistics."""
    logger.info("\n" + "=" * 60)
    logger.info("Metrics Analysis")
    logger.info("=" * 60)
    
    collector = get_metrics_collector()
    
    # Overall statistics
    logger.info("\n--- Overall Performance Statistics ---")
    log_performance_summary()
    
    # Agent-specific statistics
    logger.info("\n--- Agent Performance Statistics ---")
    for agent_name in ['data_ingestion', 'qualification', 'audit_trail']:
        logger.info(f"\nAgent: {agent_name}")
        AgentMetrics.log_agent_summary(agent_name)
    
    # Export metrics to file
    output_dir = Path(__file__).parent.parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    metrics_file = output_dir / "example_metrics.json"
    collector.export_metrics(metrics_file)
    logger.info(f"\nMetrics exported to: {metrics_file}")


def main():
    """Main function to run all examples."""
    logger.info("Starting Metrics Usage Examples")
    logger.info("=" * 60)
    
    # Run individual examples
    logger.info("\n--- Example 1: Simple Function Timing ---")
    result1 = fetch_api_data()
    logger.info(f"Result: {result1}")
    
    logger.info("\n--- Example 2: Function with Memory Tracking ---")
    result2 = process_large_dataset()
    logger.info(f"Result: {result2}")
    
    logger.info("\n--- Example 3: Function with Metadata ---")
    result3 = ingest_time_entries()
    logger.info(f"Result: {result3}")
    
    logger.info("\n--- Example 4: Context Manager ---")
    result4 = correlate_costs()
    logger.info(f"Result: {result4}")
    
    logger.info("\n--- Example 5: Agent Execution Tracking ---")
    result5 = run_data_ingestion_agent()
    logger.info(f"Result: {result5}")
    
    logger.info("\n--- Example 6: Manual Memory Tracking ---")
    manual_memory_tracking_example()
    
    # Run complete workflow simulation
    logger.info("\n")
    simulate_complete_workflow()
    
    # Analyze all collected metrics
    analyze_metrics()
    
    logger.info("\n" + "=" * 60)
    logger.info("All Examples Completed Successfully")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
